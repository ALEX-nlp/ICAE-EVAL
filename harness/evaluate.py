"""Objective pass-rate evaluation for one generated repo.

Parameterized for the results/<append_id>/<repo> layout and the env-mode
generation image:

  1. stage the generated code,
  2. run a fresh container from the SAME image used for generation, inject the
     three authoritative case dirs (public_test_cases / test_cases /
     enhanced_test_cases) from <REPOS_DIR>/<repo>/rcb_tests,
  3. run the agent's own `rcb_tests/test.sh --cases-dir <sub>`, capture each
     case's stdout,
  4. byte-compare captured stdout against the authoritative `expected_output`
     (host side, so we never trust the agent's self-reported PASS/FAIL),
  5. write objective.json (public_visible / hidden / enhanced  P/T + rates).

PRDs and tests are language-agnostic (JSON stdin -> stdout), so this works
regardless of the implementation language the agent chose.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import config as C

# authoritative subdir -> objective.json metric name
SUBDIRS = {
    "public_test_cases": "public_visible",
    "test_cases": "hidden",
    "enhanced_test_cases": "enhanced",
}


def _auth_total(cases_dir: Path) -> int:
    total = 0
    for f in sorted(cases_dir.glob("*.json")):
        try:
            total += len(json.loads(f.read_text(encoding="utf-8")).get("cases", []))
        except Exception:
            pass
    return total


def _outputs_for_stem(out_dir: Path, stem: str) -> dict[int, Path]:
    """Map captured-output index -> file path for one JSON stem.

    Parses the integer suffix out of '<stem>@<N>.txt' regardless of zero-padding
    (so '@0', '@00', '@000' all read as 0). The agent picks the numbering base,
    so we never assume one; the caller derives the base from min(index).
    """
    pat = re.compile(re.escape(stem) + r"@(\d+)\.txt$")
    out: dict[int, Path] = {}
    if not out_dir.is_dir():
        return out
    for pth in out_dir.iterdir():
        m = pat.match(pth.name)
        if m:
            out[int(m.group(1))] = pth
    return out


def _host_compare(cases_dir: Path, out_dir: Path) -> tuple[int, int, dict]:
    """Compare authoritative expected_output vs captured stdout. -> (passed, total, diag).

    Output files are matched to cases by INDEX OFFSET, not a hard-coded base: for
    each stem we take base = min(captured index) and map case i -> file (i + base).
    This handles 0-based (`@000`) and 1-based (`@001`) agent numbering alike, which
    a fixed 0-based lookup would mis-align (every case shifted -> false 0).

    diag carries the first few failures for objective.json's `reason`/`sample`.
    """
    p = t = 0
    missing = 0
    mismatches: list[dict] = []
    for f in sorted(cases_dir.glob("*.json")):
        stem = f.stem
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        cases = data.get("cases", [])
        outs = _outputs_for_stem(out_dir, stem)
        base = min(outs) if outs else 0
        for i, case in enumerate(cases):
            t += 1
            exp = case.get("expected_output", "")
            if not isinstance(exp, str):
                exp = json.dumps(exp)
            pth = outs.get(i + base)
            actual = pth.read_text(encoding="utf-8", errors="replace") if pth else None
            if actual is None:
                missing += 1
                if len(mismatches) < 3:
                    mismatches.append({"case": f"{stem}[{i}]", "kind": "missing_output",
                                       "expected": exp[:300], "actual": None})
            elif actual == exp:
                p += 1
            elif len(mismatches) < 3:
                mismatches.append({"case": f"{stem}[{i}]", "kind": "mismatch",
                                   "expected": exp[:300], "actual": actual[:300]})
    return p, t, {"missing": missing, "mismatches": mismatches}


_BUILD_ERROR_MARKERS = (
    ("npm err", "build_error"),
    ("compilation failed", "build_error"),
    ("cannot compile", "build_error"),
    ("error[e", "build_error"),                       # rustc
    ("cannot find module", "runtime_error"),
    ("traceback (most recent call last)", "runtime_error"),
    ("modulenotfounderror", "runtime_error"),
    ("importerror", "runtime_error"),
    ("syntaxerror", "runtime_error"),
    ("command not found", "build_error"),
)


def _scan_build_errors(build_log: Path) -> str | None:
    """Best-effort: classify a build/run failure from the captured test.sh trace."""
    try:
        low = build_log.read_text(encoding="utf-8", errors="replace").lower()
    except Exception:
        return None
    for marker, kind in _BUILD_ERROR_MARKERS:
        if marker in low:
            return kind
    return None


# Signatures of a DIRECT-connection network failure during an in-test.sh install
# (apt/pip/npm/pub get/...). When one of these shows up we retry the tier ONCE
# with the proxy injected — the proxy bandwidth is scarce, so it is used only as
# this fallback, never by default.
_NETWORK_ERROR_MARKERS = (
    "could not resolve host",
    "temporary failure in name resolution",
    "name or service not known",
    "connection timed out",
    "connection refused",
    "network is unreachable",
    "no route to host",
    "failed to connect",
    "could not connect to",
    "timed out (connect)",
    "proxyconnect",
    "ssl: connection",
    "etimedout",
    "enotfound",
    "tls handshake timeout",
)


def _has_network_error(build_log: Path) -> bool:
    """True if the captured trace shows a direct-connection network failure."""
    try:
        low = build_log.read_text(encoding="utf-8", errors="replace").lower()
    except Exception:
        return False
    return any(m in low for m in _NETWORK_ERROR_MARKERS)


def _diagnose(diag: dict, build_log: Path, passed: int, total: int) -> dict:
    """Distill WHY a tier didn't fully pass into a `reason` (+ first-failure `sample`)."""
    missing = diag.get("missing", 0)
    mism = diag.get("mismatches", [])
    has_mismatch = any(m.get("kind") == "mismatch" for m in mism)
    if total and missing >= total:
        reason = _scan_build_errors(build_log) or "no_output"
    elif missing > 0 and has_mismatch:
        reason = "mixed_missing_and_mismatch"
    elif missing > 0:
        reason = "partial_missing_output"
    else:
        reason = "output_mismatch"
    out = {"reason": reason}
    if mism:
        out["sample"] = mism[0]
    return out


_CONTAINER_SCRIPT = r"""
set -u
rm -rf /eval && mkdir -p /eval
cp -r /gen/. /eval/ 2>&1 | tail -3
cd /eval
rm -rf rcb_tests/stdout
# Inject the AUTHORITATIVE cases for this tier, replacing whatever the agent
# shipped under rcb_tests/__SUB__ (so the agent cannot grade itself).
rm -rf rcb_tests/__SUB__ && mkdir -p rcb_tests/__SUB__
cp -r /auth/. rcb_tests/__SUB__/ 2>&1 | tail -3
if [ -f rcb_tests/test.sh ]; then
  sed -i 's| >/dev/null 2>&1| 2>\&1|g; s| 2>/dev/null| |g; s| >/dev/null| |g' rcb_tests/test.sh
fi
echo "--- BEGIN test.sh trace (cases-dir=__SUB__) ---" >&2
bash -x rcb_tests/test.sh --cases-dir __SUB__ 2>&1
echo "--- END test.sh trace rc=$? ---" >&2
mkdir -p /rcb-out
cp -r rcb_tests/stdout/__SUB__/. /rcb-out/ 2>/dev/null || true
"""


def _run_subdir_once(image_tag: str, gen_dir: Path, cases_dir: Path, sub: str,
                     build_log: Path, proxy: str | None, timeout: float,
                     no_proxy: str | None = None,
                     container_name: str | None = None) -> Path:
    """Run one cases-dir inside a fresh container; return the host outcap dir.

    The authoritative `cases_dir` is bind-mounted read-only at /auth and copied
    over the agent's own rcb_tests/<sub> before test.sh runs.

    The container is given a run-scoped `--name` and force-removed in a `finally`.
    `--rm` alone is NOT enough: on a `timeout` (or if this process is killed / the
    host OOMs), `subprocess.run` kills only the `docker run` CLI — the container
    keeps running on the daemon, and `--rm` fires only when its own process exits
    (never, for a hung test.sh that starts a server). With the ultimate image now
    used at test time, those orphans hold multi-GB each and accumulate across a
    run -> host OOM. Removing by name on every exit path closes that leak, and the
    `_<suffix>` in the name lets the end-of-run reaper sweep any straggler too.
    """
    staging = Path(tempfile.mkdtemp(prefix="rcb-eval-"))
    outcap = staging / "outcap"
    outcap.mkdir()
    try:
        cmd = ["docker", "run", "--rm"]
        if container_name:
            cmd += ["--name", container_name]
        cmd += ["-v", f"{gen_dir}:/gen:ro",
                "-v", f"{cases_dir}:/auth:ro",
                "-v", f"{outcap}:/rcb-out"]
        if proxy:
            cmd += ["-e", f"http_proxy={proxy}", "-e", f"https_proxy={proxy}",
                    "-e", f"HTTP_PROXY={proxy}", "-e", f"HTTPS_PROXY={proxy}"]
            if no_proxy:
                cmd += ["-e", f"no_proxy={no_proxy}", "-e", f"NO_PROXY={no_proxy}"]
        cmd += [image_tag, "bash", "-lc", _CONTAINER_SCRIPT.replace("__SUB__", sub)]
        # A stale container with the same name (a prior crashed tier) would block
        # --name; clear it first, mirroring docker_env.provision.
        if container_name:
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        try:
            p = subprocess.run(cmd, capture_output=True, text=True,
                               errors="replace", timeout=timeout)
        finally:
            if container_name:
                subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        build_log.parent.mkdir(parents=True, exist_ok=True)
        build_log.write_text((p.stdout or "") + "\n" + (p.stderr or ""), encoding="utf-8")
        # copy captured stdout out of the (about-to-be-deleted) staging dir
        persisted = build_log.parent / f"outcap_{sub}"
        if persisted.exists():
            shutil.rmtree(persisted)
        shutil.copytree(outcap, persisted)
        return persisted
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _run_subdir(image_tag: str, gen_dir: Path, cases_dir: Path, sub: str,
                build_log: Path, proxy: str | None, timeout: float,
                no_proxy: str | None = None,
                fallback_proxy: str | None = None,
                container_name: str | None = None) -> Path:
    """Run a cases-dir, with a one-shot proxy fallback on a direct-network failure.

    By default the tier runs with NO proxy (`proxy` is normally None) so the
    container installs dependencies over a direct connection — the scarce proxy
    bandwidth is left untouched. Only if that run shows a network error in its
    trace (DNS/connect/timeout while apt/pip/npm/pub get were fetching) AND a
    `fallback_proxy` is available do we re-run the SAME tier once with the proxy
    injected. A pre-set explicit `proxy` disables the fallback (already proxied).
    """
    persisted = _run_subdir_once(image_tag, gen_dir, cases_dir, sub, build_log,
                                 proxy, timeout, no_proxy, container_name)
    if proxy or not fallback_proxy:
        return persisted
    if not _has_network_error(build_log):
        return persisted
    print(f"  [{sub}] direct install hit a network error; "
          f"retrying once via proxy {fallback_proxy}")
    return _run_subdir_once(image_tag, gen_dir, cases_dir, sub, build_log,
                            fallback_proxy, timeout, no_proxy, container_name)


def evaluate_repo(append_id: str, alias: str, image_tag: str, *,
                  proxy: str | None = None, no_proxy: str | None = None,
                  fallback_proxy: str | None = None,
                  timeout: float = 2400) -> dict:
    """Run the three-tier objective eval; write & return objective.json content.

    `alias` ('realcode@NNN') names the generated-code dir; the authoritative test
    cases still live under the REAL repo key, so we translate alias -> key for the
    auth root only. objective.json keeps the alias (host-side, never seen by the
    agent).
    """
    gen_dir = C.code_path(append_id, alias)
    auth_root = C.REPOS_DIR / C.key_for_alias(alias) / "rcb_tests"
    eval_dir = C.RESULTS / append_id / "_eval" / alias
    eval_dir.mkdir(parents=True, exist_ok=True)

    if not (gen_dir / "rcb_tests" / "test.sh").exists():
        result = {"error": "no rcb_tests/test.sh in generated code",
                  "repo": alias, "image": image_tag}
        (eval_dir / "objective.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    result: dict = {"repo": alias, "image": image_tag}
    for sub, metric in SUBDIRS.items():
        cases_dir = auth_root / sub
        if not cases_dir.is_dir():
            result[metric] = {"passed": 0, "total": 0, "rate": None,
                              "note": f"no authoritative {sub}"}
            continue
        build_log = eval_dir / f".build_log_{sub}.txt"
        # Run-scoped, unique-per-tier container name. The trailing `_<append_id[:8]>`
        # matches docker_env.reap_run_containers' `name=_<suffix>` filter, so a tier
        # that somehow outlives its `finally` rm is still swept at end of run.
        cname = f"rcbeval_{C.docker_safe(alias)}_{sub}_{append_id[:8]}"
        outcap = _run_subdir(image_tag, gen_dir, cases_dir, sub, build_log, proxy, timeout,
                             no_proxy, fallback_proxy, container_name=cname)
        passed, total, diag = _host_compare(cases_dir, outcap)
        auth_total = _auth_total(cases_dir)
        if auth_total and total < auth_total:
            total = auth_total  # build/run dropped cases -> use authoritative denominator
        rate = round(passed / total, 4) if total else None
        entry = {"passed": passed, "total": total, "rate": rate}
        if passed != total:
            entry.update(_diagnose(diag, build_log, passed, total))
        result[metric] = entry

    (eval_dir / "objective.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def rescore_from_outcap(append_id: str, alias: str) -> dict:
    """Recompute objective.json from already-captured outcap_<sub> dirs (no docker).

    Use this after a `_host_compare` fix to re-grade a finished run without
    re-running any container: the per-case stdout was persisted under
    _eval/<alias>/outcap_<sub>/ during the original eval.
    """
    auth_root = C.REPOS_DIR / C.key_for_alias(alias) / "rcb_tests"
    eval_dir = C.RESULTS / append_id / "_eval" / alias
    obj_path = eval_dir / "objective.json"
    prev = {}
    if obj_path.exists():
        try:
            prev = json.loads(obj_path.read_text(encoding="utf-8"))
        except Exception:
            prev = {}

    result: dict = {"repo": alias, "image": prev.get("image"), "rescored": True}
    for sub, metric in SUBDIRS.items():
        cases_dir = auth_root / sub
        if not cases_dir.is_dir():
            result[metric] = {"passed": 0, "total": 0, "rate": None,
                              "note": f"no authoritative {sub}"}
            continue
        outcap = eval_dir / f"outcap_{sub}"
        build_log = eval_dir / f".build_log_{sub}.txt"
        passed, total, diag = _host_compare(cases_dir, outcap)
        auth_total = _auth_total(cases_dir)
        if auth_total and total < auth_total:
            total = auth_total
        rate = round(passed / total, 4) if total else None
        entry = {"passed": passed, "total": total, "rate": rate}
        if passed != total:
            entry.update(_diagnose(diag, build_log, passed, total))
        result[metric] = entry

    obj_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _aliases_with_outcap(append_id: str) -> list[str]:
    eval_root = C.RESULTS / append_id / "_eval"
    if not eval_root.is_dir():
        return []
    out = []
    for d in sorted(eval_root.iterdir()):
        if d.is_dir() and any(d.glob("outcap_*")):
            out.append(d.name)
    return out


def main() -> None:
    import argparse
    from . import user_agent_client as ua

    ap = argparse.ArgumentParser(
        description="Rescore objective.json from existing outcap dirs (no docker).")
    ap.add_argument("--append-id", required=True)
    ap.add_argument("--repos", nargs="*", help="aliases/keys to rescore (default: all with outcap)")
    args = ap.parse_args()

    aliases = ([C.resolve_alias(r) for r in args.repos] if args.repos
               else _aliases_with_outcap(args.append_id))
    for alias in aliases:
        res = rescore_from_outcap(args.append_id, alias)
        ua.update_repo_status(args.append_id, alias, {"objective": res})
        pv, hd, en = (res.get(k, {}) for k in ("public_visible", "hidden", "enhanced"))
        print(f"{alias}: public {pv.get('passed')}/{pv.get('total')}  "
              f"hidden {hd.get('passed')}/{hd.get('total')}  "
              f"enhanced {en.get('passed')}/{en.get('total')}")
    print(f"rescored {len(aliases)} repos")


if __name__ == "__main__":
    main()
