#!/usr/bin/env bash
# TruePrice — start the app. Run ./setup.sh first if you haven't.
set -e
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  echo "❌ No virtual environment found. Run ./setup.sh first."
  exit 1
fi
if [ ! -f "model/pricing_model.joblib" ]; then
  echo "❌ Model not built yet. Run ./setup.sh first."
  exit 1
fi

echo "🚗 TruePrice running at http://127.0.0.1:8000  (press Ctrl+C to stop)"
echo "   Seller wizard:      http://127.0.0.1:8000/"
echo "   Guided inspection:  http://127.0.0.1:8000/inspect.html"
exec .venv/bin/python backend/run.py
