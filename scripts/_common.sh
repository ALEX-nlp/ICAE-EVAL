# ============================================================
# Shared library — sourced by each evaluation-task script under scripts/.
# This file is NOT a task and must not be executed directly; it only handles
# interpreter selection, repo-root location, Oracle defaults, and the launcher
# wrapper.
# ============================================================

# Repo root (this file lives at <root>/scripts/).
ICAE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Python interpreter (must have claude_agent_sdk / anthropic installed). Prefer
# the environment created by setup.sh so callers do not need to activate it.
if [ -z "${PYTHON:-}" ] && [ -x "$ICAE_ROOT/.venv/bin/python" ]; then
    PYTHON="$ICAE_ROOT/.venv/bin/python"
else
    PYTHON="${PYTHON:-$(command -v python3)}"
fi

# http(s) proxy used INSIDE containers when installing dependencies. Disabled by
# default (direct download); the eval layer does a single proxied retry only if a
# direct download fails (see evaluate.py). Set explicitly when needed, e.g.:
#   PROXY="$(source ~/proxy.sh; echo ${https_proxy:-$http_proxy})" bash ...
# When PROXY is empty, run_orchestrator does not pass --proxy.
export PROXY="${PROXY:-}"

# Source of the fallback proxy address (the eval layer opens one proxied retry
# from it). Defaults to ~/proxy.sh; set to empty string to disable the fallback.
export PROXY_FALLBACK_FILE="${PROXY_FALLBACK_FILE:-$HOME/proxy.sh}"

# Oracle (User Agent) defaults; override via environment variables.
USER_HOST="${USER_HOST:-127.0.0.1}"
USER_INIT_PORT="${USER_INIT_PORT:-50001}"
USER_QUERY_PORT="${USER_QUERY_PORT:-50002}"
USER_EVAL_PORT="${USER_EVAL_PORT:-50003}"

# Experiment defaults (task scripts may override).
USER_MODEL_NAME="${USER_MODEL_NAME:-DeepSeek-V3.2}"
CRITIC_MODEL_NAME="${CRITIC_MODEL_NAME:-Deepseek-V4-Flash}"
QUERY_COUNT="${QUERY_COUNT:-16}"

# Agent-under-test framework: claude-code (default) | openhands
AGENT_FRAMEWORK="${AGENT_FRAMEWORK:-claude-code}"

# Single entry point to the orchestrator. First arg is the subcommand (run|eval),
# the rest is passed through verbatim.
run_orchestrator() {
    local subcmd="$1"; shift
    local launcher_args=(
        --user-host "$USER_HOST"
        --user-init-port "$USER_INIT_PORT"
        --user-query-port "$USER_QUERY_PORT"
        --user-eval-port "$USER_EVAL_PORT"
    )
    if [ "$subcmd" = "run" ]; then
        launcher_args+=(--agent-framework "$AGENT_FRAMEWORK")
    fi
    if [ -n "$PROXY" ]; then
        launcher_args+=(--proxy "$PROXY")
    fi
    if [ -n "$PROXY_FALLBACK_FILE" ]; then
        launcher_args+=(--proxy-fallback-file "$PROXY_FALLBACK_FILE")
    fi

    cd "$ICAE_ROOT"
    exec "$PYTHON" -m harness.orchestrator "$subcmd" \
        "${launcher_args[@]}" \
        "$@"
}
