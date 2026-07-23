#!/usr/bin/env bash
#
# One-command ICAE-Bench runner.
#
# It starts the local User Agent (Oracle) when needed, waits for all three ports,
# runs a small evaluation, and stops only the Oracle process it started.
#
# Usage:
#   ./run.sh                              # Opus-4.8, one-repo smoke run
#   ./run.sh GLM-5.1                     # choose another configured model
#   RUN_LIMIT=50 ./run.sh Opus-4.8       # complete lite set
#   ./run.sh Opus-4.8 --difficulty easy  # pass any orchestrator option through
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CALLER_PYTHON="${PYTHON:-}"
source "$ROOT/scripts/_common.sh"

MODEL_NAME="${MODEL_NAME:-Opus-4.8}"
if [ "$#" -gt 0 ] && [[ "$1" != -* ]]; then
    MODEL_NAME="$1"
    shift
fi

RUN_LIMIT="${RUN_LIMIT:-1}"
ORACLE_PID=""
ORACLE_LOG="$ROOT/results/_logs/user_agent.log"

# These options affect run.sh's own preflight/Oracle lifecycle as well as the
# orchestrator. Accept both "--flag value" and "--flag=value" forms.
extra_args=("$@")
for ((index = 0; index < ${#extra_args[@]}; index++)); do
    argument="${extra_args[$index]}"
    case "$argument" in
        --model-name)
            index=$((index + 1))
            MODEL_NAME="${extra_args[$index]:?--model-name requires a value}"
            ;;
        --model-name=*)
            MODEL_NAME="${argument#*=}"
            ;;
        --limit)
            index=$((index + 1))
            RUN_LIMIT="${extra_args[$index]:?--limit requires a value}"
            ;;
        --limit=*)
            RUN_LIMIT="${argument#*=}"
            ;;
        --concurrency)
            index=$((index + 1))
            CONCURRENCY="${extra_args[$index]:?--concurrency requires a value}"
            ;;
        --concurrency=*)
            CONCURRENCY="${argument#*=}"
            ;;
        --agent-framework)
            index=$((index + 1))
            AGENT_FRAMEWORK="${extra_args[$index]:?--agent-framework requires a value}"
            ;;
        --agent-framework=*)
            AGENT_FRAMEWORK="${argument#*=}"
            ;;
        --user-host)
            index=$((index + 1))
            USER_HOST="${extra_args[$index]:?--user-host requires a value}"
            ;;
        --user-host=*)
            USER_HOST="${argument#*=}"
            ;;
        --user-init-port)
            index=$((index + 1))
            USER_INIT_PORT="${extra_args[$index]:?--user-init-port requires a value}"
            ;;
        --user-init-port=*)
            USER_INIT_PORT="${argument#*=}"
            ;;
        --user-query-port)
            index=$((index + 1))
            USER_QUERY_PORT="${extra_args[$index]:?--user-query-port requires a value}"
            ;;
        --user-query-port=*)
            USER_QUERY_PORT="${argument#*=}"
            ;;
        --user-eval-port)
            index=$((index + 1))
            USER_EVAL_PORT="${extra_args[$index]:?--user-eval-port requires a value}"
            ;;
        --user-eval-port=*)
            USER_EVAL_PORT="${argument#*=}"
            ;;
        --user-model-name)
            index=$((index + 1))
            USER_MODEL_NAME="${extra_args[$index]:?--user-model-name requires a value}"
            ;;
        --user-model-name=*)
            USER_MODEL_NAME="${argument#*=}"
            ;;
    esac
done

usage() {
    cat <<'EOF'
Usage: ./run.sh [model-name] [orchestrator options...]

Defaults:
  model-name       Opus-4.8 (or $MODEL_NAME)
  scope            one repo from the lite set (or $RUN_LIMIT)
  concurrency      4 (or $CONCURRENCY)
  framework        claude-code (or $AGENT_FRAMEWORK)

Examples:
  ./run.sh
  ./run.sh GLM-5.1 --difficulty easy
  RUN_LIMIT=50 ./run.sh Opus-4.8
  AGENT_FRAMEWORK=openhands ./run.sh GPT-5.5
EOF
}

for argument in "$@"; do
    if [ "$argument" = "-h" ] || [ "$argument" = "--help" ]; then
        usage
        if "$PYTHON" -c "import anthropic, claude_agent_sdk" >/dev/null 2>&1; then
            echo
            "$PYTHON" -m harness.orchestrator run --help
        fi
        exit 0
    fi
done

cd "$ROOT"

if [ ! -x "$ROOT/.venv/bin/python" ] && [ -z "$CALLER_PYTHON" ]; then
    echo "[run] .venv not found. Run 'bash setup.sh' first." >&2
    exit 1
fi

if ! "$PYTHON" -c "import anthropic, claude_agent_sdk, fastapi, requests" >/dev/null 2>&1; then
    echo "[run] Python dependencies are missing from: $PYTHON" >&2
    echo "[run] Run 'bash setup.sh' first." >&2
    exit 1
fi

if [ "$AGENT_FRAMEWORK" = "openhands" ] &&
   ! "$PYTHON" -c "import openhands.sdk, openhands.tools" >/dev/null 2>&1; then
    echo "[run] OpenHands dependencies are missing from: $PYTHON" >&2
    echo "[run] Run 'bash setup.sh --openhands' with Python >= 3.12." >&2
    exit 1
fi

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    echo "[run] Docker is not available. Start Docker and retry." >&2
    exit 1
fi

if [ ! -d "${ICAE_DOCKER_LANG_DIR:-$ROOT/docker_lang_official}" ] ||
   [ ! -d "${ICAE_GOLDEN_REPOS_DIR:-$ROOT/realcode_repos}" ] ||
   [ ! -d "${ICAE_RCB_TESTS_DIR:-$ROOT/rcb_tests_repos}" ]; then
    echo "[run] benchmark images/data are missing. Run 'bash setup.sh' first." >&2
    exit 1
fi

if [ "$AGENT_FRAMEWORK" = "claude-code" ]; then
    CLAUDE_COMMAND="${ICAE_CLAUDE_CLI:-claude}"
    if ! command -v "$CLAUDE_COMMAND" >/dev/null 2>&1 && [ ! -x "$CLAUDE_COMMAND" ]; then
        echo "[run] Claude Code CLI not found: $CLAUDE_COMMAND" >&2
        echo "[run] Install it or set ICAE_CLAUDE_CLI=/path/to/claude." >&2
        exit 1
    fi
fi

validate_model_config() {
    local validate_oracle_config="$1"
    "$PYTHON" - \
        "$MODEL_NAME" \
        "$USER_MODEL_NAME" \
        "$AGENT_FRAMEWORK" \
        "$validate_oracle_config" <<'PY'
import json
import sys
from pathlib import Path

root = Path.cwd()
model_name, user_model_name, framework, validate_oracle = sys.argv[1:]

def placeholder(value):
    return isinstance(value, str) and ("<" in value or ">" in value)

model_file = root / "model_list.json"
user_file = root / "user_agent" / "user_model.json"
models = json.loads(model_file.read_text(encoding="utf-8"))
users = json.loads(user_file.read_text(encoding="utf-8"))

tested = models.get("Tested Model", {})
if model_name not in tested:
    raise SystemExit(
        f"[run] model '{model_name}' is not in model_list.json. "
        f"Available: {', '.join(sorted(tested))}"
    )

entries = tested[model_name]
entries = entries if isinstance(entries, list) else [entries]
if framework == "openhands":
    selected = [entry for entry in entries if entry.get("OPENHANDS_MODEL")] or entries
else:
    selected = [entry for entry in entries if not entry.get("OPENHANDS_MODEL")] or entries

def endpoint_is_usable(entry):
    if framework == "openhands" and entry.get("OPENHANDS_MODEL"):
        required = ("OPENHANDS_MODEL", "OPENHANDS_BASE_URL", "OPENHANDS_API_KEY")
    else:
        required = ("ANTHROPIC_MODEL", "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN")
    return all(entry.get(key) and not placeholder(entry[key]) for key in required)

usable = [entry for entry in selected if endpoint_is_usable(entry)]
if not usable:
    raise SystemExit(
        f"[run] '{model_name}' has no configured {framework} endpoint in "
        "model_list.json (template placeholders are still present)."
    )

if validate_oracle != "true":
    raise SystemExit(0)

if user_model_name not in users:
    raise SystemExit(
        f"[run] Oracle model '{user_model_name}' is not in "
        "user_agent/user_model.json."
    )
user_entries = users[user_model_name]
user_entries = user_entries if isinstance(user_entries, list) else [user_entries]
user_keys = {
    "anthropic": ("model_name", "base_url", "auth_token"),
    "openai": ("model_name", "base_url", "api_key"),
}
if not any(
    all(entry.get(key) and not placeholder(entry[key])
        for key in user_keys.get(entry.get("api_type"), ()))
    for entry in user_entries
    if entry.get("api_type") in user_keys
):
    raise SystemExit(
        f"[run] Oracle model '{user_model_name}' is not configured in "
        "user_agent/user_model.json."
    )
PY
}

ports_ready() {
    "$PYTHON" - "$USER_HOST" "$USER_INIT_PORT" "$USER_QUERY_PORT" "$USER_EVAL_PORT" <<'PY'
import socket
import sys

host = sys.argv[1]
ports = [int(value) for value in sys.argv[2:]]
for port in ports:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            pass
    except OSError:
        raise SystemExit(1)
PY
}

wait_for_oracle() {
    "$PYTHON" - "$USER_HOST" "$USER_INIT_PORT" "$USER_QUERY_PORT" "$USER_EVAL_PORT" <<'PY'
import socket
import sys
import time

host = sys.argv[1]
ports = [int(value) for value in sys.argv[2:]]
deadline = time.monotonic() + 30
while time.monotonic() < deadline:
    ready = True
    for port in ports:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                pass
        except OSError:
            ready = False
            break
    if ready:
        raise SystemExit(0)
    time.sleep(0.5)
raise SystemExit(1)
PY
}

stop_oracle() {
    if [ -n "$ORACLE_PID" ] && kill -0 "$ORACLE_PID" >/dev/null 2>&1; then
        echo "[run] stopping local Oracle (pid=$ORACLE_PID)"
        kill "$ORACLE_PID" >/dev/null 2>&1 || true
        wait "$ORACLE_PID" 2>/dev/null || true
    fi
}
trap stop_oracle EXIT

VALIDATE_ORACLE_CONFIG=false
case "$USER_HOST" in
    127.0.0.1|localhost|0.0.0.0)
        VALIDATE_ORACLE_CONFIG=true
        ;;
esac
validate_model_config "$VALIDATE_ORACLE_CONFIG"

case "$USER_HOST" in
    127.0.0.1|localhost|0.0.0.0)
        if ports_ready; then
            echo "[run] reusing Oracle at $USER_HOST:$USER_INIT_PORT-$USER_EVAL_PORT"
        elif [ "$USER_INIT_PORT" != "50001" ] ||
             [ "$USER_QUERY_PORT" != "50002" ] ||
             [ "$USER_EVAL_PORT" != "50003" ]; then
            echo "[run] no Oracle is listening on the custom local ports." >&2
            echo "[run] start it separately, or use the default ports 50001-50003." >&2
            exit 1
        else
            mkdir -p "$(dirname "$ORACLE_LOG")"
            echo "[run] starting local Oracle (log: $ORACLE_LOG)"
            "$PYTHON" "$ROOT/user_agent/main.py" >>"$ORACLE_LOG" 2>&1 &
            ORACLE_PID=$!
            if ! wait_for_oracle; then
                echo "[run] Oracle did not become ready; see $ORACLE_LOG" >&2
                exit 1
            fi
        fi
        ;;
    *)
        echo "[run] using remote Oracle at $USER_HOST"
        ;;
esac

echo "[run] model=$MODEL_NAME scope=lite limit=$RUN_LIMIT concurrency=${CONCURRENCY:-4}"
bash "$ROOT/scripts/run_lite_base.sh" \
    "$MODEL_NAME" \
    --limit "$RUN_LIMIT" \
    "$@"
