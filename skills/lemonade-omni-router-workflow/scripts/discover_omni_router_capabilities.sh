#!/usr/bin/env bash
set -euo pipefail

# Cross-platform wrapper that forwards args to the Python implementation.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="${SCRIPT_DIR}/discover_omni_router_capabilities.py"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "[error] Python is required but was not found (need python3 or python in PATH)." >&2
  exit 127
fi

exec "${PYTHON_BIN}" "${PY_SCRIPT}" "$@"
