#!/usr/bin/env bash
#
# Bootstrap ICAE-Bench:
#   1. create .venv and install Python dependencies;
#   2. download/export the language images and unpack the benchmark data.
#
# Usage:
#   bash setup.sh
#   bash setup.sh --skip-download
#   bash setup.sh --openhands
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON:-}"
INSTALL_OPENHANDS=false
SKIP_DOWNLOAD=false

usage() {
    cat <<'EOF'
Usage: bash setup.sh [options]

Options:
  --openhands       Also install the optional OpenHands dependencies (Python >= 3.12).
  --skip-download   Install Python dependencies only; do not download images/data.
  -h, --help        Show this help.

Environment:
  PYTHON             Python interpreter used to create .venv.
                     By default, setup selects an installed Python 3.11+.
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --openhands)
            INSTALL_OPENHANDS=true
            ;;
        --skip-download)
            SKIP_DOWNLOAD=true
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "[setup] unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

required_minor=11
if "$INSTALL_OPENHANDS"; then
    required_minor=12
fi

python_is_compatible() {
    local candidate="$1"
    command -v "$candidate" >/dev/null 2>&1 &&
        "$candidate" - "$required_minor" <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, int(sys.argv[1])) else 1)
PY
}

if [ -z "$PYTHON_BIN" ]; then
    for candidate in python3.11 python3.12 python3.13 python3.14 python3; do
        if python_is_compatible "$candidate"; then
            PYTHON_BIN="$(command -v "$candidate")"
            break
        fi
    done
fi

if [ -z "$PYTHON_BIN" ] || ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "[setup] No compatible Python interpreter was found." >&2
    echo "[setup] Install Python 3.$required_minor+ or set PYTHON=/path/to/python." >&2
    exit 1
fi

if ! "$PYTHON_BIN" - "$required_minor" <<'PY'
import sys

required = (3, int(sys.argv[1]))
if sys.version_info < required:
    print(
        f"[setup] Python {required[0]}.{required[1]}+ is required; "
        f"found {sys.version.split()[0]}.",
        file=sys.stderr,
    )
    raise SystemExit(1)
PY
then
    exit 1
fi

echo "[setup] using Python: $PYTHON_BIN ($("$PYTHON_BIN" --version 2>&1))"
echo "[setup] creating virtual environment: $ROOT/.venv"
"$PYTHON_BIN" -m venv "$ROOT/.venv"
VENV_PYTHON="$ROOT/.venv/bin/python"

echo "[setup] installing core Python dependencies"
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r "$ROOT/requirements.txt"

if "$INSTALL_OPENHANDS"; then
    echo "[setup] installing optional OpenHands dependencies"
    "$VENV_PYTHON" -m pip install -r "$ROOT/requirements-openhands.txt"
fi

if ! "$SKIP_DOWNLOAD"; then
    echo "[setup] downloading language images and benchmark data"
    bash "$ROOT/download_scaffold.sh"
fi

echo
echo "[setup] ready."
echo "[setup] next: configure model_list.json and user_agent/user_model.json"
echo "[setup] then run: ./run.sh"
