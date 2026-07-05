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
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=False)
