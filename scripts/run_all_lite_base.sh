#!/usr/bin/env bash
# ============================================================
# Driver: evaluate all CONFIGURED models compatible with the selected framework.
#   lite (realcode@001-050), each model at concurrency 4.
#
# Models run in parallel, each with internal concurrency 4. This can multiply
# load on the shared Oracle, Critic, Docker daemon, and any shared API quota.
#
# Each model gets its own append_id; logs go to results/_logs/base_lite_<model>_<ts>.log
#
# Usage:
#   bash scripts/run_all_lite_base.sh                  # configured models (parallel)
#   bash scripts/run_all_lite_base.sh GLM-5.1 Opus-4.8 # an explicit subset
# ============================================================
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/_common.sh"

if [ "$#" -gt 0 ]; then
    MODELS=("$@")
else
    # Read the registry instead of maintaining a stale hard-coded list. Only
    # include endpoints whose required fields no longer contain template values.
    MODEL_LINES="$("$PYTHON" - "$ICAE_ROOT/model_list.json" "$AGENT_FRAMEWORK" <<'PY'
import json
import sys
from pathlib import Path

registry = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
framework = sys.argv[2]

def configured(value):
    return bool(value) and not (isinstance(value, str) and ("<" in value or ">" in value))

for name, raw in registry.get("Tested Model", {}).items():
    entries = raw if isinstance(raw, list) else [raw]
    if framework == "openhands":
        candidates = [entry for entry in entries if entry.get("OPENHANDS_MODEL")]
        keys = ("OPENHANDS_MODEL", "OPENHANDS_BASE_URL", "OPENHANDS_API_KEY")
    else:
        candidates = [entry for entry in entries if not entry.get("OPENHANDS_MODEL")]
        keys = ("ANTHROPIC_MODEL", "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN")
    if any(all(configured(entry.get(key)) for key in keys) for entry in candidates):
        print(name)
PY
)"
    MODELS=()
    while IFS= read -r model; do
        [ -n "$model" ] && MODELS+=("$model")
    done <<<"$MODEL_LINES"
    if [ "${#MODELS[@]}" -eq 0 ]; then
        echo "[run_all_lite_base] no configured $AGENT_FRAMEWORK models found in model_list.json" >&2
        exit 1
    fi
fi

LOG_DIR="$ICAE_ROOT/results/_logs"
mkdir -p "$LOG_DIR"
TS="$(date +%Y%m%d_%H%M%S)"

echo "[run_all_lite_base] models (parallel): ${MODELS[*]}"
echo "[run_all_lite_base] env=base eval=lite concurrency=4/model user_model=$USER_MODEL_NAME"
echo "[run_all_lite_base] log dir: $LOG_DIR"

# Bash 3.2 compatibility (the default on macOS): use parallel indexed arrays
# rather than associative arrays.
export AGENT_FRAMEWORK
PIDS=()
PID_MODELS=()
for m in "${MODELS[@]}"; do
    log="$LOG_DIR/base_lite_${m}_${TS}.log"
    # Background parallel: a subshell isolates the `exec` inside run_lite_base.sh.
    # EXTRA_ARGS is passed to every model (e.g. --difficulty easy), word-split.
    bash "$HERE/run_lite_base.sh" "$m" ${EXTRA_ARGS:-} >"$log" 2>&1 &
    pid=$!
    PIDS+=("$pid")
    PID_MODELS+=("$m")
    echo "[run_all_lite_base] >>> started $m  pid=$pid  ($(date '+%H:%M:%S'))  -> $log"
done

# Wait for all to finish, report each model's exit code.
rc_total=0
for i in "${!PIDS[@]}"; do
    pid="${PIDS[$i]}"
    m="${PID_MODELS[$i]}"
    if wait "$pid"; then
        echo "[run_all_lite_base] <<< done $m"
    else
        rc=$?; rc_total=1
        echo "[run_all_lite_base] !!! $m failed (rc=$rc), see $LOG_DIR/base_lite_${m}_${TS}.log"
    fi
done

echo "[run_all_lite_base] all models processed (rc=$rc_total)."
exit "$rc_total"
