#!/usr/bin/env bash
set -euo pipefail

VENV_DIR=".qtcreator"
ACTIVATES=( "$VENV_DIR"/Python_3_14_*venv/bin/activate )

if [ ! -f "${ACTIVATES[0]}" ]; then
    echo "❌ Virtual environment not found at $VENV_DIR/Python_3_14_*venv/bin/activate"
    exit 1
fi

source "${ACTIVATES[0]}"

echo "🔍 Running ruff lint..."
ruff check .

echo "🔍 Running ruff format check..."
ruff format --check .

echo "✅ All checks passed!"
