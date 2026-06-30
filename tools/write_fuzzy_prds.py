#!/usr/bin/env python3
"""Regenerate the raw fuzzy-PRD trees from the User Agent's prd_json sources.

For each task JSON in the chosen prd_json* dir, write:
    <fuzzy_prds*>/<alias>/start.md  =  "## Product Requirement Document\n\n" + fuzzy_prd

All paths are resolved RELATIVE to the repo root (the parent of this tools/ dir),
so the release is location-independent.

Difficulty -> (source, destination):
    normal  user_agent/prd_json        -> fuzzy_prds
    medium  user_agent/prd_json_medium -> fuzzy_prds_medium
    easy    user_agent/prd_json_easy   -> fuzzy_prds_easy

Usage:
    python tools/write_fuzzy_prds.py [--difficulty normal|medium|easy|all]
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEADER = "## Product Requirement Document\n\n"

DIFFICULTY = {
    "normal": ("user_agent/prd_json",        "fuzzy_prds"),
    "medium": ("user_agent/prd_json_medium", "fuzzy_prds_medium"),
    "easy":   ("user_agent/prd_json_easy",   "fuzzy_prds_easy"),
}


def generate(difficulty: str) -> None:
    src_rel, dst_rel = DIFFICULTY[difficulty]
    src_dir = ROOT / src_rel
    dst_root = ROOT / dst_rel
    written, skipped = 0, []
    for json_file in sorted(src_dir.glob("*.json")):
        alias = json_file.stem
        data = json.loads(json_file.read_text(encoding="utf-8"))
        fuzzy_prd = data.get("fuzzy_prd")
        if not fuzzy_prd:
            skipped.append(alias)
            continue
        dst_dir = dst_root / alias
        dst_dir.mkdir(parents=True, exist_ok=True)
        (dst_dir / "start.md").write_text(HEADER + fuzzy_prd, encoding="utf-8")
        written += 1
    print(f"[{difficulty}] wrote {written} start.md file(s) to {dst_root}")
    if skipped:
        print(f"[{difficulty}] skipped {len(skipped)} without fuzzy_prd: {skipped}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--difficulty", default="all",
                    choices=["normal", "medium", "easy", "all"])
    args = ap.parse_args()
    targets = list(DIFFICULTY) if args.difficulty == "all" else [args.difficulty]
    for d in targets:
        generate(d)


if __name__ == "__main__":
    main()
