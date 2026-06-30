"""Shared config + path resolution for the ICAE-Bench eval harness.

Centralizes:
  - filesystem paths (PRDs, results, docker tars, authoritative test cases)
  - model_list.json lookup (model_name -> ANTHROPIC_* env for the SUT model)
  - user_model.json (the User Agent / Oracle model labels)
  - repo -> language mapping (from repo_alias.json)
  - env_mode -> docker tar resolution (base / ultimate / <language>)

All filesystem roots are resolved RELATIVE to the repo root (the parent of this
harness/ dir) so the project is location-independent. The data roots that hold
large downloaded artifacts (golden source, authoritative tests, base-image tars)
can additionally be overridden with environment variables — handy when those
tars are unpacked outside the repo tree:

  ICAE_GOLDEN_REPOS_DIR   golden ORIGINAL source root (realcode_repos.tar.lz4)
  ICAE_RCB_TESTS_DIR      authoritative test root      (rcb_tests tar)
  ICAE_DOCKER_LANG_DIR    base-image tars              (download_scaffold.sh out)
  ICAE_SANDBOX_IMGS_DIR   per-repo ultimate sandbox images (optional)
  ICAE_CLAUDE_CLI         path to the `claude` CLI binary (default: on $PATH)
"""
import json
import os
import tarfile
from pathlib import Path


def _root_dir(env_var: str, default: Path) -> Path:
    """Resolve a data root: env override (abs or repo-relative) else default."""
    v = os.environ.get(env_var)
    if not v:
        return default
    p = Path(v)
    return p if p.is_absolute() else (ROOT / v)


# ── roots ─────────────────────────────────────────────────────────────────────
# Repo root = parent of this harness/ directory. No absolute paths baked in.
ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "harness"
RESULTS = ROOT / "results"
# Registry: append_id -> experiment config ONLY (no per-repo data). This is the
# index that maps each append_id to what experiment it was. Per-repo results live
# in each run's own results/<append_id>/settings.json so a per-repo backfill can
# never clobber the registry or another run's data.
SETTINGS_FILE = RESULTS / "settings.json"


def run_settings_path(append_id: str) -> Path:
    """Per-run settings file: results/<append_id>/settings.json (repos + config)."""
    return RESULTS / append_id / "settings.json"

FUZZY_PRDS = ROOT / "fuzzy_prds"
FUZZY_PRDS_EASY = ROOT / "fuzzy_prds_easy"  # simplified PRDs, difficulty=easy
FUZZY_PRDS_MEDIUM = ROOT / "fuzzy_prds_medium"  # mid-detail PRDs, difficulty=medium
DETAILED_PRDS = ROOT / "detailed_prds"
# Optional override for the detailed-PRD source dir. Lets a C3-style ablation
# (fuzzy_prd + oracle_data, no Oracle) point at detailed_prds_oracle/ without
# touching the real ground-truth detailed_prds/. Set DETAILED_PRDS_DIR to a dir
# name (resolved under ROOT) or an absolute path.
_detailed_override = os.environ.get("DETAILED_PRDS_DIR")
if _detailed_override:
    _p = Path(_detailed_override)
    DETAILED_PRDS = _p if _p.is_absolute() else (ROOT / _detailed_override)

_FUZZY_PRDS_BY_DIFFICULTY = {
    "easy": FUZZY_PRDS_EASY,
    "medium": FUZZY_PRDS_MEDIUM,
}


def fuzzy_prds_dir(difficulty: str = "normal") -> Path:
    """Root dir of raw fuzzy PRDs for the given difficulty."""
    return _FUZZY_PRDS_BY_DIFFICULTY.get(difficulty, FUZZY_PRDS)
MODEL_LIST_FILE = ROOT / "model_list.json"
TASK_TEMPLATE = HARNESS / "prompt_templates" / "task_docker.md"

# Anonymization map: realcode@NNN -> {key, username, repo_name, language, ...}.
# Single source of truth shared with user_agent. The agent-under-test only ever
# sees the alias; the harness translates alias<->real key internally.
ALIAS_FILE = ROOT / "repo_alias.json"

# ── user-agent (Oracle) side ──────────────────────────────────────────────────
# In the release, the User Agent lives inside the repo (user_agent/).
USER_AGENT_DIR = ROOT / "user_agent"
FUZZY_SUFFIX_FILE = USER_AGENT_DIR / "fuzzy_suffix.md"
USER_MODEL_FILE = USER_AGENT_DIR / "user_model.json"
# Demo init key (matches user_agent/main.py INIT_KEY). The harness holds it;
# the agent-under-test never sees it. Override both sides for a real deployment.
INIT_KEY = "zVtwLTkCKwoCWq4Jq9D2"

# ── docker images ─────────────────────────────────────────────────────────────
# Base-language images produced by download_scaffold.sh (`docker save` of the
# upstream Docker Hub images). Default: docker_lang_official/ under the repo.
DOCKER_LANG_DIR = _root_dir("ICAE_DOCKER_LANG_DIR", ROOT / "docker_lang_official")
# Per-repo "ultimate" sandbox images (optional; not shipped with the base-only
# release). Override with ICAE_SANDBOX_IMGS_DIR if you build them yourself.
SANDBOX_IMGS_DIR = _root_dir("ICAE_SANDBOX_IMGS_DIR", ROOT / "clean_sandbox_docker_imgs")

# ── golden source + authoritative test cases (two independent data roots) ─────
# 1) Golden ORIGINAL source tree (realcode_repos.tar.lz4), read host-side only for
#    structural/agentic scoring. Layout: <GOLDEN_REPOS_DIR>/<username__repo>/...
GOLDEN_REPOS_DIR = _root_dir("ICAE_GOLDEN_REPOS_DIR", ROOT / "realcode_repos")
# 2) Authoritative test cases (separate rcb_tests tar). Layout:
#    <REPOS_DIR>/<username__repo>/rcb_tests/{public_test_cases,test_cases,enhanced_test_cases}
REPOS_DIR = _root_dir("ICAE_RCB_TESTS_DIR", ROOT / "rcb_tests_repos")

# ── claude CLI ────────────────────────────────────────────────────────────────
# Path to the `claude` CLI binary used by the claude-code runner. Default assumes
# it is on $PATH; override with ICAE_CLAUDE_CLI for a pinned install.
CLI_PATH = os.environ.get("ICAE_CLAUDE_CLI", "claude")

# Canonical language label -> internal tar key. Accepts common aliases / casings.
LANG_CANON = {
    "python": "Python", "java": "Java", "go": "Go", "golang": "Go",
    "rust": "Rust", "ruby": "Ruby", "php": "PHP", "dart": "Dart",
    "kotlin": "Kotlin", "javascript": "JavaScript", "js": "JavaScript",
    "typescript": "TypeScript", "ts": "TypeScript",
    "cpp": "Cpp", "c++": "Cpp", "csharp": "CSharp", "c#": "CSharp", "cs": "CSharp",
}

# Canonical language -> official-image tar FILENAME as produced by
# docker_lang_official/download.sh (`docker save` of the upstream image, name =
# image ref with '/' and ':' turned into '_'). Kept as an internal map so users
# can drop the freshly-downloaded tars in DOCKER_LANG_DIR *without renaming them*.
# JavaScript and TypeScript intentionally share the one Node image.
LANG_TAR = {
    "Python": "python_3.11.tar",
    "Java": "eclipse-temurin_17.tar",
    "Go": "golang_1.22.tar",
    "Rust": "rust_1.81.tar",
    "Ruby": "ruby_3.2.tar",
    "PHP": "php_8.2.tar",
    "Dart": "dart_3.5.tar",
    "Kotlin": "kotlin_1.9.25.tar",
    "JavaScript": "node_20.tar",
    "TypeScript": "node_20.tar",
    "Cpp": "gcc_12.tar",
    "CSharp": "dotnet_sdk_8.0.tar",
}


def canon_lang(lang: str) -> str:
    """Normalize an arbitrary language label to a canonical tar key."""
    return LANG_CANON.get((lang or "").strip().lower(), lang)


def lang_tar_path(lang: str) -> Path:
    """Canonical language -> base-image tar Path under DOCKER_LANG_DIR.

    Resolves via the LANG_TAR filename map (no on-disk renaming needed). If the
    pinned version filename is absent, fall back to the same prefix with any
    version (e.g. 'python_3.11.tar' -> 'python_*.tar') so a patch-version bump in
    download.sh still resolves without editing this map.
    """
    fname = LANG_TAR.get(lang)
    if not fname:
        raise ValueError(f"no base-image tar mapping for language '{lang}'")
    exact = DOCKER_LANG_DIR / fname
    if exact.exists():
        return exact
    prefix = fname.rsplit("_", 1)[0]  # 'python_3.11.tar' -> 'python'
    matches = sorted(DOCKER_LANG_DIR.glob(f"{prefix}_*.tar"))
    if matches:
        return matches[0]
    return exact  # non-existent; caller surfaces a clear error


def split_key(repo_key: str):
    """'Ahoo-Wang__Wow' -> ('Ahoo-Wang', 'Wow')  (username, repo_name)."""
    u, _, r = repo_key.partition("__")
    return u, r


# ── alias <-> real key (anonymization) ───────────────────────────────────────
_ALIAS_CACHE: dict | None = None
_KEY_TO_ALIAS_CACHE: dict | None = None


def _load_alias() -> dict:
    """alias record map: {'realcode@001': {key, username, repo_name, language,...}}."""
    global _ALIAS_CACHE, _KEY_TO_ALIAS_CACHE
    if _ALIAS_CACHE is None:
        _ALIAS_CACHE = json.loads(ALIAS_FILE.read_text(encoding="utf-8"))
        _KEY_TO_ALIAS_CACHE = {rec["key"]: aid for aid, rec in _ALIAS_CACHE.items()}
    return _ALIAS_CACHE


def alias_record(alias: str) -> dict:
    """Full record for an alias (raises KeyError if unknown)."""
    rec = _load_alias().get(alias)
    if rec is None:
        raise KeyError(f"unknown alias '{alias}' (not in {ALIAS_FILE.name})")
    return rec


def key_for_alias(alias: str) -> str:
    """'realcode@001' -> real 'username__repo_name' (for tars + authoritative tests)."""
    return alias_record(alias)["key"]


def alias_for_key(key: str) -> str:
    """Real 'username__repo_name' -> 'realcode@NNN' (raises KeyError if unknown)."""
    _load_alias()
    aid = _KEY_TO_ALIAS_CACHE.get(key)
    if aid is None:
        raise KeyError(f"no alias for repo key '{key}'")
    return aid


def resolve_alias(token: str) -> str:
    """Accept either an alias ('realcode@001') or a real key; return the alias."""
    if token.startswith("realcode@"):
        return token
    return alias_for_key(token)


def docker_safe(alias: str) -> str:
    """'realcode@001' -> 'realcode_001'  (Docker names/tags forbid '@')."""
    return alias.replace("@", "_")


# ── model_list.json (SUT + Critic models) ───────────────────────────────────
# Structure (per task.md): each model name maps to ONE endpoint dict OR a LIST of
# interchangeable endpoint dicts (a pool of same-model variants):
#   {"Tested Model": {<name>: [{ANTHROPIC_*[, OPENHANDS_*]}, ...]},
#    "Critic Model": {<name>: [{ANTHROPIC_*}, ...]}}
def load_model_list() -> dict:
    return json.loads(MODEL_LIST_FILE.read_text(encoding="utf-8"))


def _resolve_in_section(model_name: str, section: str) -> dict:
    ml = load_model_list()
    table = ml.get(section, {})
    if model_name not in table:
        raise KeyError(
            f"model_name '{model_name}' not in {MODEL_LIST_FILE} ['{section}'] "
            f"(available: {sorted(table)})"
        )
    return table[model_name]


def resolve_model(model_name: str) -> list[dict]:
    """SUT model_name -> a LIST of interchangeable endpoint variants (same model,
    different provider/token/framework routing), from model_list.json['Tested Model'].

    Mirrors resolve_critic_model: the JSON value may be a single dict (one endpoint)
    or a list of dicts (a pool to spread load across). Always returns a list so
    callers can round-robin uniformly. Each entry carries ANTHROPIC_* (used by the
    claude-code runner) and may also carry OPENHANDS_* (used by the openhands
    runner); the runner picks the right fields for its framework.
    """
    entry = _resolve_in_section(model_name, "Tested Model")
    if isinstance(entry, dict):
        return [entry]
    if isinstance(entry, list):
        return [e for e in entry if isinstance(e, dict)]
    raise TypeError(f"Tested Model '{model_name}' must be a dict or list, got {type(entry)}")


def resolve_critic_model(model_name: str) -> list[dict]:
    """Critic (Agentic-eval) model_name -> a LIST of interchangeable endpoint
    variants (same model, different provider/token), from
    model_list.json['Critic Model'].

    The JSON value may be a single dict (one endpoint) or a list of dicts (a pool
    of equivalent endpoints to round-robin over). Always returns a list so callers
    can build a CriticPool uniformly.
    """
    entry = _resolve_in_section(model_name, "Critic Model")
    if isinstance(entry, dict):
        return [entry]
    if isinstance(entry, list):
        return [e for e in entry if isinstance(e, dict)]
    raise TypeError(f"Critic Model '{model_name}' must be a dict or list, got {type(entry)}")


def load_user_models() -> dict:
    return json.loads(USER_MODEL_FILE.read_text(encoding="utf-8"))


# ── repo -> language ─────────────────────────────────────────────────────────
def repo_language(alias: str) -> str:
    """Canonical language (CamelCase tar basename) for an alias, or '' if unknown.

    Read straight from repo_alias.json (which carries `language` per repo),
    so no separate real-name lookup is needed.
    """
    try:
        return canon_lang(alias_record(alias).get("language", ""))
    except KeyError:
        return ""


def prompt_language(env_mode: str, alias: str) -> str:
    """Language to advertise to the agent in the task prompt's `{lang}` slot.

    Must agree with the image `resolve_docker_tar` provisions, otherwise the agent
    is told one language but handed another language's image (e.g. env_mode=Python
    on a Ruby repo would tell it 'Ruby' yet boot the Python image):
      - 'base' / 'ultimate' -> the repo's own (original) language.
      - '<language>'         -> that explicit language (cross-language: the agent
                               re-implements in the env_mode language).
    """
    mode = (env_mode or "").strip()
    if mode in ("base", "ultimate", ""):
        return repo_language(alias)
    return canon_lang(mode)


# ── env_mode -> docker tar ───────────────────────────────────────────────────
def resolve_docker_tar(env_mode: str, alias: str) -> Path:
    """Resolve the docker image tar to provision for an alias under an env_mode.

    The base/cross-language tars keep their official download.sh filenames; the
    LANG_TAR map (via lang_tar_path) resolves language -> filename, so no on-disk
    renaming is needed. The ultimate sandbox tars are still named by the real key.

    env_mode:
      - 'base'      -> docker_lang_official/<official tar for repo's language>
      - 'ultimate'  -> sandbox_docker_imgs/<key>_sandbox.tar
      - '<language>'-> docker_lang_official/<official tar for that language>  (cross-language)
    """
    mode = (env_mode or "").strip()
    if mode == "ultimate":
        key = key_for_alias(alias)
        return SANDBOX_IMGS_DIR / f"{key}_sandbox.tar"
    if mode == "base":
        lang = repo_language(alias)
        if not lang:
            raise ValueError(f"unknown language for alias '{alias}' (needed for env_mode=base)")
        return lang_tar_path(lang)
    # treat as an explicit target language
    lang = canon_lang(mode)
    if lang not in LANG_TAR:
        raise ValueError(
            f"env_mode='{env_mode}' is neither base/ultimate nor a known language"
        )
    tar = lang_tar_path(lang)
    if not tar.exists():
        raise ValueError(
            f"env_mode='{env_mode}' resolves to language '{lang}' but no tar exists "
            f"at {tar} (expected {LANG_TAR[lang]} in {DOCKER_LANG_DIR})"
        )
    return tar


def image_tag_from_tar(tar_path: Path) -> str:
    """Read the RepoTag baked into a docker save tar (manifest.json -> RepoTags[0])."""
    with tarfile.open(tar_path) as t:
        member = t.getmember("manifest.json")
        manifest = json.loads(t.extractfile(member).read().decode("utf-8"))
    tags = manifest[0].get("RepoTags") or []
    if not tags:
        raise ValueError(f"no RepoTags in {tar_path}")
    return tags[0]


def fuzzy_out_dir(user_model_name: str, query_count: int,
                  difficulty: str = "normal") -> Path:
    """Where filled fuzzy PRDs are written, refreshed each run."""
    tag = {"easy": "_easy", "medium": "_medium"}.get(difficulty, "")
    return ROOT / f"fuzzy_prds{tag}@{user_model_name}@query_{query_count}"


def code_path(append_id: str, alias: str) -> Path:
    """The agent-under-test working directory (host side, bind-mounted into the
    container). Named by the anonymous alias so `docker inspect` never reveals
    the real repo name via the mount source."""
    return RESULTS / append_id / alias
