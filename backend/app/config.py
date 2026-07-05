"""
config.py — tiny, dependency-free config loader for optional features.

Reads a .env file at the repo root (if present) into os.environ, then exposes the
Smart Assist (Gemini) settings. No third-party dependency — we parse .env ourselves so
the free/on-device default path stays free and installable anywhere.

Smart Assist is OFF unless GEMINI_API_KEY is set. Everything degrades gracefully.
"""

from __future__ import annotations
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load_dotenv():
    path = os.path.join(_ROOT, ".env")
    if not os.path.exists(path):
        return
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                # don't overwrite a real environment variable
                os.environ.setdefault(k, v)
    except OSError:
        pass


_load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()


def smart_assist_enabled() -> bool:
    return bool(GEMINI_API_KEY)
