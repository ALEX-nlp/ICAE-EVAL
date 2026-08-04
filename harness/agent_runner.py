"""Async wrapper around claude_agent_sdk.query() for one agent-under-test task.

Adapted from agent_env/scripts/pipeline_sdk/sdk_runner.py. Differences:
  - model + ANTHROPIC_* env are injected per-run from model_list.json (the SUT
    model), not read from the ambient environment.
  - includes watchdog timeouts and rate-limit / refusal classification.
"""
import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path

from claude_agent_sdk import (
    query, ClaudeAgentOptions,
    AssistantMessage, ResultMessage, SystemMessage, UserMessage,
    TextBlock, ThinkingBlock, ToolUseBlock, ToolResultBlock,
)

from . import config as C

REFUSAL_MARKERS = [
    "Usage Policy", "usage policies", "I can't help with that",
    "I cannot help with", "I'm not able to help", "against Anthropic",
]
RATELIMIT_MARKERS = [
    "429", "每分钟请求次数超过限制", "rate limit", "rate_limit",
    "overloaded", "Overloaded",
]
INACTIVITY_TIMEOUT = 900  # seconds with no message before abandoning the stream


class RateLimited(Exception):
    pass


@dataclass
class AgentResult:
    status: str           # "success" | "refused" | "error"
    is_error: bool = False
    refused: bool = False
    cost_usd: float = 0.0
    num_turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    tail: str = ""
    raw_subtype: str = ""
    detail: str = ""


def _contains(haystack: str, markers) -> bool:
    h = haystack or ""
    return any(m in h for m in markers)


async def _aclose(agen, w) -> None:
    try:
        aclose = getattr(agen, "aclose", None)
        if aclose is not None:
            await asyncio.wait_for(aclose(), timeout=15)
    except Exception as e:  # noqa: BLE001
        w(f"[watchdog] aclose failed (ignored): {type(e).__name__}: {e}")


def _block_to_text(block) -> str:
    if isinstance(block, TextBlock):
        return block.text or ""
    if isinstance(block, ThinkingBlock):
        return ""
    if isinstance(block, ToolUseBlock):
        inp = repr(block.input)
        if len(inp) > 800:
            inp = inp[:800] + "...<truncated>"
        return f"[tool_use {block.name}] {inp}"
    if isinstance(block, ToolResultBlock):
        c = block.content
        s = c if isinstance(c, str) else repr(c)
        if len(s) > 1200:
            s = s[:1200] + "...<truncated>"
        return f"[tool_result] {s}"
    return ""


def _block_to_record(block) -> dict:
    """Full-fidelity structured form of one content block (NO truncation).

    Used for the per-round JSONL transcript so every model input/output round
    is preserved verbatim (unlike _block_to_text, which truncates for the
    human-readable .log).
    """
    if isinstance(block, TextBlock):
        return {"kind": "text", "text": block.text or ""}
    if isinstance(block, ThinkingBlock):
        return {"kind": "thinking",
                "thinking": getattr(block, "thinking", "") or "",
                "signature": getattr(block, "signature", None)}
    if isinstance(block, ToolUseBlock):
        return {"kind": "tool_use", "id": getattr(block, "id", None),
                "name": block.name, "input": block.input}
    if isinstance(block, ToolResultBlock):
        return {"kind": "tool_result",
                "tool_use_id": getattr(block, "tool_use_id", None),
                "content": block.content,
                "is_error": getattr(block, "is_error", None)}
    return {"kind": block.__class__.__name__, "repr": repr(block)}


def build_env(model_entry: dict) -> dict:
    """ANTHROPIC_* overrides for the CLI subprocess from a model_list.json entry."""
    env = {}
    if model_entry.get("ANTHROPIC_MODEL"):
        env["ANTHROPIC_MODEL"] = model_entry["ANTHROPIC_MODEL"]
    if model_entry.get("ANTHROPIC_BASE_URL"):
        env["ANTHROPIC_BASE_URL"] = model_entry["ANTHROPIC_BASE_URL"]
    if model_entry.get("ANTHROPIC_AUTH_TOKEN"):
        env["ANTHROPIC_AUTH_TOKEN"] = model_entry["ANTHROPIC_AUTH_TOKEN"]
    return env


async def run_agent(prompt: str, cwd: Path, log_path: Path, model_entry: dict,
                    *, max_turns: int = 200, timeout: float | None = 7200) -> AgentResult:
    """Run one agent turn-loop in `cwd`, streaming a transcript to `log_path`."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    opts = ClaudeAgentOptions(
        model=model_entry.get("ANTHROPIC_MODEL"),
        permission_mode="bypassPermissions",
        cwd=str(cwd),
        cli_path=C.CLI_PATH,
        max_turns=max_turns,
        allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Grep"],
        setting_sources=["user", "project"],
        env=build_env(model_entry),
    )

    started = time.time()
    last_text = ""
    turn = 0
    result_obj: AgentResult | None = None
    saw_ratelimit = False

    transcript_path = log_path.with_suffix(".jsonl")
    with open(log_path, "a", encoding="utf-8") as log, \
            open(transcript_path, "a", encoding="utf-8") as tf:
        def w(line: str):
            log.write(line.rstrip("\n") + "\n")
            log.flush()

        def emit(rec: dict):
            """Append one full-fidelity round record to the JSONL transcript.
            Never let transcript I/O break the run."""
            try:
                rec.setdefault("ts", time.time())
                tf.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
                tf.flush()
            except Exception:  # noqa: BLE001
                pass

        w(f"\n===== run_agent @ {time.strftime('%Y-%m-%d %H:%M:%S')} cwd={cwd} "
          f"model={opts.model} (overall={timeout}s inactivity={INACTIVITY_TIMEOUT}s) =====")
        # round 0 input: the initial task prompt handed to the model
        emit({"type": "prompt", "model": opts.model, "cwd": str(cwd),
              "started": time.strftime('%Y-%m-%d %H:%M:%S'), "prompt": prompt})
        agen = query(prompt=prompt, options=opts).__aiter__()
        try:
            while True:
                if timeout and (time.time() - started) > timeout:
                    w(f"[watchdog] OVERALL TIMEOUT after {timeout}s — aborting")
                    await _aclose(agen, w)
                    return AgentResult(status="error", is_error=True,
                                       detail="timeout_overall", tail=last_text[-2000:])
                budget = INACTIVITY_TIMEOUT
                if timeout:
                    budget = min(budget, max(1.0, timeout - (time.time() - started)))
                try:
                    msg = await asyncio.wait_for(agen.__anext__(), timeout=budget)
                except StopAsyncIteration:
                    break
                except asyncio.TimeoutError:
                    w(f"[watchdog] INACTIVITY TIMEOUT: no message for {budget:.0f}s — aborting")
                    await _aclose(agen, w)
                    return AgentResult(status="error", is_error=True,
                                       detail="timeout_inactivity", tail=last_text[-2000:])
                if isinstance(msg, AssistantMessage):
                    turn += 1
                    emit({"type": "assistant", "turn": turn,
                          "model": getattr(msg, "model", None),
                          "content": [_block_to_record(b) for b in msg.content],
                          "error": getattr(msg, "error", None)})
                    for b in msg.content:
                        t = _block_to_text(b)
                        if t:
                            w(t)
                            if isinstance(b, TextBlock):
                                last_text = t
                    if getattr(msg, "error", None):
                        w(f"[assistant.error] {msg.error}")
                        if _contains(str(msg.error), RATELIMIT_MARKERS):
                            saw_ratelimit = True
                elif isinstance(msg, (SystemMessage, UserMessage)):
                    # UserMessage carries the tool_result blocks fed back into the
                    # model as the NEXT round's input; SystemMessage carries init/
                    # config. Persist both verbatim so every input round is stored.
                    if isinstance(msg, UserMessage):
                        content = getattr(msg, "content", None)
                        if isinstance(content, list):
                            rec_content = [_block_to_record(b) for b in content]
                        else:
                            rec_content = content
                        emit({"type": "user", "turn": turn, "content": rec_content})
                    else:
                        emit({"type": "system",
                              "subtype": getattr(msg, "subtype", None),
                              "data": getattr(msg, "data", None)})
                elif isinstance(msg, ResultMessage):
                    txt = msg.result or ""
                    api_status = getattr(msg, "api_error_status", None)
                    errs = getattr(msg, "errors", None)
                    usage = getattr(msg, "usage", None) or {}
                    emit({"type": "result", "subtype": str(msg.subtype),
                          "is_error": bool(msg.is_error),
                          "num_turns": int(msg.num_turns or 0),
                          "total_cost_usd": float(msg.total_cost_usd or 0.0),
                          "api_error_status": api_status,
                          "usage": usage, "result_text": txt})
                    w(f"[result] subtype={msg.subtype} is_error={msg.is_error} "
                      f"turns={msg.num_turns} cost={msg.total_cost_usd} "
                      f"api_error_status={api_status}")
                    if txt:
                        w(f"[result.text] {txt[:2000]}")
                    blob = " ".join(str(x) for x in (txt, api_status, errs, msg.subtype))
                    if _contains(blob, RATELIMIT_MARKERS) or saw_ratelimit:
                        raise RateLimited(blob[:300])
                    refused = _contains(txt, REFUSAL_MARKERS) or msg.subtype == "refusal"
                    result_obj = AgentResult(
                        status="refused" if refused else ("error" if msg.is_error else "success"),
                        is_error=bool(msg.is_error),
                        refused=refused,
                        cost_usd=float(msg.total_cost_usd or 0.0),
                        num_turns=int(msg.num_turns or 0),
                        input_tokens=int(usage.get("input_tokens") or 0),
                        output_tokens=int(usage.get("output_tokens") or 0),
                        cache_creation_tokens=int(usage.get("cache_creation_input_tokens") or 0),
                        cache_read_tokens=int(usage.get("cache_read_input_tokens") or 0),
                        tail=(txt or last_text)[-2000:],
                        raw_subtype=str(msg.subtype),
                    )
        except RateLimited:
            raise
        except Exception as e:  # noqa: BLE001
            blob = f"{type(e).__name__}: {e}"
            w(f"[exception] {blob}")
            if _contains(blob, RATELIMIT_MARKERS):
                raise RateLimited(blob[:300])
            if result_obj is not None:
                result_obj.detail = (result_obj.detail + " | " + blob).strip(" |")
                return result_obj
            return AgentResult(status="error", is_error=True, detail=blob,
                               tail=last_text[-2000:])

    if result_obj is None:
        return AgentResult(status="error", is_error=True, detail="no ResultMessage",
                           tail=last_text[-2000:])
    return result_obj
