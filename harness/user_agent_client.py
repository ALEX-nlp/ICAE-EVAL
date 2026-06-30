"""User Agent (Oracle) init + experiment-settings persistence.

Two responsibilities:
  1. mint_or_resume_append_id(): obtain the append_id that ties this run to the
     User Agent. A fresh run POSTs the hard-coded key + user_model_name +
     query_count to the init port; the server binds them to a new append_id and
     persists state. A resume run reuses a caller-supplied append_id (the server
     already remembers its model / budget / per-repo history), so we DON'T call
     init again — that would mint a new id.
  2. settings persistence, split across two files so a per-repo backfill can
     never clobber the experiment registry:
       - results/settings.json            -> registry: append_id -> config ONLY
       - results/<append_id>/settings.json -> that run's {config, repos:{...}}
     init_settings() writes config to both; per-repo updates touch only the
     per-run file.
"""
import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

import requests

from . import config as C


def mint_append_id(user_host: str, user_init_port: int,
                   user_model_name: str, query_count: int,
                   difficulty: str = "normal",
                   timeout: float = 30.0) -> str:
    """POST the init request and return a fresh append_id."""
    url = f"http://{user_host}:{user_init_port}/"
    payload = {
        "key": C.INIT_KEY,
        "model": user_model_name,       # bound to append_id on the server
        "max_interactions": query_count,
        "difficulty": difficulty,       # server selects the matching oracle_data
    }
    resp = requests.post(url, json=payload, timeout=timeout).json()
    status = resp.get("status", {})
    if not status.get("ok"):
        raise RuntimeError(f"init failed at {url}: {status.get('error', resp)}")
    append_id = resp.get("append_id")
    if not append_id:
        raise RuntimeError(f"init returned no append_id: {resp}")
    return append_id


def mint_or_resume_append_id(append_id: str | None, *, user_host: str,
                             user_init_port: int, user_model_name: str,
                             query_count: int,
                             difficulty: str = "normal") -> tuple[str, bool]:
    """Return (append_id, is_new). Resume reuses the given id without re-init."""
    if append_id:
        return append_id, False
    new_id = mint_append_id(user_host, user_init_port, user_model_name,
                            query_count, difficulty)
    return new_id, True


# ── interaction-quality stats (metric group (d), user_eval_port) ──────────────

_INTERACTION_KEYS = ("constraint_coverage", "fallback_rate", "budget_usage_rate")


def validate_append_id(append_id: str, *, user_host: str, user_query_port: int,
                       timeout: float = 15.0) -> bool | None:
    """Preflight: is this append_id registered/valid on the live Oracle?

    Sends a sentinel probe to the interaction port (50002) with a throwaway
    task_id ("__preflight__") so it never touches a real repo's interaction
    budget. The ONLY signal we trust is the Oracle's "invalid append_id"
    rejection (main.py:155, returned BEFORE any logging/budget mutation):

      - status.error == "invalid append_id"  -> False (id was never init'd)
      - any other response (an Oracle answer, or a different error)  -> True
      - network/parse failure -> None (cannot tell; caller decides, must not
        false-kill a run just because the Oracle momentarily hiccuped)

    Why this exists: a resume run that reuses an append_id the Oracle never
    registered (the f19f02 incident) otherwise runs ALL repos with every
    clarification silently rejected — zero interaction data, blind generations.
    The caller aborts the run when this returns False.
    """
    url = f"http://{user_host}:{user_query_port}/"
    payload = {"append_id": append_id, "task_id": "__preflight__",
               "question": "ping"}
    try:
        resp = requests.post(url, json=payload, timeout=timeout).json()
    except Exception:  # noqa: BLE001 — network/parse: undetermined
        return None
    status = resp.get("status", {}) or {}
    err = str(status.get("error", "")).lower()
    if "invalid append_id" in err:
        return False
    return True



def fetch_interaction_stats(append_id: str, *, user_host: str, user_eval_port: int,
                            task_id: str | None = None,
                            timeout: float = 30.0) -> dict:
    """Fetch Interaction Quality stats from the User Agent stats port.

    POST {append_id, task_id?} to user_eval_port; the Oracle returns
    constraint_coverage / fallback_rate / budget_usage_rate (per-task when a
    task_id/alias is given, else aggregate across all of this append_id's repos).
    Returns the compact metric subset (+ ok/error). Never raises on a bad
    response — interaction stats are best-effort and must not abort an eval.
    """
    url = f"http://{user_host}:{user_eval_port}/"
    payload: dict = {"append_id": append_id}
    if task_id:
        payload["task_id"] = task_id
    try:
        resp = requests.post(url, json=payload, timeout=timeout).json()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"request failed: {e}"}
    status = resp.get("status", {})
    if not status.get("ok"):
        return {"ok": False, "error": status.get("error", resp)}
    stats = resp.get("stats", {}) or {}
    out = {k: stats.get(k) for k in _INTERACTION_KEYS}
    out["ok"] = True
    return out


# ── settings persistence (registry + per-run) ────────────────────────────────
# Registry  results/settings.json            : {append_id: {config...}}  (NO repos)
# Per-run    results/<append_id>/settings.json: {append_id, config, repos:{...}}

# repo-level keys never belong in the registry (config-only index).
_RUN_ONLY_KEYS = ("repos",)


def _read_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Unique temp name per write: the shared registry (results/settings.json) is
    # written by every concurrent batch, and a fixed '*.tmp' lets two writers race
    # on the same temp file (one replace() then fails FileNotFoundError).
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".",
                                    suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


# Registry (config index) ------------------------------------------------------

@contextmanager
def _registry_lock():
    """Inter-process lock for the shared registry read-modify-write.

    Every concurrent batch process writes results/settings.json, so init_settings
    must serialize across processes or one writer's entry gets dropped
    (last-writer-wins). Uses flock on a sidecar lock file; degrades to a no-op if
    flock is unavailable (e.g. non-POSIX), which is acceptable since the per-run
    files — the source of truth for resume — are process-exclusive.
    """
    lock_path = C.SETTINGS_FILE.with_suffix(C.SETTINGS_FILE.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import fcntl
    except Exception:
        yield
        return
    fh = open(lock_path, "w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fh, fcntl.LOCK_UN)
        finally:
            fh.close()


def _load_registry() -> dict:
    return _read_json(C.SETTINGS_FILE)


def _save_registry(data: dict) -> None:
    _write_json(C.SETTINGS_FILE, data)


# Per-run file -----------------------------------------------------------------

def _load_run(append_id: str) -> dict:
    return _read_json(C.run_settings_path(append_id))


def _save_run(append_id: str, data: dict) -> None:
    _write_json(C.run_settings_path(append_id), data)


# Backward-compatible aliases (older backfill scripts import these). They now
# operate on the PER-RUN file via a thin {append_id: run} view so a careless
# "rebuild from scratch then save" can only ever damage a single run's file,
# never the registry or other runs.
def _load_settings() -> dict:  # noqa: D401 - compat shim
    return _load_registry()


def _save_settings(data: dict) -> None:  # noqa: D401 - compat shim
    _save_registry(data)


def init_settings(append_id: str, params: dict) -> None:
    """Record run config in BOTH the registry and the per-run file.

    `params` is config only; any stray per-repo keys are dropped from the
    registry. The per-run file additionally carries the `repos` map.
    """
    cfg = {k: v for k, v in params.items() if k not in _RUN_ONLY_KEYS}
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    with _registry_lock():
        reg = _load_registry()
        rrec = reg.get(append_id, {})
        rrec.update(cfg)
        rrec["updated_at"] = now
        reg[append_id] = rrec
        _save_registry(reg)

    run = _load_run(append_id)
    run["append_id"] = append_id
    run.setdefault("config", {}).update(cfg)
    run.setdefault("repos", {})
    run["updated_at"] = now
    _save_run(append_id, run)


def update_repo_status(append_id: str, repo_key: str, status: dict) -> None:
    """Merge per-repo status into the PER-RUN file only (registry untouched)."""
    run = _load_run(append_id)
    run.setdefault("append_id", append_id)
    run.setdefault("config", {})
    repos = run.setdefault("repos", {})
    cur = repos.get(repo_key, {})
    cur.update(status)
    repos[repo_key] = cur
    run["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save_run(append_id, run)


def get_repo_status(append_id: str, repo_key: str) -> dict:
    return _load_run(append_id).get("repos", {}).get(repo_key, {})


def load_run_record(append_id: str) -> dict:
    """Full per-run record {append_id, config, repos}. Empty dict if absent."""
    return _load_run(append_id)
