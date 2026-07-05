"""
vision_metrics.py — the reference implementation of TruePrice's frame-quality metrics.

These are the SAME algorithms the browser runs live on camera frames (frontend/vision.js is
a faithful port of this file). We keep a Python reference so the algorithms can be validated
objectively and reproducibly on controlled inputs — that validation (tests/vision_validation.py)
is our "proof" that the analysis is real and reliable, not static or hand-wavy.

Every metric here is a standard, well-understood computer-vision measure operating on the
luminance (grayscale) of a frame:

  sharpness  — variance of the Laplacian. The classic focus/blur measure: a sharp, in-focus
               image has strong second derivatives (edges) → high Laplacian variance; a blurry
               image is smooth → low variance. (Pech-Pacheco et al., 2000.)
  exposure   — mean luminance + fraction of blown/crushed pixels. Detects too-dark/too-bright.
  stability  — mean absolute frame-to-frame luminance difference. High motion → unstable.
  framing    — edge density (fraction of pixels on a strong gradient). Proxy for how much
               real subject detail fills the frame → drives "move closer".
  glare      — fraction of near-saturated specular pixels. Detects reflections/hotspots.

All functions take float luminance arrays in [0, 255].
"""

from __future__ import annotations
import numpy as np


def to_luma(rgb: np.ndarray) -> np.ndarray:
    """RGB (H,W,3) uint8/float -> luminance (H,W) float, Rec. 601 weights."""
    rgb = rgb.astype(np.float64)
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


def sharpness(luma: np.ndarray) -> float:
    """Variance of the Laplacian. Higher = sharper/more in focus."""
    lap = (-4.0 * luma[1:-1, 1:-1]
           + luma[:-2, 1:-1] + luma[2:, 1:-1]
           + luma[1:-1, :-2] + luma[1:-1, 2:])
    return float(lap.var())


def exposure(luma: np.ndarray) -> dict:
    mean = float(luma.mean())
    blown = float((luma > 240).mean())      # fraction near-white
    crushed = float((luma < 15).mean())     # fraction near-black
    return {"mean": mean, "blown": blown, "crushed": crushed}


def stability(luma: np.ndarray, prev_luma: np.ndarray | None) -> float:
    """Mean absolute frame-to-frame difference, normalized to [0,1]. Lower = steadier.
    Returns 0.0 (perfectly steady) when there is no previous frame."""
    if prev_luma is None or prev_luma.shape != luma.shape:
        return 0.0
    return float(np.abs(luma - prev_luma).mean() / 255.0)


def framing(luma: np.ndarray) -> float:
    """Edge density: fraction of pixels whose gradient magnitude exceeds a threshold.
    A close, detailed subject fills the frame with edges; a far/empty frame has few."""
    gx = luma[1:-1, 2:] - luma[1:-1, :-2]
    gy = luma[2:, 1:-1] - luma[:-2, 1:-1]
    mag = np.hypot(gx, gy)
    return float((mag > 40).mean())


def glare(luma: np.ndarray) -> float:
    return float((luma > 250).mean())


# ---- Assessment: turn raw metrics into guidance + a capturable decision -----------------
# Thresholds are deliberately explicit and documented so behaviour is auditable.
TH = {
    "sharp_ok": 120.0,      # Laplacian variance above this = acceptably sharp
    "sharp_good": 300.0,    # clearly sharp
    "dark": 55.0,           # mean luma below this = too dark
    "bright": 205.0,        # mean luma above this = too bright
    "blown": 0.12,          # >12% blown pixels = overexposed/glare
    "unstable": 0.045,      # frame-diff above this = moving
    "framing_min": 0.020,   # edge density below this = subject too far / empty
    "glare": 0.06,
}


def assess_frame(luma: np.ndarray, prev_luma: np.ndarray | None = None) -> dict:
    """Return metrics, a single actionable guidance message, a 0-100 quality score, and
    whether this frame is good enough to auto-capture. Mirrors frontend/vision.js."""
    s = sharpness(luma)
    ex = exposure(luma)
    st = stability(luma, prev_luma)
    fr = framing(luma)
    gl = glare(luma)

    # Priority-ordered guidance (fix the most disqualifying problem first).
    guidance, status = "Looks great — hold still", "good"
    if ex["mean"] < TH["dark"]:
        guidance, status = "Too dark — find better light", "bad"
    elif ex["mean"] > TH["bright"] or ex["blown"] > TH["blown"] or gl > TH["glare"]:
        guidance, status = "Too much glare — change your angle", "bad"
    elif fr < TH["framing_min"]:
        guidance, status = "Move closer to fill the frame", "bad"
    elif st > TH["unstable"]:
        guidance, status = "Hold steady", "warn"
    elif s < TH["sharp_ok"]:
        guidance, status = "Hold steady to focus", "warn"

    # Quality score (0-100): a transparent blend of the normalized sub-scores.
    def clip01(x): return max(0.0, min(1.0, x))
    q_sharp = clip01((s - TH["sharp_ok"]) / (TH["sharp_good"] - TH["sharp_ok"]))
    q_expo = clip01(1 - abs(ex["mean"] - 130) / 130) * (1 - clip01(ex["blown"] / 0.25))
    q_frame = clip01(fr / 0.06)
    q_stable = clip01(1 - st / TH["unstable"]) if prev_luma is not None else 1.0
    q_glare = clip01(1 - gl / 0.12)
    quality = round(100 * (0.35 * q_sharp + 0.25 * q_expo + 0.20 * q_frame
                           + 0.12 * q_stable + 0.08 * q_glare))

    capturable = (status == "good") and quality >= 65

    return {
        "metrics": {"sharpness": round(s, 1), "mean_luma": round(ex["mean"], 1),
                    "blown": round(ex["blown"], 4), "stability": round(st, 4),
                    "framing": round(fr, 4), "glare": round(gl, 4)},
        "guidance": guidance, "status": status,
        "quality": int(quality), "capturable": bool(capturable),
    }
