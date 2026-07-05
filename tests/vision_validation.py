"""
vision_validation.py — objective proof that the frame-quality metrics are reliable.

The user's requirement: "proofs that our productions are correct and reliable." For a
computer-vision layer, "reliable" has a precise, testable meaning — the metrics must respond
correctly and monotonically to controlled changes in the input. We construct synthetic frames
with KNOWN properties (known blur, known brightness, known motion, known glare) and verify each
metric moves the right way. If a metric didn't track ground truth, this harness would fail.

This is the reproducible evidence behind docs/08-vision.md §Reliability. It validates the
Python reference in backend/app/vision_metrics.py, which frontend/vision.js ports verbatim.

Run:  .venv/bin/python tests/vision_validation.py
"""
from __future__ import annotations
import os
import sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend", "app"))
import vision_metrics as vm  # noqa: E402

rng = np.random.default_rng(7)


def box_blur(img: np.ndarray, radius: int) -> np.ndarray:
    """Simple separable box blur (no scipy) to synthesize known amounts of defocus."""
    if radius <= 0:
        return img
    out = img.astype(np.float64).copy()
    k = 2 * radius + 1
    # horizontal then vertical moving average via cumulative sums
    for axis in (0, 1):
        cs = np.cumsum(np.pad(out, [(radius + 1, radius) if a == axis else (0, 0)
                                    for a in range(2)], mode="edge"), axis=axis)
        sl_hi = [slice(None)] * 2; sl_lo = [slice(None)] * 2
        sl_hi[axis] = slice(k, None); sl_lo[axis] = slice(0, -k)
        out = (cs[tuple(sl_hi)] - cs[tuple(sl_lo)]) / k
    return out


def base_scene() -> np.ndarray:
    """A detailed synthetic 'car-ish' scene: textured noise + hard edges (a sharp target)."""
    img = rng.integers(60, 200, size=(240, 320), endpoint=True).astype(np.float64)
    img[60:180, 80:240] = 40           # a dark panel (hard edges)
    img[90:150, 110:210] = 210         # a bright window
    return img


PASS, FAIL = "PASS", "FAIL"
results = []


def check(name, cond, detail=""):
    results.append((name, cond))
    print(f"  {PASS if cond else FAIL}  {name}" + (f"  — {detail}" if detail else ""))


def main():
    print("Vision metric validation (synthetic frames with known ground truth)")
    print("=" * 70)

    scene = base_scene()

    # 1) SHARPNESS must decrease monotonically as blur increases.
    print("\n[1] Sharpness (Laplacian variance) vs known blur radius")
    sharps = [vm.sharpness(box_blur(scene, r)) for r in (0, 1, 2, 4, 8)]
    print("    radius 0,1,2,4,8 ->", [round(s) for s in sharps])
    check("sharpness strictly decreases with blur",
          all(sharps[i] > sharps[i + 1] for i in range(len(sharps) - 1)))
    check("sharp frame is 'capturable', very blurry frame is not",
          vm.assess_frame(scene)["metrics"]["sharpness"] > vm.TH["sharp_ok"]
          and vm.assess_frame(box_blur(scene, 8))["metrics"]["sharpness"] < vm.TH["sharp_ok"])

    # 2) EXPOSURE mean must track brightness scaling; extremes must flag.
    print("\n[2] Exposure vs known brightness scaling")
    dark = np.clip(scene * 0.2, 0, 255)
    normal = scene
    bright = np.clip(scene * 1.8, 0, 255)
    md, mn, mb = (vm.exposure(x)["mean"] for x in (dark, normal, bright))
    print("    mean luma dark/normal/bright ->", round(md), round(mn), round(mb))
    check("mean luminance increases with brightness", md < mn < mb)
    check("dark frame flagged 'Too dark'", vm.assess_frame(dark)["status"] == "bad"
          and "dark" in vm.assess_frame(dark)["guidance"].lower())

    # 3) STABILITY must be ~0 for identical frames and large for shifted frames.
    print("\n[3] Stability vs known motion")
    still = vm.stability(scene, scene.copy())
    shifted = vm.stability(scene, np.roll(scene, 25, axis=1))
    print("    frame-diff still/shifted ->", round(still, 4), round(shifted, 4))
    check("still frames read as steady (~0)", still < 1e-9)
    check("shifted frames read as moving", shifted > vm.TH["unstable"])

    # 4) FRAMING must rise when the subject fills more of the frame ('move closer').
    print("\n[4] Framing / edge-density vs subject size")
    far = np.full((240, 320), 120.0); far[110:130, 150:170] = scene[110:130, 150:170]
    near = scene
    fr_far, fr_near = vm.framing(far), vm.framing(near)
    print("    edge density far/near ->", round(fr_far, 4), round(fr_near, 4))
    check("edge density higher when subject fills frame", fr_near > fr_far)
    check("far/empty frame triggers 'Move closer'",
          "closer" in vm.assess_frame(far)["guidance"].lower())

    # 5) GLARE must rise with a specular hotspot.
    print("\n[5] Glare vs known specular hotspot")
    glary = scene.copy(); glary[40:120, 40:160] = 255
    check("glare fraction rises with hotspot", vm.glare(glary) > vm.glare(scene))
    check("glare frame flagged", vm.assess_frame(glary)["status"] == "bad")

    # 6) End-to-end: a clean sharp well-lit frame is capturable with high quality.
    print("\n[6] End-to-end capture decision")
    good = vm.assess_frame(scene)
    print(f"    clean frame -> quality {good['quality']}, capturable {good['capturable']}")
    check("clean frame is high-quality & capturable",
          good["capturable"] and good["quality"] >= 65)

    total = len(results); passed = sum(1 for _, c in results if c)
    print("\n" + "=" * 70)
    print(f"{passed}/{total} reliability checks passed")
    print("These checks are deterministic (seeded) and reproducible — the objective proof")
    print("that the vision metrics respond correctly to real image properties.")
    return passed == total


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
