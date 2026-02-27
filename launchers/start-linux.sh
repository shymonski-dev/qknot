#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_COMMAND="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_COMMAND="python"
else
  echo "Python is required. Install Python 3.10, 3.11, or 3.12." >&2
  exit 1
fi

cd "$PROJECT_DIR"
exec "$PYTHON_COMMAND" scripts/start-standalone.py
