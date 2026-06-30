"""Structural Assessment — metric group (b) of task.md.

Reuses the per-language extractors from analyze.py (vendored next to this module,
the same script that produces objective.json in the build pipeline) so the numbers
are identical to the rest of ICAE-Bench. We only keep the three task.md metrics:

  - File Count / LOC   -> scale.{generated_src_files, generated_src_loc,
                                  orig_src_files, orig_src_loc, loc_coverage_ratio}
  - Class Similarity   -> class_match_rate   (orig class-like names ∩ generated)
  - Method Similarity  -> method_match_rate  (orig method names ∩ generated)

Comparison is generated tree (results/<append_id>/<alias>) vs the GOLDEN original
source at <GOLDEN_REPOS_DIR>/<real_key>. Everything is host-side; the agent never
sees the golden source or the real repo name.
"""
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from . import config as C

# Import the authoritative extractors (regex/AST parsers per language) instead of
# re-implementing them. analyze.py is vendored alongside this harness and imports
# cleanly (no side effects on import).
_ANALYSIS_DIR = C.HARNESS
if str(_ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(_ANALYSIS_DIR))
import analyze as _analyze  # noqa: E402

GOLDEN_ORIG_ROOT = C.GOLDEN_REPOS_DIR
REPOS_YAML = _ANALYSIS_DIR / "repos.yaml"

_YAML_CACHE: dict | None = None


def _repo_entry(real_key: str) -> dict | None:
    """Look up the repos.yaml entry (carries in_scope) by real repo key.

    repos.yaml is keyed by repo_id 'username/repo'; our key is 'username__repo'.
    Returns None when the repo isn't in the build manifest (≈115 of 480) — the
    caller then falls back to a whole-tree scan.
    """
    global _YAML_CACHE
    if _YAML_CACHE is None:
        doc = yaml.safe_load(REPOS_YAML.read_text(encoding="utf-8"))
        _YAML_CACHE = {e["repo_id"]: e for e in doc.get("repos", [])}
    u, _, r = real_key.partition("__")
    return _YAML_CACHE.get(f"{u}/{r}")


def _canon_extractor(language: str):
    """(ext, extractor_fn) for a canonical/lowercased language label, or None."""
    lang = language if language in _analyze.EXTRACTORS else None
    if lang is None:
        canon = {k.lower(): k for k in _analyze.EXTRACTORS}
        lang = canon.get((language or "").strip().lower())
    if lang is None:
        return None
    return _analyze.EXTRACTORS[lang]


def _whole_tree_files(root: Path, ext: str) -> list[Path]:
    """Fallback file collection: every *.<ext> under root minus non-source dirs."""
    out: list[Path] = []
    if not root.is_dir():
        return out
    for p in root.rglob(f"*.{ext}"):
        if not p.is_file():
            continue
        if any(part in _analyze.NON_SOURCE_DIRS for part in p.relative_to(root).parts):
            continue
        n = p.name.lower()
        if any(n.endswith(s) for s in (f"test.{ext}", f"tests.{ext}", f"_test.{ext}",
                                       f"_spec.{ext}", f"spec.{ext}")):
            continue
        out.append(p)
    return out


def _collect(root: Path, in_scope: dict | None, ext: str, key_prefix: str) -> list[Path]:
    """in_scope-driven collection (matches analyze.py), with whole-tree fallback."""
    files: list[Path] = []
    if in_scope:
        files = _analyze.collect_files(root, in_scope, ext, key_prefix)
    if not files:
        files = _whole_tree_files(root, ext)
    return files


def _rate(matched: int, total: int) -> float:
    return round(matched / total, 4) if total else 1.0


def evaluate_structural(append_id: str, alias: str, env_mode: str = "") -> dict:
    """Compute metric group (b) for one generated repo; write & return structural.json.

    Cross-language aware: the GOLDEN tree is read with the repo's ORIGINAL language
    extractor, while the GENERATED tree is read with the TARGET language extractor
    (C.prompt_language — e.g. Python when env_mode=Python). In same-language modes
    (base/ultimate/"") both resolve to the same language, so behavior is unchanged.
    """
    real_key = C.key_for_alias(alias)
    orig_lang = C.repo_language(alias)
    gen_lang = C.prompt_language(env_mode, alias)
    gen_root = C.code_path(append_id, alias)
    orig_root = GOLDEN_ORIG_ROOT / real_key
    eval_dir = C.RESULTS / append_id / "_eval" / alias
    eval_dir.mkdir(parents=True, exist_ok=True)
    out_path = eval_dir / "structural.json"

    orig_ext_extractor = _canon_extractor(orig_lang)
    gen_ext_extractor = _canon_extractor(gen_lang)
    if orig_ext_extractor is None or gen_ext_extractor is None:
        missing = orig_lang if orig_ext_extractor is None else gen_lang
        res = {"repo": alias, "error": f"no extractor for language {missing!r}"}
        out_path.write_text(_dump(res), encoding="utf-8")
        return res
    ext_o, extractor_o = orig_ext_extractor
    ext_g, extractor_g = gen_ext_extractor

    if not orig_root.is_dir():
        res = {"repo": alias, "error": f"golden source missing: {orig_root}"}
        out_path.write_text(_dump(res), encoding="utf-8")
        return res

    entry = _repo_entry(real_key) or {}
    in_scope = entry.get("in_scope")

    # Authoritative original scale comes from the pre-computed stats in
    # repo_alias.json (total_code_files / total_lines_of_code), NOT from walking
    # the golden cache: that cache is pruned (.git/build/vendor/... stripped) and
    # the language extractor only sees one extension, so a re-walk under-counts
    # the true repo size. The golden source is still read below for class/method
    # name extraction, which the stats file does not provide.
    arec = C.alias_record(alias)
    orig_files_count = arec.get("total_code_files")
    orig_loc_count = arec.get("total_lines_of_code")

    orig_files = _collect(orig_root, in_scope, ext_o, "original")
    gen_present = gen_root.is_dir() and any(gen_root.iterdir())
    gen_files = _collect(gen_root, in_scope, ext_g, "generated") if gen_present else []

    orig = extractor_o(orig_files) if orig_files else _analyze.Extracted()
    gen = extractor_g(gen_files) if gen_files else _analyze.Extracted()

    orig_class_like = orig.classes | orig.modules
    gen_class_like = gen.classes | gen.modules
    orig_methods = orig.class_methods | orig.instance_methods
    gen_methods = gen.class_methods | gen.instance_methods

    class_match_rate = _rate(len(orig_class_like & gen_class_like), len(orig_class_like))
    method_match_rate = _rate(len(orig_methods & gen_methods), len(orig_methods))

    res = {
        "repo": alias,
        "language": orig_lang,
        "orig_language": orig_lang,
        "gen_language": gen_lang,
        "scale": {
            "generated_src_files": gen.files if gen_present else None,
            "generated_src_loc": gen.loc if gen_present else None,
            "orig_src_files": orig_files_count,
            "orig_src_loc": orig_loc_count,
            "loc_coverage_ratio": round(gen.loc / orig_loc_count, 4)
            if (gen_present and orig_loc_count) else None,
        },
        "class_similarity": class_match_rate,
        "method_similarity": method_match_rate,
        "notes": {
            "matched_class_like": len(orig_class_like & gen_class_like),
            "orig_class_like": len(orig_class_like),
            "matched_methods": len(orig_methods & gen_methods),
            "orig_methods": len(orig_methods),
            "used_in_scope": bool(in_scope),
        },
    }
    out_path.write_text(_dump(res), encoding="utf-8")
    return res


def _dump(obj: dict) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False, indent=2)
