#!/usr/bin/env bash
# ============================================================
# Driver: evaluate ALL tested models under the base-language environment.
#   lite (realcode@001-050), each model at concurrency 4.
#
#   *** Fully parallel ***: each tested model uses its own API endpoint (no shared
#   quota), so all models run at once (each with internal concurrency 4). Only the
#   Oracle (User Agent) and Critic models are shared, but they are a small fraction
#   of the pipeline time and are not the bottleneck.
#
# Each model gets its own append_id; logs go to results/_logs/base_lite_<model>_<ts>.log
#
# Usage:
#   bash scripts/run_all_lite_base.sh                 # all default models (parallel)
#   bash scripts/run_all_lite_base.sh GLM-5.1 GPT-5.5 # a subset (parallel)
# ============================================================
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/_common.sh"

# Tested models (keys of model_list.json['Tested Model']).
DEFAULT_MODELS=(GLM-5.1 MiniMax-M2.5 Claude-Sonnet-4.6 GPT-5.5 Opus-4.8)
if [ "$#" -gt 0 ]; then
    MODELS=("$@")
else
    MODELS=("${DEFAULT_MODELS[@]}")
fi

LOG_DIR="$ICAE_ROOT/results/_logs"
mkdir -p "$LOG_DIR"
TS="$(date +%Y%m%d_%H%M%S)"

echo "[run_all_lite_base] models (parallel): ${MODELS[*]}"
echo "[run_all_lite_base] env=base eval=lite concurrency=4/model user_model=$USER_MODEL_NAME"
echo "[run_all_lite_base] log dir: $LOG_DIR"

declare -A PID2MODEL
for m in "${MODELS[@]}"; do
    log="$LOG_DIR/base_lite_${m}_${TS}.log"
    # Background parallel: a subshell isolates the `exec` inside run_lite_base.sh.
    # EXTRA_ARGS is passed to every model (e.g. --difficulty easy), word-split.
    bash "$HERE/run_lite_base.sh" "$m" ${EXTRA_ARGS:-} >"$log" 2>&1 &
    pid=$!
    PID2MODEL[$pid]=$m
    echo "[run_all_lite_base] >>> started $m  pid=$pid  ($(date '+%H:%M:%S'))  -> $log"
done

# Wait for all to finish, report each model's exit code.
rc_total=0
for pid in "${!PID2MODEL[@]}"; do
    m="${PID2MODEL[$pid]}"
    if wait "$pid"; then
        echo "[run_all_lite_base] <<< done $m"
    else
        rc=$?; rc_total=1
        echo "[run_all_lite_base] !!! $m failed (rc=$rc), see $LOG_DIR/base_lite_${m}_${TS}.log"
    fi
done

echo "[run_all_lite_base] all models processed (rc=$rc_total)."
exit "$rc_total"
