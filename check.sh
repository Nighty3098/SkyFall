#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="venv"
ACTIVATES=( "$VENV_DIR"/bin/activate )

if [ ! -f "${ACTIVATES[0]}" ]; then
    echo "❌ Virtual environment not found at $ACTIVATES"
    exit 1
fi

source "${ACTIVATES[0]}"

echo "🔍 Running ruff lint..."
ruff check .

echo "🔍 Running ruff format check..."
ruff format --check .

echo "✅ All checks passed!"
