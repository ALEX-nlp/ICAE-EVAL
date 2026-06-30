"""Async wrapper around claude_agent_sdk.query() for one agent-under-test task.

Adapted from agent_env/scripts/pipeline_sdk/sdk_runner.py. Differences:
  - model + ANTHROPIC_* env are injected per-run from model_list.json (the SUT
    model), not read from the ambient environment.
  - includes watchdog timeouts and rate-limit / refusal classification.
"""
import asyncio
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
    result_obj: AgentResult | None = None
    saw_ratelimit = False

    with open(log_path, "a", encoding="utf-8") as log:
        def w(line: str):
            log.write(line.rstrip("\n") + "\n")
            log.flush()

        w(f"\n===== run_agent @ {time.strftime('%Y-%m-%d %H:%M:%S')} cwd={cwd} "
          f"model={opts.model} (overall={timeout}s inactivity={INACTIVITY_TIMEOUT}s) =====")
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
                    pass
                elif isinstance(msg, ResultMessage):
                    txt = msg.result or ""
                    api_status = getattr(msg, "api_error_status", None)
                    errs = getattr(msg, "errors", None)
                    w(f"[result] subtype={msg.subtype} is_error={msg.is_error} "
                      f"turns={msg.num_turns} cost={msg.total_cost_usd} "
                      f"api_error_status={api_status}")
                    if txt:
                        w(f"[result.text] {txt[:2000]}")
                    blob = " ".join(str(x) for x in (txt, api_status, errs, msg.subtype))
                    if _contains(blob, RATELIMIT_MARKERS) or saw_ratelimit:
                        raise RateLimited(blob[:300])
                    refused = _contains(txt, REFUSAL_MARKERS) or msg.subtype == "refusal"
                    usage = getattr(msg, "usage", None) or {}
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
