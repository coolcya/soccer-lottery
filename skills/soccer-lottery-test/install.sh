#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "Python 3 was not found on PATH. Install Python 3.10 or newer and rerun install.sh." >&2
    exit 1
  fi
fi

if [[ ! -d ".venv" ]]; then
  "$PYTHON_BIN" -m venv .venv
fi

VENV_PYTHON="$ROOT/.venv/bin/python"
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r requirements.txt

if [[ ! -f "config.yaml" ]]; then
  cp config.example.yaml config.yaml
  echo "Created config.yaml. Add your Football-Data.org API key before running the skill."
fi

echo "Installed soccer-lottery-test in $ROOT"
echo "Python: $VENV_PYTHON"
