#!/usr/bin/env bash
# TruePrice — one-command setup. Safe to re-run.
# Creates a virtual environment, installs dependencies, builds the dataset, and
# trains the pricing model. After this, run ./run.sh
set -e

cd "$(dirname "$0")"

echo "==> [1/4] Creating virtual environment (.venv) ..."
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
PY=".venv/bin/python"

echo "==> [2/4] Installing dependencies (free & open-source) ..."
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet -r requirements.txt

echo "==> [3/4] Generating the synthetic dataset ..."
"$PY" model/generate_data.py --rows 24000

echo "==> [4/4] Training the pricing model (prints held-out metrics) ..."
"$PY" model/train.py

echo ""
echo "✅ Setup complete. Start the app with:   ./run.sh"
echo "   Then open http://127.0.0.1:8000 in your browser."
