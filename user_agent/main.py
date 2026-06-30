"""Three-port User Agent service.

  - Port 50001  Init service:    validate the hard-coded key, issue an append_id.
  - Port 50002  Interaction:     validate append_id, keep an independent history
                                 and a configurable interaction budget per
                                 {append_id, task_id}, call the Oracle.
  - Port 50003  Stats service:   given an append_id, return Constraint Coverage,
                                 Fallback Rate, and Budget Usage Rate.

`task_id` is the anonymous repo alias ('realcode@NNN'); the agent-under-test never
sees the real `username__repo_name` (which would let it find the reference repo).

Both apps run in ONE process so they share the in-memory append_id registry.
State is persisted to state/ directory and recovered on restart.

Run:  python main.py
"""

import asyncio
import json
import time
import uuid
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request

from user_agent import UserAgentSession, get_prd_dir

INIT_KEY = "zVtwLTkCKwoCWq4Jq9D2"
MAX_INTERACTIONS = 16  # default, can be overridden per append_id via init request

BASE_DIR = Path(__file__).parent

# Debug log directory — one JSONL file per (task_id, append_id).
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Persistence directory — state survives restarts.
STATE_DIR = BASE_DIR / "state"
STATE_DIR.mkdir(exist_ok=True)
STATE_FILE = STATE_DIR / "append_ids.json"       # append_id registry
SESSION_DIR = STATE_DIR / "sessions"             # one JSON file per session key
SESSION_DIR.mkdir(exist_ok=True)

_log_lock: asyncio.Lock = None      # created inside event loop on first use
_state_lock: asyncio.Lock = None

def _get_log_lock() -> asyncio.Lock:
    global _log_lock
    if _log_lock is None:
        _log_lock = asyncio.Lock()
    return _log_lock

def _get_state_lock() -> asyncio.Lock:
    global _state_lock
    if _state_lock is None:
        _state_lock = asyncio.Lock()
    return _state_lock


# ── persistence helpers ───────────────────────────────────────────────────────

def _load_state() -> dict:
    """Load valid_append_ids from disk."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_append_id(append_id: str, record: dict) -> None:
    """Persist a single append_id record (synchronous, called under _state_lock)."""
    data = _load_state()
    data[append_id] = record
    STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _session_path(append_id: str, task_id: str) -> Path:
    return SESSION_DIR / f"{append_id}__{task_id}.json"


def _save_session(append_id: str, task_id: str, count: int, messages: list) -> None:
    """Persist session messages and count to disk (synchronous)."""
    path = _session_path(append_id, task_id)
    path.write_text(json.dumps(
        {"count": count, "messages": messages}, ensure_ascii=False, indent=2
    ), encoding="utf-8")


def _load_session(append_id: str, task_id: str) -> tuple[int, list]:
    """Load session count and messages from disk. Returns (0, []) if not found."""
    path = _session_path(append_id, task_id)
    if path.exists():
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            return d.get("count", 0), d.get("messages", [])
        except Exception:
            pass
    return 0, []


# ── in-memory state (restored from disk on startup) ──────────────────────────

valid_append_ids: dict = _load_state()
sessions: dict = {}           # (append_id, task_id) -> session record (runtime only)
sessions_guard = asyncio.Lock()

print(f"Restored {len(valid_append_ids)} append_id(s) from state.")


# ── log helper ────────────────────────────────────────────────────────────────

async def _append_log(task_id: str, append_id: str, entry: dict) -> None:
    repo_log_dir = LOG_DIR / task_id
    repo_log_dir.mkdir(exist_ok=True)
    path = repo_log_dir / f"{append_id}.jsonl"
    line = json.dumps(entry, ensure_ascii=False) + "\n"
    async with _get_log_lock():
        with path.open("a", encoding="utf-8") as f:
            f.write(line)


# ── endpoints ─────────────────────────────────────────────────────────────────

init_app  = FastAPI(title="UserAgent Init")
chat_app  = FastAPI(title="UserAgent Interaction")
stats_app = FastAPI(title="UserAgent Stats")


@init_app.post("/")
async def init_endpoint(req: Request):
    """Request: {"key", "model", "max_interactions"?}  ->  {"append_id", "status"}."""
    body = await req.json()
    if body.get("key") != INIT_KEY:
        return {"append_id": None, "status": {"ok": False, "error": "invalid key"}}
    model = body.get("model") or ""
    if not model:
        return {"append_id": None, "status": {"ok": False, "error": "missing model"}}
    difficulty = body.get("difficulty", "normal")
    if difficulty not in ("normal", "medium", "easy"):
        return {"append_id": None, "status": {"ok": False, "error": "difficulty must be 'normal', 'medium', or 'easy'"}}
    open_access = bool(body.get("open_access", False))
    append_id = uuid.uuid4().hex
    max_interactions = int(body.get("max_interactions", MAX_INTERACTIONS))
    record = {
        "status": body.get("status", {}),
        "max_interactions": max_interactions,
        "model": model,
        "difficulty": difficulty,
        "open_access": open_access,
    }
    async with _get_state_lock():
        valid_append_ids[append_id] = record
        await asyncio.to_thread(_save_append_id, append_id, record)
    return {"append_id": append_id, "status": {
        "ok": True,
        "max_interactions": max_interactions,
        "model": model,
        "difficulty": difficulty,
        "open_access": open_access,
    }}


@chat_app.post("/")
async def chat_endpoint(req: Request):
    """Request: {"append_id", "task_id", "question"} -> {"data", "status"}."""
    body = await req.json()
    append_id = body.get("append_id")
    task_id   = body.get("task_id")
    question  = body.get("question", "")

    if append_id not in valid_append_ids:
        return {"data": "", "status": {"ok": False, "error": "invalid append_id"}}
    if not (task_id and question):
        return {"data": "", "status": {"ok": False, "error": "missing task_id/question"}}

    id_record        = valid_append_ids[append_id]
    max_interactions = id_record["max_interactions"]
    model            = id_record["model"]
    difficulty       = id_record.get("difficulty", "normal")
    open_access      = id_record.get("open_access", False)

    key = (append_id, task_id)
    async with sessions_guard:
        record = sessions.get(key)
        if record is None:
            try:
                sess = UserAgentSession(task_id, difficulty=difficulty, open_access=open_access)
            except FileNotFoundError:
                return {"data": "", "status": {"ok": False,
                                               "error": f"no prd for {task_id}"}}
            # Restore count and message history from disk if available.
            count, messages = _load_session(append_id, task_id)
            sess.messages = messages
            record = {"sess": sess, "count": count, "lock": asyncio.Lock()}
            sessions[key] = record

    async with record["lock"]:
        if record["count"] >= max_interactions:
            await _append_log(task_id, append_id, {
                "ts": time.time(), "append_id": append_id,
                "turn": record["count"] + 1, "question": question,
                "error": "max_interactions_reached",
            })
            return {"data": "", "status": {"ok": False,
                                           "error": "max_interactions_reached", "remaining": 0}}

        t0     = time.time()
        result = await asyncio.to_thread(record["sess"].ask, question, model=model)
        elapsed = round(time.time() - t0, 3)
        record["count"] += 1
        remaining = max_interactions - record["count"]
        if remaining <= 0:
            record["sess"].close()

        # Persist updated session state.
        await asyncio.to_thread(
            _save_session, append_id, task_id,
            record["count"], record["sess"].messages
        )

        ilog  = result.get("_internal_log", {})
        reply = result.get("reply", "")
        response = {
            "data": reply,
            "status": {
                "ok": True,
                "remaining": remaining,
                "internal_log": ilog,
                "parse_error": result.get("_parse_error", False),
            },
        }

        await _append_log(task_id, append_id, {
            "ts": time.time(),
            "append_id": append_id,
            "turn": record["count"],
            "remaining": remaining,
            "elapsed_s": elapsed,
            "question": question,
            "answer": reply,
            "triggers_hit": ilog.get("triggers_hit", []),
            "fallback_triggered": ilog.get("fallback_triggered", False),
            "api_alignment_triggered": ilog.get("api_alignment_triggered", False),
            "cheating_attempt_detected": ilog.get("cheating_attempt_detected", False),
            "score_adjustment": ilog.get("score_adjustment", 0),
            "parse_error": result.get("_parse_error", False),
        })

        return response


def _calc_repo_stats(append_id: str, log_file: Path, max_interactions: int, model: str, difficulty: str = "normal") -> dict:
    """Compute stats for one (append_id, task_id) log file."""
    entries = []
    for line in log_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except Exception:
                pass

    turn_entries = [e for e in entries if "turn" in e and "error" not in e]
    turns_used   = len(turn_entries)
    triggered    = set()
    for e in turn_entries:
        triggered.update(e.get("triggers_hit", []))
    fallbacks   = sum(1 for e in turn_entries if e.get("fallback_triggered"))
    total_score = sum(e.get("score_adjustment", 0) for e in turn_entries)

    task_id = log_file.parent.name          # e.g. "realcode@001"
    all_constraint_ids, missed, coverage_pct = [], [], None
    prd_path = get_prd_dir(difficulty) / f"{task_id}.json"
    if prd_path.exists():
        prd = json.loads(prd_path.read_text(encoding="utf-8"))
        all_constraint_ids = [
            c["constraint_id"]
            for c in prd.get("oracle_data", {}).get("hidden_constraints", [])
        ]
        missed = [c for c in all_constraint_ids if c not in triggered]
        if all_constraint_ids:
            coverage_pct = round(100 * len(triggered) / len(all_constraint_ids), 1)

    return {
        "task_id": task_id,
        "model": model,
        "turns_used": turns_used,
        "max_interactions": max_interactions,
        "budget_usage_rate": round(100 * turns_used / max_interactions, 1) if max_interactions else 0.0,
        "fallbacks": fallbacks,
        "fallback_rate": round(100 * fallbacks / turns_used, 1) if turns_used else 0.0,
        "triggers_hit": sorted(triggered),
        "total_constraints": len(all_constraint_ids),
        "constraint_coverage": coverage_pct,
        "missed_constraints": missed,
        "interaction_score": total_score,
    }


@stats_app.post("/")
async def stats_endpoint(req: Request):
    """Request: {"append_id", "task_id"?}
       - append_id only  → aggregate stats across all tasks for this append_id
       - + task_id       → stats for that specific task only
    """
    body = await req.json()
    append_id = body.get("append_id")
    task_id   = body.get("task_id")

    if not append_id:
        return {"status": {"ok": False, "error": "missing append_id"}}
    if not (len(append_id) == 32 and all(c in "0123456789abcdef" for c in append_id)):
        return {"status": {"ok": False, "error": "invalid append_id format"}}

    id_record        = valid_append_ids.get(append_id, {})
    max_interactions = id_record.get("max_interactions", MAX_INTERACTIONS)
    model            = id_record.get("model")
    difficulty       = id_record.get("difficulty", "normal")

    # ── single task mode ──────────────────────────────────────────────────────
    if task_id:
        log_file = LOG_DIR / task_id / f"{append_id}.jsonl"
        if not log_file.exists():
            return {"status": {"ok": False, "error": f"no log for {task_id}"}}
        stats = _calc_repo_stats(append_id, log_file, max_interactions, model, difficulty)
        return {"stats": stats, "status": {"ok": True}}

    # ── aggregate mode ────────────────────────────────────────────────────────
    log_files = [f for f in LOG_DIR.rglob(f"{append_id}.jsonl") if len(f.stem) == 32]
    if not log_files:
        return {"status": {"ok": False, "error": "no log found for append_id"}}

    per_repo = [_calc_repo_stats(append_id, lf, max_interactions, model, difficulty) for lf in log_files]

    # Roll up totals.
    total_turns     = sum(r["turns_used"] for r in per_repo)
    total_fallbacks = sum(r["fallbacks"] for r in per_repo)
    total_score     = sum(r["interaction_score"] for r in per_repo)
    all_triggered   = set()
    all_constraints = set()
    for r in per_repo:
        all_triggered.update(r["triggers_hit"])
        all_constraints.update(r["triggers_hit"])
        all_constraints.update(r["missed_constraints"])

    n = len(per_repo)
    avg_budget_usage   = round(sum(r["budget_usage_rate"] for r in per_repo) / n, 1) if n else 0.0
    avg_fallback_rate  = round(sum(r["fallback_rate"] for r in per_repo) / n, 1) if n else 0.0
    avg_coverage       = round(sum(r["constraint_coverage"] for r in per_repo
                                   if r["constraint_coverage"] is not None)
                               / sum(1 for r in per_repo if r["constraint_coverage"] is not None), 1) \
                         if any(r["constraint_coverage"] is not None for r in per_repo) else None

    agg = {
        "append_id": append_id,
        "model": model,
        "repos": n,
        "turns_used": total_turns,
        "max_interactions": max_interactions,
        "budget_usage_rate": avg_budget_usage,
        "fallbacks": total_fallbacks,
        "fallback_rate": avg_fallback_rate,
        "constraint_coverage": avg_coverage,
        "interaction_score": total_score,
        "per_repo": per_repo,
    }
    return {"stats": agg, "status": {"ok": True}}


async def main():
    cfg1 = uvicorn.Config(init_app,  host="0.0.0.0", port=50001, log_level="info")
    cfg2 = uvicorn.Config(chat_app,  host="0.0.0.0", port=50002, log_level="info")
    cfg3 = uvicorn.Config(stats_app, host="0.0.0.0", port=50003, log_level="info")
    await asyncio.gather(
        uvicorn.Server(cfg1).serve(),
        uvicorn.Server(cfg2).serve(),
        uvicorn.Server(cfg3).serve(),
    )


if __name__ == "__main__":
    asyncio.run(main())
