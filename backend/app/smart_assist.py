"""
smart_assist.py — OPTIONAL Gemini-powered signal detection for guided inspection.

This is the opt-in "Smart Assist" layer. The free, private, on-device computer vision
(vision.js / vision_metrics.py) remains the default and always runs. When — and only when —
a GEMINI_API_KEY is configured, a captured frame for a signal point (roof, wheel, dashboard,
engine bay, tyre, odometer) can additionally be sent to Google's Gemini multimodal model to
*suggest* the answer, which pre-fills the confirmation step.

Honesty rules (consistent with docs/06-responsible-ai.md and docs/08-vision.md):
  - Gemini's answer is a SUGGESTION with a self-reported confidence — never a silent verdict.
    The seller still confirms; the inspector still verifies.
  - It maps only to the SAME allowed option values the manual flow uses (from the catalog /
    condition specs) — no free-form claims.
  - Any error, timeout, or missing key degrades gracefully to the on-device flow.

Privacy note: enabling Smart Assist means a captured frame leaves the device and is sent to
Google. This is stated in the UI and docs. The on-device path sends nothing.

Implementation uses a direct REST call (stdlib urllib) — no extra dependency to install.
We cannot end-to-end test the live Gemini call here without a key; the code is structured so
the enabled/disabled and error paths are exercised, and the request/response shape follows the
documented generateContent API.
"""

from __future__ import annotations
import json
import urllib.request
import urllib.error

import config
from catalog import FEATURE_QUESTIONS
from evidence import REQUIRED_POINTS
import condition as cond

_ENDPOINT = ("https://generativelanguage.googleapis.com/v1beta/models/"
             "{model}:generateContent?key={key}")


def _spec_for_point(point_id: str):
    """Return (question, {value: description}) for a point's signal, or None."""
    sig = REQUIRED_POINTS.get(point_id)
    if not sig:
        return None
    kind, key = sig
    if kind == "variant":
        q = FEATURE_QUESTIONS[key]
        return q["question"], {str(v): lbl for v, lbl in q["options"].items()}, "enum"
    if kind == "condition":
        d = cond.DISCLOSURES[key]
        return d["question"], {v: opt["label"] for v, opt in d["options"].items()}, "enum"
    if kind == "odometer":
        return "Read the exact odometer reading in kilometres.", {}, "number"
    return None


def _call_gemini(prompt: str, image_b64: str, schema: dict) -> dict:
    body = {
        "contents": [{"parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}},
        ]}],
        "generationConfig": {"responseMimeType": "application/json",
                             "responseSchema": schema, "temperature": 0.0},
    }
    url = _ENDPOINT.format(model=config.GEMINI_MODEL, key=config.GEMINI_API_KEY)
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


def analyze(point_id: str, image_b64: str, make: str = "", model: str = "") -> dict:
    """Suggest the signal value for a captured frame. Always safe to call."""
    if not config.smart_assist_enabled():
        return {"available": False, "reason": "Smart Assist is not configured."}
    spec = _spec_for_point(point_id)
    if not spec:
        return {"available": False, "reason": "No detectable signal for this shot."}

    question, options, kind = spec
    ctx = f"The car is a {make} {model}. " if make else ""

    if kind == "enum":
        allowed = list(options.keys())
        opt_lines = "\n".join(f'  - "{v}": {desc}' for v, desc in options.items())
        prompt = (
            f"{ctx}You are assisting a used-car inspection. Look ONLY at the attached photo. "
            f"{question}\nChoose exactly one of these values based on what is visible:\n"
            f"{opt_lines}\n"
            f'If you cannot tell clearly, use "unsure". Report your confidence 0-1 and a very '
            f"short reason describing what you see.")
        schema = {"type": "object", "properties": {
            "value": {"type": "string", "enum": allowed + ["unsure"]},
            "confidence": {"type": "number"},
            "reason": {"type": "string"}}, "required": ["value", "confidence"]}
    else:  # number (odometer)
        prompt = (
            f"{ctx}Read the odometer in the attached photo. Return the total kilometres as an "
            f"integer. If you cannot read it clearly, set readable=false. Report confidence 0-1.")
        schema = {"type": "object", "properties": {
            "km": {"type": "integer"}, "readable": {"type": "boolean"},
            "confidence": {"type": "number"}}, "required": ["km", "readable", "confidence"]}

    try:
        out = _call_gemini(prompt, image_b64, schema)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            KeyError, ValueError, json.JSONDecodeError) as e:
        return {"available": False, "reason": f"Smart Assist unavailable ({type(e).__name__})."}

    if kind == "number":
        if not out.get("readable"):
            return {"available": True, "detected": None,
                    "confidence": float(out.get("confidence", 0)),
                    "note": "Couldn't read the odometer clearly — please type it."}
        return {"available": True, "detected": int(out["km"]), "kind": "odometer",
                "confidence": float(out.get("confidence", 0)),
                "note": "AI read the odometer — please confirm."}

    val = out.get("value", "unsure")
    if val == "unsure" or val not in options:
        return {"available": True, "detected": None,
                "confidence": float(out.get("confidence", 0)),
                "note": "AI wasn't sure — please pick what you see."}
    return {"available": True, "detected": val, "kind": kind,
            "label": options[val], "confidence": float(out.get("confidence", 0)),
            "reason": out.get("reason", ""),
            "note": "AI suggestion — please confirm."}
