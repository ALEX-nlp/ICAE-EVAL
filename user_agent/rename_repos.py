"""Rename realcode_repos subdirectories from {username}__{repo_name} to realcode@NNN.

Usage:
    python rename_repos.py [--dry-run]

With --dry-run, prints what would be renamed without touching the filesystem.

Paths default to the repo layout (realcode_repos/ and repo_alias.json under the
repo root) and can be overridden with env vars ICAE_GOLDEN_REPOS_DIR and
ICAE_ALIAS_FILE.
"""

import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
REPOS_DIR  = Path(os.environ.get("ICAE_GOLDEN_REPOS_DIR", str(_ROOT / "realcode_repos")))
ALIAS_PATH = Path(os.environ.get("ICAE_ALIAS_FILE", str(_ROOT / "repo_alias.json")))


def main(dry_run: bool) -> None:
    alias_map = json.loads(ALIAS_PATH.read_text(encoding="utf-8"))
    # key (username__repo_name) -> realcode@NNN
    key_to_alias = {v["key"]: k for k, v in alias_map.items()}

    dirs = sorted(d for d in REPOS_DIR.iterdir() if d.is_dir())
    renamed = skipped = unknown = 0

    for d in dirs:
        name = d.name
        if name not in key_to_alias:
            print(f"[UNKNOWN ] {name}  (no alias entry, skipped)")
            unknown += 1
            continue

        new_name = key_to_alias[name]
        dst = REPOS_DIR / new_name

        if dst.exists():
            print(f"[SKIP    ] {name}  ->  {new_name}  (target already exists)")
            skipped += 1
            continue

        print(f"[RENAME  ] {name}  ->  {new_name}")
        if not dry_run:
            d.rename(dst)
        renamed += 1

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}renamed={renamed}  skipped={skipped}  unknown={unknown}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print actions without renaming")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
