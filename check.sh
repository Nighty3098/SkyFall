#!/usr/bin/env bash
set -euo pipefail

VENV=".qtcreator/Python_3_14_5venv"
ACTIVATE="$VENV/bin/activate"

if [ ! -f "$ACTIVATE" ]; then
    echo "❌ Virtual environment not found at $ACTIVATE"
    exit 1
fi

source "$ACTIVATE"

echo "🔍 Running ruff lint..."
ruff check .

echo "🔍 Running ruff format check..."
ruff format --check .

echo "✅ All checks passed!"
