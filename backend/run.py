"""
run.py — launch the TruePrice server.

Wires sys.path so the flat modules in model/ and backend/app/ import cleanly, then
starts Uvicorn. Run from the repo root:

    .venv/bin/python backend/run.py            # serves http://127.0.0.1:8000
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (os.path.join(ROOT, "model"), os.path.join(ROOT, "backend", "app")):
    if p not in sys.path:
        sys.path.insert(0, p)

import uvicorn  # noqa: E402

if __name__ == "__main__":
    # Friendly guard: the app needs the trained model. If it's missing, tell the user
    # exactly what to do instead of failing later on the first request.
    model_path = os.path.join(ROOT, "model", "pricing_model.joblib")
    if not os.path.exists(model_path):
        sys.exit(
            "\n❌ Pricing model not found (model/pricing_model.joblib).\n"
            "   Build it first:\n"
            "     python model/generate_data.py --rows 24000\n"
            "     python model/train.py\n"
            "   ...or just run ./setup.sh once.\n")

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    print(f"🚗 TruePrice → http://{host}:{port}  (Ctrl+C to stop)")
    uvicorn.run("main:app", host=host, port=port, reload=False)
