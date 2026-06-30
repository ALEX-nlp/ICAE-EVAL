#!/usr/bin/env bash
# ============================================================
# Task: evaluate ONE model under the base-language environment (lite, conc 4).
#   env-mode base -> docker_lang_official/<repo-language>.tar
#   (no project source / no detailed PRD; the agent works from the fuzzy PRD)
#
# Usage:
#   bash scripts/run_lite_base.sh <model-name> [extra orchestrator args...]
# Examples:
#   bash scripts/run_lite_base.sh Opus-4.8
#   bash scripts/run_lite_base.sh GPT-5.5 --append-id <id>   # resume
# ============================================================
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

MODEL_NAME="${1:?usage: run_lite_base.sh <model-name> [extra args...]}"; shift || true

CONCURRENCY="${CONCURRENCY:-4}"

run_orchestrator run \
    --model-name      "$MODEL_NAME" \
    --env-mode        base \
    --eval-mode       lite \
    --prd-type        "$PRD_TYPE" \
    --user-model-name "$USER_MODEL_NAME" \
    --critic-model-name "$CRITIC_MODEL_NAME" \
    --query-count     "$QUERY_COUNT" \
    --concurrency     "$CONCURRENCY" \
    "$@"
