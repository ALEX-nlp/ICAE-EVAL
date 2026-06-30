"""Per-repo Markdown summary for one eval run (append_id).

Reads results/<append_id>/settings.json[repos] (the authoritative store for
generation / agentic / interaction) plus each repo's _eval/<alias>/
{objective,structural}.json, and writes two Markdown tables grouped into the
four task.md metric families:

  Test Cases Pass Rate   -> Overall / Public / Native / Enhanced
  Agentic Evaluation     -> Semantic Similarity / API Similarity / Design Quality
  Structural Assessment  -> File Count % / LOC % / Class Similarity / Method Similarity
  Interaction Quality    -> Constraint Coverage / Fallback Rate / Budget Usage Rate

Scale convention (uniform, one decimal):
  - pass rates + agentic scores + class/method similarity are reported on a
    0-100 scale (0-1 internal values are multiplied by 100);
  - File/LOC are RATIOS (generated/orig) and stay as a plain ratio (one decimal);
  - interaction values are already 0-100 percentages.

Per-repo Overall is the case-aggregated pass rate of Native+Enhanced (NOT a mean
of their rates, and NOT including Public):
    Overall = (passed_native + passed_enhanced) / (total_native + total_enhanced)
The separate Averages table reports the MEAN of each per-repo value across repos
that have one.

Rows are sorted by alias index ascending (realcode@001, @002, ...).
One file per append_id: results/<append_id>/summary.md (override with --out).
"""
import argparse
import json
from pathlib import Path

from . import config as C


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _suite(obj: dict, key: str) -> dict | None:
    m = obj.get(key) if isinstance(obj, dict) else None
    return m if isinstance(m, dict) else None


def _pt(metric: dict | None) -> tuple[int | None, int | None]:
    """Return (passed, total) ints from a suite entry, or (None, None)."""
    if not isinstance(metric, dict):
        return None, None
    p, t = metric.get("passed"), metric.get("total")
    if isinstance(p, int) and isinstance(t, int):
        return p, t
    return None, None


def _rate(metric: dict | None) -> float | None:
    """0-1 pass rate for a suite, or None when there are no cases."""
    p, t = _pt(metric)
    if t is None or t == 0:
        return None
    return p / t


def _overall_rate(hid: dict | None, enh: dict | None) -> float | None:
    """Case-aggregated Native+Enhanced: (Σpassed)/(Σtotal). Excludes Public."""
    hp, ht = _pt(hid)
    ep, et = _pt(enh)
    tt = (ht or 0) + (et or 0)
    if tt == 0:
        return None
    return ((hp or 0) + (ep or 0)) / tt


def _ratio(num, den) -> float | None:
    if not isinstance(num, (int, float)) or not isinstance(den, (int, float)) or den == 0:
        return None
    return num / den


def _alias_num(alias: str) -> int:
    try:
        return int(alias.split("@")[-1])
    except Exception:
        return 10 ** 9


# ---- metric layout: (label, key, kind) -------------------------------------
# kind drives both display and averaging:
#   "pct"    -> value is 0-1; show value*100 (one decimal)
#   "native" -> value is already 0-100; show as-is (one decimal)
#   "ratio"  -> value is a ratio (generated/orig); show as-is (one decimal)
_GROUPS: list[tuple[str, list[tuple[str, str, str]]]] = [
    ("Test Cases Pass Rate", [
        ("Overall", "overall", "pct"),
        ("Public", "public", "pct"),
        ("Native", "native", "pct"),
        ("Enhanced", "enhanced", "pct"),
    ]),
    ("Agentic Evaluation", [
        ("Semantic Sim", "semantic", "pct"),
        ("API Sim", "api", "pct"),
        ("Design Quality", "design", "pct"),
    ]),
    ("Structural Assessment", [
        ("File Count %", "files", "pct"),
        ("LOC %", "loc", "pct"),
        ("Class Sim", "class", "pct"),
        ("Method Sim", "method", "pct"),
    ]),
    ("Interaction Quality", [
        ("Constraint Cov", "cov", "native"),
        ("Fallback Rate", "fallback", "native"),
        ("Budget Usage", "budget", "native"),
    ]),
]
_COLS = [(label, key, kind) for _, group in _GROUPS for (label, key, kind) in group]


def _cell(v, kind: str) -> str:
    if not isinstance(v, (int, float)):
        return "—"
    return f"{v * 100:.1f}" if kind == "pct" else f"{v:.1f}"


# Per-suite failure reasons emitted by evaluate._diagnose, shortened for the table.
_REASON_SHORT = {
    "no_output": "no output",
    "mixed_missing_and_mismatch": "missing+mismatch",
    "output_mismatch": "mismatch",
    "runtime_error": "runtime err",
    "build_error": "build err",
    "partial_missing_output": "partial missing",
}


def _short_gen_reason(reason: str) -> str:
    r = (reason or "").strip()
    if not r:
        return "gen error"
    if r.startswith("docker:"):
        return "docker timeout" if "timed out" in r else "docker err"
    if r.startswith("prd:"):
        return "prd err"
    return r[:40]


# Substrings that mark an outcome as an infrastructure / external-API failure
# rather than the model's own fault. Matched case-insensitively against BOTH the
# orchestrator's `reason` (docker:/prd:/skipped) and the agent runner's `detail`
# (where API/SDK errors land: no_db_connection, rate limits, timeouts, 5xx, ...).
_INFRA_MARKERS = (
    "docker:", "prd:",
    "no_db_connection", "no connected db", "no connected database",
    "ratelimited", "rate limit", "rate_limit", "429", "overloaded", "overload",
    "timeout_inactivity", "timeout_overall", "timed out", "timeout",
    "upstream_error", "upstream error", "bad gateway", "gateway timeout",
    "service unavailable", "service_unavailable", "internal server error",
    "502", "503", "504", "500",
    "connection", "connect error", "connection reset", "connection refused",
    "network", "dns", "econnreset", "econnrefused",
    "401", "403", "unauthorized", "forbidden", "authentication", "invalid api key",
)


def _is_infra_error(rec: dict) -> bool:
    """True if a generation error is an infra / external-API failure, not the
    model's fault. Inspects `reason` (orchestrator) AND `detail` (agent runner)."""
    blob = f"{rec.get('reason') or ''} {rec.get('detail') or ''}".lower()
    return any(m in blob for m in _INFRA_MARKERS)


def _failure_class(rec: dict, obj: dict) -> str:
    """Classify a repo's outcome for pass-rate scoring.

      'ok'    — generation succeeded and tests ran (use the real rates).
      'model' — the model's own failure: it refused, hung/errored with no result,
                or finished but never produced rcb_tests/test.sh. These score 0%
                and STAY in the denominator (a weak/non-compliant model is penalized).
      'infra' — not the model's fault: docker/provisioning failure, an external API
                error (no_db_connection, 429/ratelimit, timeout, 5xx, connection,
                auth), or the harness couldn't present the task (missing tar/PRD).
                Excluded from stats; eligible for a retest.
    """
    if rec.get("refused"):
        return "model"
    gen = rec.get("generation")
    if gen == "error":
        return "infra" if _is_infra_error(rec) else "model"
    if gen == "skipped":
        return "infra"
    if gen == "success":
        if isinstance(obj, dict) and obj.get("error") and "test.sh" in obj["error"]:
            return "model"
    return "ok"


def _error_cause(rec: dict, obj: dict, struct: dict) -> str:
    """Human-readable cause when a repo failed / data is missing. '—' if clean."""
    gen = rec.get("generation")
    if gen and gen != "success":
        if rec.get("refused"):
            return "refused"
        if gen == "skipped":
            return f"skipped: {_short_gen_reason(rec.get('reason', ''))}"
        if rec.get("reason"):
            return _short_gen_reason(rec.get("reason", ""))
        # API/SDK errors land in `detail` (no_db_connection, 429, timeout, ...).
        detail = (rec.get("detail") or "").strip()
        return f"infra: {detail[:34]}" if detail else "gen error"
    if isinstance(obj, dict) and obj.get("error"):
        e = obj["error"]
        return "no test.sh" if "test.sh" in e else e[:40]
    seen: list[str] = []
    for k in ("public_visible", "hidden", "enhanced"):
        m = _suite(obj, k)
        if m and m.get("reason"):
            s = _REASON_SHORT.get(m["reason"], m["reason"])
            if s not in seen:
                seen.append(s)
    if seen:
        return "/".join(seen)
    if isinstance(struct, dict) and struct.get("error"):
        return "no golden src" if "golden" in struct["error"] else struct["error"][:40]
    return "—"


def build_rows(append_id: str) -> tuple[list[dict], dict]:
    # Per-run file results/<append_id>/settings.json = {append_id, config, repos}.
    # Flatten config to the top level so existing header lookups (env_mode,
    # run_seconds, ...) keep working, and keep `repos` alongside.
    run = _load(C.run_settings_path(append_id))
    settings = dict(run.get("config", {}))
    settings["repos"] = run.get("repos", {})
    repos = settings.get("repos", {})
    eval_root = C.RESULTS / append_id / "_eval"
    rows: list[dict] = []
    for alias in sorted(repos, key=_alias_num):
        rec = repos[alias]
        d = eval_root / alias
        obj = _load(d / "objective.json")
        struct = _load(d / "structural.json")
        agentic = rec.get("agentic", {}) or {}
        inter = rec.get("interaction", {}) or {}
        scale = struct.get("scale", {}) if isinstance(struct, dict) else {}
        try:
            orig_lang = C.alias_record(alias).get("language", "—")
        except Exception:
            orig_lang = "—"

        nums = {
            "overall": _overall_rate(_suite(obj, "hidden"), _suite(obj, "enhanced")),
            "public": _rate(_suite(obj, "public_visible")),
            "native": _rate(_suite(obj, "hidden")),
            "enhanced": _rate(_suite(obj, "enhanced")),
            "semantic": agentic.get("semantic_similarity"),
            "api": agentic.get("api_similarity"),
            "design": agentic.get("design_quality"),
            "files": _ratio(scale.get("generated_src_files"), scale.get("orig_src_files")),
            "loc": scale.get("loc_coverage_ratio") if isinstance(
                scale.get("loc_coverage_ratio"), (int, float)) else None,
            "class": struct.get("class_similarity") if isinstance(struct, dict) else None,
            "method": struct.get("method_similarity") if isinstance(struct, dict) else None,
            "cov": inter.get("constraint_coverage"),
            "fallback": inter.get("fallback_rate"),
            "budget": inter.get("budget_usage_rate"),
        }
        # Scoring rule: a model-side failure (refusal / hang / no test.sh) is the
        # model being weak, so its pass-rate columns count as 0% and stay in the
        # denominator. Infra failures (docker/provisioning) are excluded entirely
        # (eligible for retest) and leave the cells as missing.
        fclass = _failure_class(rec, obj)
        if fclass == "model":
            for k in ("overall", "public", "native", "enhanced"):
                if nums[k] is None:
                    nums[k] = 0.0
        rows.append({
            "alias": alias,
            "source": rec.get("real_key", "—"),
            "lang": orig_lang,
            "error": _error_cause(rec, obj, struct),
            "fclass": fclass,
            "_nums": nums,
        })
    return rows, settings


def _group_header() -> str:
    cells = ["", "", ""]
    for name, group in _GROUPS:
        cells.append(name)
        cells.extend([""] * (len(group) - 1))
    cells.append("")  # Error column
    return "| " + " | ".join(cells) + " |"


def _col_header() -> str:
    cells = ["Repo", "Source", "Lang"] + [label for (label, _, _) in _COLS] + ["Error"]
    return "| " + " | ".join(cells) + " |"


def _divider(n: int) -> str:
    return "| " + " | ".join(["---"] * n) + " |"


def _averages_table(rows: list[dict]) -> list[str]:
    total = len(rows)
    out = ["| Group | Metric | Mean | n | missing (reason) |",
           "| --- | --- | --- | --- | --- |"]
    for name, group in _GROUPS:
        first = True
        for label, key, kind in group:
            vals = [r["_nums"][key] for r in rows
                    if isinstance(r["_nums"].get(key), (int, float))]
            mean = _cell(sum(vals) / len(vals), kind) if vals else "—"
            # Tally why the remaining (total - n) repos have no value for this metric.
            reasons: dict[str, int] = {}
            for r in rows:
                if isinstance(r["_nums"].get(key), (int, float)):
                    continue
                why = r["error"] if r["error"] != "—" else "no value"
                reasons[why] = reasons.get(why, 0) + 1
            miss = total - len(vals)
            top = ", ".join(f"{c}× {w}" for w, c in
                            sorted(reasons.items(), key=lambda x: -x[1])[:2])
            miss_cell = f"{miss} ({top})" if miss else "0"
            out.append(f"| {name if first else ''} | {label} | {mean} | "
                       f"{len(vals)} | {miss_cell} |")
            first = False
    return out


def render(append_id: str) -> str:
    rows, settings = build_rows(append_id)
    rows.sort(key=lambda r: _alias_num(r["alias"]))

    model = settings.get("model_name", "?")
    ncol = 3 + len(_COLS) + 1
    out: list[str] = []
    out.append(f"# ICAE-Bench — Per-Repo Results ({model})")
    out.append("")
    out.append(f"- **append_id**: `{append_id}`")
    out.append(f"- **Tested model**: {model}  |  **User model**: "
               f"{settings.get('user_model_name', '?')}  |  **Critic**: "
               f"{settings.get('critic_model_name', '?')}")
    out.append(f"- **env_mode**: {settings.get('env_mode', '?')}  |  **prd_type**: "
               f"{settings.get('prd_type', '?')}  |  **eval_mode**: "
               f"{settings.get('eval_mode', '?')}  |  **query_count**: "
               f"{settings.get('query_count', '?')}")
    out.append(f"- **repos evaluated**: {len(rows)}")

    repos_meta = settings.get("repos", {})
    gen_secs = [r.get("gen_seconds") for r in repos_meta.values()
                if isinstance(r.get("gen_seconds"), (int, float))]
    wall = settings.get("run_seconds")
    timing_bits = []
    if isinstance(wall, (int, float)):
        timing_bits.append(f"**wall-clock**: {wall / 60:.1f} min ({wall:.0f}s)")
    if gen_secs:
        timing_bits.append(
            f"**gen/repo**: mean {sum(gen_secs) / len(gen_secs):.0f}s, "
            f"min {min(gen_secs):.0f}s, max {max(gen_secs):.0f}s")
    if isinstance(settings.get("run_concurrency"), int):
        timing_bits.append(f"**concurrency**: {settings['run_concurrency']}")
    if timing_bits:
        out.append("- " + "  |  ".join(timing_bits))
    if settings.get("finished_at"):
        out.append(f"- **finished_at**: {settings['finished_at']}")
    out.append("")

    out.append("## Scale & columns")
    out.append("- All metrics are on a **0-100 scale, one decimal**. "
               "**File Count %** and **LOC %** are generated/orig source "
               "files / LOC expressed as a percentage of the original "
               "(can exceed 100% when the generated tree is larger).")
    out.append("- **Test Cases Pass Rate** — `Overall` / `Public` / `Native` / "
               "`Enhanced` over `public_test_cases` / `test_cases` / "
               "`enhanced_test_cases`. **Overall** is the case-aggregated pass rate "
               "of Native+Enhanced: `(passed_native + passed_enhanced) / "
               "(total_native + total_enhanced)` — not a mean of the two rates, "
               "and not including Public. **A model-side failure (refusal, hang, "
               "or no `rcb_tests/test.sh`) scores 0% and stays in the average; "
               "infra/provisioning failures are excluded (retest-eligible).**")
    out.append("- **Agentic Evaluation** — three INDEPENDENT Critic scores "
               "(behavioral equivalence / public surface / engineering).")
    out.append("- **Structural Assessment** — generated vs golden original "
               "(in-scope subset).")
    out.append("- **Interaction Quality** — from the User Agent.")
    out.append("- **Error** — failure/missing-data cause (`no test.sh`, `build err`, "
               "`runtime err`, `mismatch`, `no output`, `docker timeout`, "
               "`gen error`, `no golden src` = structural skipped, golden source "
               "not cached). `—` = ran cleanly.")
    out.append("")
    out.append("Sorted by repo index ascending.")
    out.append("")
    out.append(_group_header())
    out.append(_col_header())
    out.append(_divider(ncol))
    for r in rows:
        cells = [f"`{r['alias']}`", f"`{r['source']}`", r["lang"]]
        cells += [_cell(r["_nums"].get(key), kind) for (_, key, kind) in _COLS]
        cells.append(r["error"])
        out.append("| " + " | ".join(cells) + " |")
    out.append("")

    n_err = sum(1 for r in rows if r["error"] != "—")
    n_model = sum(1 for r in rows if r["fclass"] == "model")
    n_infra = sum(1 for r in rows if r["fclass"] == "infra")
    out.append("## Averages")
    out.append("")
    out.append(f"Mean of each per-repo value over the repos that have one (`n`). "
               f"Repos with errors: {n_err}/{len(rows)}  |  "
               f"model-side failures scored 0% (in denominator): {n_model}  |  "
               f"infra failures excluded (retest-eligible): {n_infra}.")
    out.append("")
    out.extend(_averages_table(rows))
    out.append("")
    return "\n".join(out)


def write_summary(append_id: str, out_path: Path | None = None) -> Path:
    md = render(append_id)
    if out_path is None:
        out_path = C.RESULTS / append_id / "summary.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Write per-repo Markdown summary for an eval run.")
    ap.add_argument("--append-id", required=True)
    ap.add_argument("--out", default=None, help="output path (default results/<id>/summary.md)")
    args = ap.parse_args()
    path = write_summary(args.append_id, Path(args.out) if args.out else None)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
