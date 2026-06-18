#!/usr/bin/env bash
set -euo pipefail

VENV=".qtcreator/Python_3_14_5venv"
ACTIVATE="$VENV/bin/activate"

if [ ! -f "$ACTIVATE" ]; then
    echo "❌ Virtual environment not found at $ACTIVATE"
    exit 1
fi

source "$ACTIVATE"

echo "🎨 Running ruff format..."
ruff format .

echo "🎨 Running ruff check --fix..."
ruff check --fix .

echo "✅ Formatting complete!"
