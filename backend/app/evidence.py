"""
evidence.py — score a guided-inspection Evidence Pack (server side).

The heavy computer vision runs in the browser (frontend/vision.js) on live camera frames or
uploaded media — raw pixels never leave the device (privacy). What reaches the server is a
compact, structured summary: which inspection points were captured, at what quality, and which
pricing signals they back. This module scores that pack into:

  - coverage        : captured points / required points
  - avg_quality     : mean capture quality (0-100)
  - evidence_strength : 0-1, how much the estimate can lean on captured proof vs self-report
  - backed_signals  : which variant/condition inputs are photo-backed

`evidence_strength` feeds pricing.estimate() as a small, honest confidence uplift — because an
input backed by a timestamped, quality-gated photo is more trustworthy than a typed dropdown
(recall: 4 in 10 typed variants are wrong). It is deliberately modest: evidence improves
*input trust*, it does not claim to have classified anything.
"""

from __future__ import annotations
from typing import List, Dict

# The inspection points a complete walkthrough should cover, and the signal each backs.
REQUIRED_POINTS = {
    "front": None, "rear": None, "left": None, "right": None,
    "roof": ("variant", "sunroof"),
    "wheel": ("variant", "wheels"),
    "dash": ("variant", "infotainment"),
    "odo": ("odometer", None),
    "engine": ("condition", "aftermarket_cng"),
    "tyre": ("condition", "tyres"),
}


def score(points: List[Dict]) -> dict:
    """points: [{id, captured: bool, quality: 0-100, ...}]"""
    by_id = {p["id"]: p for p in points}
    required = list(REQUIRED_POINTS)
    captured = [pid for pid in required if by_id.get(pid, {}).get("captured")]
    coverage = len(captured) / len(required)

    quals = [by_id[pid]["quality"] for pid in captured if "quality" in by_id[pid]]
    avg_quality = round(sum(quals) / len(quals)) if quals else 0

    # Evidence strength: mostly coverage, scaled by capture quality. Capped so it stays a
    # trust *aid*, never a substitute for inspection.
    evidence_strength = round(coverage * (0.5 + 0.5 * (avg_quality / 100)), 3)

    backed = []
    for pid in captured:
        sig = REQUIRED_POINTS[pid]
        if sig:
            backed.append({"point": pid, "signal_type": sig[0], "signal": sig[1]})

    return {
        "coverage": round(coverage, 3),
        "captured_count": len(captured),
        "required_count": len(required),
        "avg_quality": avg_quality,
        "evidence_strength": evidence_strength,
        "backed_signals": backed,
        "missing_points": [pid for pid in required if pid not in captured],
    }
