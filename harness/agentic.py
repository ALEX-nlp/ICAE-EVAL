"""Agentic Evaluation — metric group (c) of task.md.

Runs the **Critic Model** (model_list.json['Critic Model'], default
"Deepseek-V4-Flash") as a static code reviewer that compares the GOLDEN original
source against the generated tree and emits three INDEPENDENT 0-1 scores into
subjective.json:

  - Semantic Similarity -> semantic_similarity   (observable behavior)
  - API Similarity      -> api_similarity         (public surface)
  - Design Quality      -> design_quality         (engineering quality)

semantic_similarity is its own standalone score (kept separate from
api_similarity) per the 2026-06-16 decision.

Performance: the critic is a SINGLE Messages-API call with the in-scope source
pre-packed into the prompt and `tool_choice` forcing the `submit_review` tool, so
the three scores come back as a guaranteed, schema-validated JSON object — no
multi-turn agent loop, no filesystem exploration, no regex scraping of free text.
"""
import json
from pathlib import Path

from anthropic import AsyncAnthropic, APIStatusError, APIError

from . import config as C
from . import structural as struct
from .critic_pool import CriticPool

AGENTIC_TEMPLATE = C.HARNESS / "prompt_templates" / "task_agentic.md"
GOLDEN_ORIG_ROOT = struct.GOLDEN_ORIG_ROOT

# Context budget for the packed source (CHARS). The model window is ~1024K tokens
# (~4M chars); we strip comments/blank-lines first (functional code only) so even a
# ~60k-LOC repo mostly fits. Budget is PER TREE — original and generated each get
# their own TOTAL_CHARS so a big original can't starve the generated side.
PER_FILE_CHARS = 120_000
TOTAL_CHARS = 1_400_000   # per tree; orig + gen together stay well under the window
MAX_FILES = 400
HARD_STATUS = {400, 401, 402, 403, 404}  # permanent: bad request / auth / balance

# Line-comment + block-comment markers by file extension. Used to drop comments,
# docstrings and blank lines so only functional code is packed into the prompt.
_LINE_COMMENT = {
    "py": "#", "rb": "#", "sh": "#", "pl": "#", "r": "#", "yaml": "#", "yml": "#",
    "js": "//", "ts": "//", "jsx": "//", "tsx": "//", "java": "//", "kt": "//",
    "go": "//", "rs": "//", "c": "//", "h": "//", "cpp": "//", "cc": "//",
    "hpp": "//", "cs": "//", "php": "//", "swift": "//", "scala": "//", "dart": "//",
}
_BLOCK_COMMENT = {  # (open, close)
    "js": ("/*", "*/"), "ts": ("/*", "*/"), "jsx": ("/*", "*/"), "tsx": ("/*", "*/"),
    "java": ("/*", "*/"), "kt": ("/*", "*/"), "go": ("/*", "*/"), "rs": ("/*", "*/"),
    "c": ("/*", "*/"), "h": ("/*", "*/"), "cpp": ("/*", "*/"), "cc": ("/*", "*/"),
    "hpp": ("/*", "*/"), "cs": ("/*", "*/"), "php": ("/*", "*/"), "swift": ("/*", "*/"),
    "scala": ("/*", "*/"), "dart": ("/*", "*/"),
}


def _strip_noise(text: str, ext: str) -> str:
    """Drop blank lines and comments (best-effort, syntax-unaware) so only
    functional code is packed. Conservative: never touches a line that has code
    before the comment marker, so inline trailing comments keep their code."""
    line_c = _LINE_COMMENT.get(ext)
    block = _BLOCK_COMMENT.get(ext)
    out: list[str] = []
    in_block = False
    bo, bc = block if block else ("\0", "\0")
    for raw in text.splitlines():
        s = raw.strip()
        if in_block:
            if bc in s:
                in_block = False
                s = s.split(bc, 1)[1].strip()
                if not s:
                    continue
            else:
                continue
        if not s:
            continue
        if block and s.startswith(bo):
            if bc not in s[len(bo):]:
                in_block = True
            continue
        if line_c and s.startswith(line_c):
            continue
        out.append(raw.rstrip())
    return "\n".join(out)

# The single tool the critic is forced to call. tool_choice pins it, so the model
# MUST return arguments matching this schema — that is the JSON guarantee.
SCORE_TOOL = {
    "name": "submit_review",
    "description": "Submit the three independent 0..1 code-review scores with rationales.",
    "input_schema": {
        "type": "object",
        "properties": {
            "semantic_similarity": {"type": "number", "minimum": 0, "maximum": 1},
            "semantic_similarity_rationale": {"type": "string"},
            "api_similarity": {"type": "number", "minimum": 0, "maximum": 1},
            "api_similarity_rationale": {"type": "string"},
            "design_quality": {"type": "number", "minimum": 0, "maximum": 1},
            "design_quality_rationale": {"type": "string"},
        },
        "required": ["semantic_similarity", "api_similarity", "design_quality"],
    },
}


def _coerce_score(v) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return round(max(0.0, min(1.0, float(v))), 4)
    return None


def _read_files(files: list[Path], root: Path, ext: str) -> str:
    """Concatenate readable source files under a char budget, after stripping
    comments and blank lines so only functional code counts toward the budget."""
    parts: list[str] = []
    used = 0
    for p in files[:MAX_FILES]:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        text = _strip_noise(text, ext)
        if len(text) > PER_FILE_CHARS:
            text = text[:PER_FILE_CHARS] + "\n...<truncated>\n"
        try:
            rel = p.relative_to(root)
        except ValueError:
            rel = p.name
        block = f"\n--- {rel} ---\n{text}\n"
        if used + len(block) > TOTAL_CHARS:
            break
        parts.append(block)
        used += len(block)
    return "".join(parts) if parts else "(no readable source files)"


def _pack_source(real_key: str, orig_root: Path, gen_root: Path,
                 env_mode: str = "") -> str:
    """Collect in-scope source from both trees (reusing the structural extractors
    for file selection) and render it into one prompt section.

    Cross-language aware: the GOLDEN tree is selected/stripped with the ORIGINAL
    language extension, the GENERATED tree with the TARGET language extension
    (C.prompt_language — Python in cross-language mode). Same-language modes
    resolve both to the same extension, so behavior is unchanged.
    """
    alias = C.alias_for_key(real_key)
    orig_lang = C.repo_language(alias)
    gen_lang = C.prompt_language(env_mode, alias)
    orig_ee = struct._canon_extractor(orig_lang)
    gen_ee = struct._canon_extractor(gen_lang)
    entry = struct._repo_entry(real_key) or {}
    in_scope = entry.get("in_scope")
    ext_o = orig_ee[0] if orig_ee is not None else ""
    ext_g = gen_ee[0] if gen_ee is not None else ""
    orig_files = struct._collect(orig_root, in_scope, ext_o, "original") if orig_ee else []
    gen_files = struct._collect(gen_root, in_scope, ext_g, "generated") if gen_ee else []
    return (f"## ORIGINAL (reference) source — {orig_root.name}\n"
            f"{_read_files(orig_files, orig_root, ext_o)}\n"
            f"## GENERATED source (under review)\n"
            f"{_read_files(gen_files, gen_root, ext_g)}\n")


def _build_prompt(alias: str, packed: str) -> str:
    """The scoring rubric from the template, minus the filesystem-exploration and
    write-a-file instructions (the tool handles output), plus the packed source."""
    rubric = AGENTIC_TEMPLATE.read_text(encoding="utf-8")
    return (
        f"{rubric}\n\n"
        f"---\n\n"
        f"Repo id: {alias}\n\n"
        f"The in-scope source of BOTH trees is provided inline below. Do a static "
        f"review (do not run the code) and call the `submit_review` tool exactly "
        f"once with the three independent 0..1 scores and short rationales.\n\n"
        f"{packed}"
    )


def _classify(status_code: int | None) -> str:
    """Map an HTTP status to the pool's transient/permanent contract."""
    if status_code in HARD_STATUS:
        return "dead"
    return "retry"  # 429, 5xx, network/timeout -> cool down and retry


async def evaluate_agentic(append_id: str, alias: str,
                           critic: "dict | list[dict] | CriticPool",
                           *, env_mode: str = "", timeout: float = 180) -> dict:
    """Run the Critic Model review via a single forced-tool-use call; write &
    return the three agentic scores.

    Writes subjective.json (scores + rationales) and returns a compact dict with
    semantic_similarity / api_similarity / design_quality (+ critic_status,
    critic_label).
    """
    real_key = C.key_for_alias(alias)
    orig_root = GOLDEN_ORIG_ROOT / real_key
    gen_root = C.code_path(append_id, alias)
    eval_dir = C.RESULTS / append_id / "_eval" / alias
    eval_dir.mkdir(parents=True, exist_ok=True)
    subj_path = eval_dir / "subjective.json"

    summary = {"repo": alias, "semantic_similarity": None,
               "api_similarity": None, "design_quality": None}

    if not orig_root.is_dir():
        summary["error"] = f"golden source missing: {orig_root}"
        subj_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary
    if not (gen_root.is_dir() and any(gen_root.iterdir())):
        summary["error"] = "generated tree missing/empty"
        subj_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary

    packed = _pack_source(real_key, orig_root, gen_root, env_mode)
    prompt = _build_prompt(alias, packed)

    pool = critic if isinstance(critic, CriticPool) else CriticPool.from_entries(
        critic if isinstance(critic, list) else [critic])

    async def _call(entry: dict):
        client = AsyncAnthropic(
            base_url=entry["ANTHROPIC_BASE_URL"].rstrip("/"),
            auth_token=entry["ANTHROPIC_AUTH_TOKEN"],
            timeout=timeout,
        )
        try:
            msg = await client.messages.create(
                model=entry["ANTHROPIC_MODEL"],
                max_tokens=1500,
                tools=[SCORE_TOOL],
                tool_choice={"type": "tool", "name": "submit_review"},
                messages=[{"role": "user", "content": prompt}],
            )
        except APIStatusError as e:
            return _classify(e.status_code), None, f"{e.status_code}: {str(e)[:120]}"
        except APIError as e:
            return "retry", None, f"apierror: {str(e)[:120]}"
        except Exception as e:  # noqa: BLE001 — network/timeout
            return "retry", None, f"{type(e).__name__}: {str(e)[:120]}"

        data = next((b.input for b in msg.content
                     if getattr(b, "type", None) == "tool_use"), None)
        if not isinstance(data, dict):
            return "retry", None, f"no tool_use (stop={msg.stop_reason})"
        scores = {
            "semantic_similarity": _coerce_score(data.get("semantic_similarity")),
            "api_similarity": _coerce_score(data.get("api_similarity")),
            "design_quality": _coerce_score(data.get("design_quality")),
        }
        if not any(v is not None for v in scores.values()):
            return "retry", None, "tool returned no numeric scores"
        return "ok", (scores, data), ""

    value, info = await pool.run(_call)
    if value is None:
        summary["critic_status"] = "error"
        summary["error"] = f"all critic endpoints failed: {info}"
        subj_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary

    scores, data = value
    summary.update(scores)
    summary["critic_status"] = "ok"
    summary["critic_label"] = info
    # Persist the full critic JSON (scores + rationales) for auditing.
    record = {"repo_id": alias, "subjective": data}
    subj_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
