"""Docker provisioning for one agent-under-test task.

The harness (not the agent) does the heavy lifting: load the tar, start a
long-lived container with the host code path bind-mounted at WORKDIR, ensure the
mounted dir holds only the PRD, and hand the agent just the container id. The
agent develops inside via `docker exec`; output persists on the host through the
mount.
"""
import hashlib
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from . import config as C

WORKDIR = "/workspace"          # bind-mount target inside the container
PRD_NAME = "start.md"

# Transient docker/daemon hiccups (run/load races) are retried a few times before
# we declare an infra failure. Keeps the pipeline robust against flaky provisioning.
PROVISION_RETRIES = 3
RETRY_BACKOFF = (2.0, 5.0, 10.0)


class DockerError(RuntimeError):
    pass


def _run(cmd: list[str], *, timeout: float = 600, check: bool = True) -> subprocess.CompletedProcess:
    p = subprocess.run(cmd, capture_output=True, text=True,
                       errors="replace", timeout=timeout)
    if check and p.returncode != 0:
        raise DockerError(f"cmd failed ({p.returncode}): {' '.join(cmd)}\n{p.stderr[-2000:]}")
    return p


def _image_present(tag: str) -> bool:
    return subprocess.run(["docker", "image", "inspect", tag],
                          capture_output=True).returncode == 0


def anon_tag_for(alias: str, tar_path: Path | None = None) -> str:
    """'realcode@001' -> docker tag 'realcode/001:env-<h8>' (no '@', repo name hidden).

    The tag is keyed by the SOURCE TAR so two different images for the same repo
    number (e.g. the base language image vs the ultimate per-repo sandbox image)
    can NEVER share a tag. Without this, `ensure_image`'s present-tag early-return
    would silently reuse whichever env_mode populated 'realcode/NNN:env' first, so
    an ultimate run on a host that already held base images would generate AND test
    in the base image (no pre-installed deps) -> tests fail on missing deps ->
    artificially low scores (and vice-versa). The hash is over the tar's absolute
    path, which already encodes env_mode/language (docker_lang_official/node_20.tar
    vs clean_sandbox_docker_imgs/<key>_sandbox.tar), so it stays anonymous: it
    leaks neither the repo name nor a readable 'base'/'ultimate' label to the agent.
    tar_path is optional only for backward-compat; callers always pass it.
    """
    nnn = alias.split("@", 1)[1] if "@" in alias else C.docker_safe(alias)
    if tar_path is None:
        return f"realcode/{nnn}:env"
    h8 = hashlib.sha1(str(Path(tar_path).resolve()).encode()).hexdigest()[:8]
    return f"realcode/{nnn}:env-{h8}"


def ensure_image(tar_path: Path, *, anon_tag: str, hide_real_tag: bool) -> str:
    """Load the tar image, re-tag it to an anonymous tag, return the anon tag.

    The agent-under-test has host docker access, so `docker images` / `docker
    inspect` must never show the real repo name. We:
      1. load the tar (it carries the REAL RepoTag baked in),
      2. `docker tag` it to the anonymous `anon_tag`,
      3. for per-repo (ultimate) images whose real tag embeds the repo name,
         remove that real tag so only the anon tag remains.
    Base/cross-language images keep their real tag (it's just a language name,
    no repo-name leak) but are still RUN from the anon tag for a clean Config.Image.
    """
    if not tar_path.exists():
        raise DockerError(f"docker tar not found: {tar_path}")
    if _image_present(anon_tag):
        return anon_tag

    real_tag = C.image_tag_from_tar(tar_path)
    if not _image_present(real_tag):
        _run(["docker", "load", "-i", str(tar_path)], timeout=1800)
        if not _image_present(real_tag):
            raise DockerError(f"image {real_tag} not present after loading {tar_path}")

    _run(["docker", "tag", real_tag, anon_tag])
    if hide_real_tag and real_tag != anon_tag:
        # untag the real (repo-named) tag; the image survives via anon_tag
        subprocess.run(["docker", "rmi", "--no-prune", real_tag], capture_output=True)
    return anon_tag


@dataclass
class Container:
    container_id: str
    image_tag: str
    workdir: str
    code_path: Path

    def exec(self, bash: str, *, timeout: float = 600, check: bool = False) -> subprocess.CompletedProcess:
        return _run(["docker", "exec", "-w", self.workdir, self.container_id,
                     "bash", "-lc", bash], timeout=timeout, check=check)

    def teardown(self) -> None:
        """Stop and remove the container; host-side generated code is preserved."""
        subprocess.run(["docker", "rm", "-f", self.container_id], capture_output=True)


def _clean_workdir(code_path: Path, *, fallback_image: str | None = None) -> None:
    """Empty the host code dir before a fresh run.

    A previous container may have written files as root (uid 0) via the bind
    mount; a plain host `rm` then fails with EACCES. We try a normal rm first and,
    if anything remains, fall back to deleting from inside a throwaway container
    (which runs as root and shares the mount), so provisioning never wedges on a
    leftover root-owned file. `fallback_image` must already be loaded locally
    (we use the repo's own anon image, so no network pull is needed).
    """
    for child in code_path.iterdir():
        try:
            if child.is_dir():
                subprocess.run(["rm", "-rf", str(child)], capture_output=True)
            else:
                child.unlink()
        except (PermissionError, OSError):
            pass
    if fallback_image and any(code_path.iterdir()):
        # root-owned residue: wipe via a container that shares the mount.
        subprocess.run(
            ["docker", "run", "--rm", "-v", f"{code_path}:{WORKDIR}",
             fallback_image, "bash", "-lc",
             f"rm -rf {WORKDIR}/* {WORKDIR}/.[!.]* 2>/dev/null || true"],
            capture_output=True, timeout=120)


def provision(alias: str, code_path: Path, prd_text: str, tar_path: Path, *,
              clean_workdir: bool = True, proxy: str | None = None,
              no_proxy: str | None = None,
              hide_real_tag: bool = True,
              name_suffix: str | None = None,
              scaffold_src: Path | None = None) -> Container:
    """Prepare the host code path (PRD only), start the container, return it.

    alias:         the anonymous 'realcode@NNN' identifier (never the real key).
    clean_workdir: wipe the host dir first so the container starts with only the
                   PRD (used for fresh runs; skipped when resuming).
    proxy:         optional http(s) proxy for in-container apt/pip installs.
    no_proxy:      hosts that must bypass the proxy (the internal Oracle, so the
                   agent's clarification POSTs are not routed to the gateway).
    hide_real_tag: untag the real (repo-named) image after re-tagging (ultimate).
    scaffold_src:  if given (scaffold=True), a host dir whose contents are copied
                   into the workdir as `rcb_tests/public_test_cases/` (where the
                   eval protocol's `test.sh --cases-dir public_test_cases` looks),
                   so the agent under test starts with the public cases already
                   present. Default None preserves the prior PRD-only behaviour.

    Transient docker failures (run/load races, daemon hiccups) are retried with
    backoff; only a persistent failure raises DockerError (a true infra failure).
    """
    code_path.mkdir(parents=True, exist_ok=True)

    anon_tag = anon_tag_for(alias, tar_path)
    image_tag = ensure_image(tar_path, anon_tag=anon_tag, hide_real_tag=hide_real_tag)

    if clean_workdir:
        _clean_workdir(code_path, fallback_image=image_tag)
    (code_path / PRD_NAME).write_text(prd_text, encoding="utf-8")

    # scaffold: drop the public cases where the eval protocol expects them —
    # `rcb_tests/public_test_cases/` (test.sh runs `--cases-dir public_test_cases`
    # relative to rcb_tests). Written AFTER _clean_workdir so it is not wiped;
    # copied host-side onto the bind mount before the container starts.
    if scaffold_src is not None and Path(scaffold_src).is_dir():
        dst = code_path / "rcb_tests" / "public_test_cases"
        shutil.rmtree(dst, ignore_errors=True)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(scaffold_src, dst)

    name = f"rcb_{C.docker_safe(alias)}"          # 'rcb_realcode_001' (no '@')
    if name_suffix:
        # Namespace by run so concurrent batches over the same alias range never
        # collide on --name (and never 'docker rm -f' each other's containers).
        name = f"{name}_{name_suffix}"
    cmd = ["docker", "run", "-d", "--rm",
           "--name", name,
           "-v", f"{code_path}:{WORKDIR}",
           "-w", WORKDIR]
    if proxy:
        cmd += ["-e", f"http_proxy={proxy}", "-e", f"https_proxy={proxy}",
                "-e", f"HTTP_PROXY={proxy}", "-e", f"HTTPS_PROXY={proxy}"]
        if no_proxy:
            cmd += ["-e", f"no_proxy={no_proxy}", "-e", f"NO_PROXY={no_proxy}"]
    cmd += [image_tag, "sleep", "infinity"]

    last_err: Exception | None = None
    for attempt in range(PROVISION_RETRIES):
        # A stale container with the same name would block --name; remove it first.
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
        try:
            p = _run(cmd, timeout=300)
            container_id = p.stdout.strip()
            if not container_id:
                raise DockerError(f"docker run produced no container id for {alias}")
            return Container(container_id=container_id, image_tag=image_tag,
                             workdir=WORKDIR, code_path=code_path)
        except (DockerError, subprocess.TimeoutExpired) as e:  # noqa: PERF203
            last_err = e
            if attempt < PROVISION_RETRIES - 1:
                time.sleep(RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)])
    raise DockerError(f"docker run failed after {PROVISION_RETRIES} attempts "
                      f"for {alias}: {last_err}")


def reap_run_containers(name_suffix: str) -> int:
    """Force-remove any containers from THIS run that are still alive.

    Containers are named `rcb_<alias>_<name_suffix>` (name_suffix = append_id[:8]),
    so filtering by the suffix scopes the sweep to the current run only — a
    concurrent batch over the same alias range (different append_id, hence a
    different suffix) is never touched, preserving the per-run isolation the
    `--name` suffixing was introduced for. Best-effort: never raises (it is a
    cleanup safety net, not a critical path). Returns the count removed.
    """
    if not name_suffix:
        return 0
    try:
        p = subprocess.run(
            ["docker", "ps", "-aq", "--filter", f"name=_{name_suffix}"],
            capture_output=True, text=True, timeout=60)
        ids = [x for x in p.stdout.split() if x]
        if ids:
            subprocess.run(["docker", "rm", "-f", *ids],
                           capture_output=True, timeout=120)
        return len(ids)
    except Exception:  # noqa: BLE001
        return 0
