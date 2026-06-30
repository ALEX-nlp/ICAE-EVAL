"""Async wrapper around the OpenHands SDK for one agent-under-test task.

This is an alternative to `agent_runner.py` (Claude Agent SDK / Claude Code CLI).
It exposes the same `run_agent(...) -> AgentResult` contract so the orchestrator
can swap frameworks with `--agent-framework openhands`. Claude Code remains the
default.

Mapping from a model_list.json entry to an OpenHands LLM (litellm under the hood):
  OPENHANDS_MODEL / OPENHANDS_BASE_URL / OPENHANDS_API_KEY  (preferred, if present)
  else ANTHROPIC_MODEL -> `anthropic/<model>`, ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN
The OPENHANDS_* keys exist because litellm's routing differs from the Anthropic
wire protocol the CLI runner uses: some gateways only accept the OpenAI-compatible
route (e.g. the local litellm proxy needs `openai/<model>` @ `<base>/v1`).

The SUT only ever sees the bind-mounted PRD and the container; here the agent
runs on the host with terminal/file tools rooted at `cwd` (the host code path,
same as the Claude runner). `docker exec` calls are issued by the agent through
the terminal tool exactly as with the CLI runner.
"""
import asyncio
import time
from pathlib import Path

from pydantic import SecretStr

from .agent_runner import (
    AgentResult, RateLimited,
    REFUSAL_MARKERS, RATELIMIT_MARKERS,
    _contains,
)

# Prepended (OpenHands path only) to ground the agent in this framework's tool
# set. Some models otherwise emit tool calls under another harness's naming
# convention (e.g. `CompatTerminal<hash>`) that the OpenHands dispatcher rejects,
# stalling the conversation. The task prompt itself is framework-agnostic.
OPENHANDS_TOOL_PREAMBLE = (
    "You are running inside the OpenHands agent framework. "
    "Invoke tools via the function-calling interface using ONLY their exact "
    "registered names: `terminal`, `file_editor`, `task_tracker`, `finish`, "
    "`think`. Do NOT use any other tool name (e.g. do not invent "
    "Bash/Edit/CompatTerminal style names) \u2014 calls to unregistered names "
    "will fail.\n\n"
)


def _llm_model_id(model_entry: dict) -> str:
    """Resolve the litellm model id for OpenHands.

    Precedence:
      1. explicit `OPENHANDS_MODEL` in the model_list.json entry (full litellm id,
         e.g. "openai/glm-5.1" or "anthropic/claude-sonnet-4.6") — lets each
         endpoint pick the provider/route that its gateway actually accepts;
      2. else fall back to the ANTHROPIC_MODEL, prefixed `anthropic/<model>`
         (the Anthropic Messages route, matching the CLI runner's wire protocol).
    """
    explicit = model_entry.get("OPENHANDS_MODEL")
    if explicit:
        return explicit
    model = model_entry.get("ANTHROPIC_MODEL") or "claude"
    return model if "/" in model else f"anthropic/{model}"


def _llm_base_url(model_entry: dict) -> str | None:
    return model_entry.get("OPENHANDS_BASE_URL") or model_entry.get("ANTHROPIC_BASE_URL")


def build_llm(model_entry: dict):
    from openhands.sdk import LLM
    kwargs = {
        "usage_id": "sut",
        "model": _llm_model_id(model_entry),
    }
    base_url = _llm_base_url(model_entry)
    if base_url:
        kwargs["base_url"] = base_url
    token = model_entry.get("OPENHANDS_API_KEY") or model_entry.get("ANTHROPIC_AUTH_TOKEN")
    if token:
        kwargs["api_key"] = SecretStr(token)
    # Optional capability-lookup override. OpenHands picks the OpenAI Responses
    # API (`/responses`) vs chat completions (`/chat/completions`) purely from a
    # capability lookup on the model NAME (gpt-5* => Responses). Some gateways
    # only expose /chat/completions, so allow forcing the canonical name used for
    # that lookup (e.g. a non-gpt-5 string) without changing the model actually
    # called. Only affects capability flags, not the wire model id.
    canonical = model_entry.get("OPENHANDS_MODEL_CANONICAL")
    if canonical:
        kwargs["model_canonical_name"] = canonical
        # The canonical name is also what the SDK uses to look up litellm
        # model_info (context window, max_output_tokens). A routing-only alias
        # like gpt-4.1 silently inherits gpt-4.1's caps — e.g. max_output_tokens
        # 32768 instead of gpt-5.5's 128000 — which truncates generations. Pin
        # the real caps so the alias affects ONLY the responses-vs-chat routing.
        mo = model_entry.get("OPENHANDS_MAX_OUTPUT_TOKENS")
        if mo:
            kwargs["max_output_tokens"] = int(mo)
        mi = model_entry.get("OPENHANDS_MAX_INPUT_TOKENS")
        if mi:
            kwargs["max_input_tokens"] = int(mi)
    # reasoning_effort is gated on the REAL model name in the chat path
    # (chat_options.select_chat_options), so it survives the canonical alias —
    # but it is only forwarded when explicitly set (default None => unset).
    effort = model_entry.get("OPENHANDS_REASONING_EFFORT")
    if effort:
        kwargs["reasoning_effort"] = effort
    return LLM(**kwargs)


def _build_conversation(prompt: str, cwd: Path, model_entry: dict, max_turns: int,
                        on_event):
    from openhands.sdk import Agent, Conversation, Tool
    from openhands.tools.file_editor import FileEditorTool
    from openhands.tools.task_tracker import TaskTrackerTool
    from openhands.tools.terminal import TerminalTool

    llm = build_llm(model_entry)
    agent = Agent(llm=llm, tools=[
        # Force the subprocess terminal backend: the box ships tmux 1.8 which
        # lacks `new-session -c`, so the default tmux backend fails to start.
        Tool(name=TerminalTool.name, params={"terminal_type": "subprocess"}),
        Tool(name=FileEditorTool.name),
        Tool(name=TaskTrackerTool.name),
    ])
    conversation = Conversation(
        agent=agent,
        workspace=str(cwd),
        callbacks=[on_event],
        max_iteration_per_run=max_turns,
        visualizer=None,
    )
    return llm, conversation


def _run_conversation_blocking(prompt: str, cwd: Path, model_entry: dict,
                               max_turns: int, log_path: Path) -> AgentResult:
    """Synchronous OpenHands turn-loop; runs inside a worker thread."""
    turns = {"n": 0}
    seen_text = {"last": "", "ratelimit": False, "refused": False}

    with open(log_path, "a", encoding="utf-8") as log:
        def w(line: str):
            log.write(line.rstrip("\n") + "\n")
            log.flush()

        def on_event(event):
            # Best-effort transcript + signal extraction; never raise from a callback.
            try:
                from openhands.sdk import LLMConvertibleEvent
            except Exception:  # noqa: BLE001
                LLMConvertibleEvent = ()  # type: ignore
            try:
                text = ""
                if isinstance(event, LLMConvertibleEvent):
                    turns["n"] += 1
                    msg = event.to_llm_message()
                    text = str(getattr(msg, "content", msg))
                else:
                    text = str(event)
                if len(text) > 2000:
                    text = text[:2000] + "...<truncated>"
                if text.strip():
                    w(text)
                    seen_text["last"] = text
                if _contains(text, RATELIMIT_MARKERS):
                    seen_text["ratelimit"] = True
                if _contains(text, REFUSAL_MARKERS):
                    seen_text["refused"] = True
            except Exception as e:  # noqa: BLE001
                w(f"[callback-error] {type(e).__name__}: {e}")

        w(f"\n===== openhands run_agent @ {time.strftime('%Y-%m-%d %H:%M:%S')} "
          f"cwd={cwd} model={_llm_model_id(model_entry)} max_turns={max_turns} =====")

        llm, conversation = _build_conversation(prompt, cwd, model_entry, max_turns, on_event)
        try:
            conversation.send_message(OPENHANDS_TOOL_PREAMBLE + prompt)
            conversation.run()
        except Exception as e:  # noqa: BLE001
            blob = f"{type(e).__name__}: {e}"
            w(f"[exception] {blob}")
            if seen_text["ratelimit"] or _contains(blob, RATELIMIT_MARKERS):
                raise RateLimited(blob[:300])
            return AgentResult(status="error", is_error=True, detail=blob,
                               tail=seen_text["last"][-2000:])

        if seen_text["ratelimit"]:
            raise RateLimited("ratelimit marker in transcript")

        status_str = ""
        try:
            status_str = str(conversation.state.execution_status)
        except Exception:  # noqa: BLE001
            pass
        cost = 0.0
        try:
            if llm.metrics is not None:
                cost = float(llm.metrics.accumulated_cost or 0.0)
        except Exception:  # noqa: BLE001
            pass

        is_error = "error" in status_str.lower() or "stuck" in status_str.lower()
        refused = seen_text["refused"]
        w(f"[result] execution_status={status_str} turns={turns['n']} "
          f"cost={cost} refused={refused}")
        return AgentResult(
            status="refused" if refused else ("error" if is_error else "success"),
            is_error=is_error,
            refused=refused,
            cost_usd=cost,
            num_turns=turns["n"],
            tail=seen_text["last"][-2000:],
            raw_subtype=status_str,
        )


async def run_agent(prompt: str, cwd: Path, log_path: Path, model_entry: dict,
                    *, max_turns: int = 200, timeout: float | None = 7200) -> AgentResult:
    """Run one OpenHands turn-loop in `cwd`, streaming a transcript to `log_path`.

    Signature-compatible with agent_runner.run_agent. The blocking SDK loop runs
    in a worker thread; an overall watchdog aborts via asyncio.wait_for.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    coro = asyncio.to_thread(
        _run_conversation_blocking, prompt, cwd, model_entry, max_turns, log_path)
    try:
        if timeout:
            return await asyncio.wait_for(coro, timeout=timeout)
        return await coro
    except asyncio.TimeoutError:
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"[watchdog] OVERALL TIMEOUT after {timeout}s — aborting\n")
        return AgentResult(status="error", is_error=True, detail="timeout_overall")
