"""Resolve and build the PRD that the agent-under-test will receive.

Two PRD types:
  - detailed: the self-contained detailed_prds/<alias>/start.md (no Oracle).
  - fuzzy:    fuzzy_prds/<alias>/start.md (intentionally incomplete) + the
              fuzzy_suffix.md Clarification block, with {host}/{query_port}/
              {append_id}/{task_id} substituted so the agent knows how to reach
              the Oracle. The complete PRD is written to
              fuzzy_prds@<user_model_name>@query_<query_count>/<alias>/start.md
              (refreshed every run) and that text is returned.

`<alias>` is the anonymous 'realcode@NNN' id; the agent never sees the real repo
name (which would let it search GitHub for the reference implementation). The
Oracle is addressed by `task_id=alias` for the same reason.
"""
from pathlib import Path

from . import config as C


def _read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"PRD source not found: {path}")
    return path.read_text(encoding="utf-8")


def build_fuzzy_prd(alias: str, *, append_id: str, user_host: str,
                    user_query_port: int, user_model_name: str,
                    query_count: int, difficulty: str = "normal") -> tuple[str, Path]:
    """Compose raw fuzzy PRD + filled suffix, persist it, return (text, out_path)."""
    raw = _read(C.fuzzy_prds_dir(difficulty) / alias / "start.md")
    suffix_tmpl = _read(C.FUZZY_SUFFIX_FILE)
    # fuzzy_suffix.md uses str.format placeholders; literal JSON braces are {{ }}.
    suffix = suffix_tmpl.format(
        host=user_host,
        query_port=user_query_port,
        append_id=append_id,
        task_id=alias,
    )
    full = raw.rstrip() + "\n\n" + suffix.lstrip()

    out_dir = C.fuzzy_out_dir(user_model_name, query_count, difficulty) / alias
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "start.md"
    out_path.write_text(full, encoding="utf-8")
    return full, out_path


def build_detailed_prd(alias: str) -> tuple[str, Path]:
    src = C.DETAILED_PRDS / alias / "start.md"
    return _read(src), src


def resolve_prd(alias: str, *, prd_type: str, append_id: str, user_host: str,
                user_query_port: int, user_model_name: str,
                query_count: int, difficulty: str = "normal") -> str:
    """Return the final PRD text (start.md) for an alias under the given prd_type."""
    if prd_type == "fuzzy":
        text, _ = build_fuzzy_prd(
            alias, append_id=append_id, user_host=user_host,
            user_query_port=user_query_port, user_model_name=user_model_name,
            query_count=query_count, difficulty=difficulty,
        )
        return text
    if prd_type == "detailed":
        text, _ = build_detailed_prd(alias)
        return text
    raise ValueError(f"unknown prd_type: {prd_type!r} (expected fuzzy|detailed)")
