"""User Agent core: the simulated requirements-provider (Oracle).

Why the plain Messages API (not the Agent SDK):
  init.md forbids the Oracle from using any external knowledge or reading the
  repo — it answers ONLY from the injected `oracle_data` JSON. So there are no
  tools to run. The Agent SDK's value (built-in Read/Bash/web tools) is unused,
  and its bundled Claude Code CLI injects a "You are Claude Code" identity that
  fights the Oracle persona. The Messages API gives a fully controlled system
  prompt and explicit per-session history, which is exactly what we need.

Model config is read from user_model.json at runtime. Supports both
anthropic and openai API types. Each model key maps to a list of backends;
a round-robin with skip-on-failure is used for high-concurrency requests.
"""

import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Optional

import anthropic
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent
INIT_PROMPT = (BASE_DIR / "init.md").read_text(encoding="utf-8")
PRD_DIR = BASE_DIR / "prd_json"
PRD_DIR_MEDIUM = BASE_DIR / "prd_json_medium"
PRD_DIR_EASY = BASE_DIR / "prd_json_easy"
# Golden ORIGINAL source root (realcode_repos.tar.lz4), used ONLY in open_access
# mode to inject repo source as extra reference. Resolved relative to the repo
# root by default; override with ICAE_GOLDEN_REPOS_DIR (shared with the harness).
REALCODE_REPOS_DIR = Path(
    os.environ.get("ICAE_GOLDEN_REPOS_DIR", str(BASE_DIR.parent / "realcode_repos"))
)
USER_MODEL_PATH = BASE_DIR / "user_model.json"

PRD_DIRS = {
    "normal": PRD_DIR,
    "medium": PRD_DIR_MEDIUM,
    "easy": PRD_DIR_EASY,
}

# Max characters of repo source injected into the system prompt (~100K tokens).
REPO_CODE_CHAR_LIMIT = 400_000

# File extensions treated as source code (everything else is skipped).
_CODE_SUFFIXES = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".kt", ".kts",
    ".go", ".rs", ".cpp", ".cc", ".cxx", ".c", ".h", ".hpp",
    ".cs", ".rb", ".php", ".swift", ".scala", ".dart", ".ex", ".exs",
    ".lua", ".r", ".R", ".sh", ".bash", ".zsh",
    ".html", ".css", ".scss", ".sass", ".less",
    ".json", ".yaml", ".yml", ".toml", ".xml",
    ".md", ".txt",
}

OPEN_ACCESS_EXTRA_PROMPT = """
# Open-Access Mode
The repository source code has been injected below as additional reference material.
You MAY use this code to answer questions that are NOT covered by the oracle_data — but ONLY when the question does not violate the interaction rules above (no cheating-attempt, no direct code hand-out, etc.).
All existing rules (Single Source of Truth for oracle_data, Exact Match, Fallback, Rate Limiting, etc.) still apply in full.
When answering from the repository code rather than oracle_data, do NOT cite specific file paths or line numbers — summarise the behaviour in natural language as a Tech Lead would.
"""

MAX_TOKENS = 4096

# How long (seconds) to skip a backend after it fails.
_SKIP_DURATION = 60.0

# Per-model round-robin state: { model_key: {"idx": int, "lock": Lock, "skip_until": [float,...]} }
_rr_state: dict = {}
_rr_state_lock = threading.Lock()


def _load_user_models() -> dict:
    if USER_MODEL_PATH.exists():
        return json.loads(USER_MODEL_PATH.read_text(encoding="utf-8"))
    return {}


def _get_rr(model_key: str, n: int) -> dict:
    """Return (or create) round-robin state for a model key."""
    with _rr_state_lock:
        if model_key not in _rr_state:
            _rr_state[model_key] = {
                "idx": 0,
                "lock": threading.Lock(),
                "skip_until": [0.0] * n,
            }
        return _rr_state[model_key]


def _pick_backend(model_key: str, cfgs: list) -> tuple[int, dict]:
    """Round-robin pick: skip backends that recently failed.
    Returns (index, cfg). Raises ValueError if all backends are skipped."""
    rr = _get_rr(model_key, len(cfgs))
    now = time.time()
    with rr["lock"]:
        n = len(cfgs)
        for _ in range(n):
            idx = rr["idx"] % n
            rr["idx"] = (rr["idx"] + 1) % n
            if rr["skip_until"][idx] <= now:
                return idx, cfgs[idx]
        # All skipped — pick the one whose skip expires soonest
        best = min(range(n), key=lambda i: rr["skip_until"][i])
        return best, cfgs[best]


def _mark_failed(model_key: str, idx: int) -> None:
    """Mark backend idx as failed; skip it for _SKIP_DURATION seconds."""
    rr = _rr_state.get(model_key)
    if rr:
        with rr["lock"]:
            rr["skip_until"][idx] = time.time() + _SKIP_DURATION


def _call_backend(cfg: dict, system: str, messages: list) -> str:
    """Call one backend and return the text response."""
    api_type  = cfg.get("api_type", "anthropic")
    model_name = cfg["model_name"]

    if api_type == "openai":
        client = OpenAI(base_url=cfg["base_url"], api_key=cfg.get("api_key", ""))
        msgs = [{"role": "system", "content": system}] + messages
        resp = client.chat.completions.create(
            model=model_name, max_tokens=MAX_TOKENS, messages=msgs)
        return resp.choices[0].message.content or ""
    else:
        client = anthropic.Anthropic(
            base_url=cfg["base_url"], auth_token=cfg.get("auth_token", ""))
        resp = client.messages.create(
            model=model_name, max_tokens=MAX_TOKENS,
            system=system, messages=messages)
        return next((b.text for b in resp.content if b.type == "text"), "")


def _call_with_rr(model_key: str, system: str, messages: list) -> str:
    """Call the model using round-robin backend selection with skip-on-failure."""
    models = _load_user_models()
    if model_key not in models:
        raise ValueError(
            f"Model '{model_key}' not found in user_model.json. "
            f"Available: {list(models.keys())}"
        )
    cfgs = models[model_key]
    if isinstance(cfgs, dict):
        cfgs = [cfgs]  # backward compat if someone passes old single-dict format

    idx, cfg = _pick_backend(model_key, cfgs)
    try:
        text = _call_backend(cfg, system, messages)
        return text
    except Exception as e:
        _mark_failed(model_key, idx)
        raise


def _read_repo_code(task_id: str) -> str:
    """Read source files under the golden repo directory up to REPO_CODE_CHAR_LIMIT chars."""
    repo_dir = REALCODE_REPOS_DIR / task_id
    if not repo_dir.exists():
        return ""
    parts = []
    total = 0
    for f in sorted(repo_dir.rglob("*")):
        if not f.is_file():
            continue
        if f.suffix.lower() not in _CODE_SUFFIXES:
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = f.relative_to(repo_dir)
        chunk = f"### {rel}\n{content}"
        if total + len(chunk) > REPO_CODE_CHAR_LIMIT:
            remaining = REPO_CODE_CHAR_LIMIT - total
            if remaining > 0:
                parts.append(chunk[:remaining] + "\n... [truncated]")
            break
        parts.append(chunk)
        total += len(chunk)
    return "\n\n".join(parts)


def get_prd_dir(difficulty: str = "normal") -> Path:
    return PRD_DIRS.get(difficulty, PRD_DIR)



def load_record(task_id: str, difficulty: str = "normal") -> dict:
    """Load the PRD JSON for a task.

    normal: prd_json/{task_id}.json
    medium: prd_json_medium/{task_id}.json
    easy:   prd_json_easy/{task_id}.json
    """
    prd_dir = get_prd_dir(difficulty)
    path = prd_dir / f"{task_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"no PRD json for {task_id} at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def build_system_prompt(record: dict, open_access: bool = False, task_id: str = "") -> str:
    oracle = record.get("oracle_data", {})
    injected = json.dumps(oracle, ensure_ascii=False, indent=2)
    prompt = (
        f"{INIT_PROMPT}\n\n"
        f"# Injected oracle_data (your single source of truth)\n"
        f"```json\n{injected}\n```\n"
    )
    if open_access and task_id:
        repo_code = _read_repo_code(task_id)
        if repo_code:
            prompt += (
                f"\n{OPEN_ACCESS_EXTRA_PROMPT}\n"
                f"# Repository Source Code\n"
                f"{repo_code}\n"
            )
    return prompt


def parse_reply(text: str) -> dict:
    raw = text or ""
    match = re.search(r"\{.*\}", raw, re.S)
    candidate = match.group(0) if match else raw
    try:
        obj = json.loads(candidate)
    except Exception:
        return {"reply": raw, "_internal_log": {}, "_parse_error": True}
    if isinstance(obj, dict):
        obj.setdefault("reply", "")
        obj.setdefault("_internal_log", {})
        return obj
    return {"reply": raw, "_internal_log": {}, "_parse_error": True}


class UserAgentSession:
    """One Oracle conversation for a single {append_id, task_id}."""

    def __init__(self, task_id: str, difficulty: str = "normal", open_access: bool = False):
        record = load_record(task_id, difficulty=difficulty)
        self.system = build_system_prompt(record, open_access=open_access, task_id=task_id)
        self.messages: list[dict] = []

    def ask(self, question: str, model: str) -> dict:
        self.messages.append({"role": "user", "content": question})
        text = _call_with_rr(model, self.system, self.messages)
        self.messages.append({"role": "assistant", "content": text})
        return parse_reply(text)

    def close(self) -> None:
        self.messages.clear()
