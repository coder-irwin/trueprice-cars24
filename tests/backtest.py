"""
backtest.py — does TruePrice actually shrink the estimate-to-final-price gap?

This is the money question. We simulate two worlds over the same fresh sample of cars and
their realized auction prices (same data-generating process as training), and measure the
**below-floor rate** — the share of sellers whose FINAL price lands below the quoted floor.
That is the CEO's ~40% pain metric (docs/00-research.md §1).

  WORLD A — "Old front door" (type-your-variant):
      The seller enters a variant with aspiration bias (often one trim too high — the
      real "4 in 10 mismatch"). The estimate is computed on that ENTERED variant with a
      falsely-confident tight range. But reality pays for the TRUE variant.

  WORLD B — "TruePrice":
      The Variant Resolver recovers the true variant from feature evidence (usually
      right), and the range is WIDENED honestly when confidence is low. The estimate is
      computed on the resolved variant + confidence.

Everything downstream (inspection, auction noise) is identical. The only thing that
changes is the front door. Run:  .venv/bin/python tests/backtest.py
"""

from __future__ import annotations
import os
import sys
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "model"))
sys.path.insert(0, os.path.join(ROOT, "backend", "app"))

from catalog import CATALOG, get_model  # noqa: E402
import variant_resolver as vr           # noqa: E402
import pricing                           # noqa: E402
import generate_data as gd               # noqa: E402


def aspirational_variant(model, true_variant):
    """Seller aspiration bias: with some probability, name a trim one step ABOVE true."""
    ranks = sorted(model.variants, key=lambda v: v.trim_rank)
    idx = next(i for i, v in enumerate(ranks) if v.name == true_variant.name)
    if idx < len(ranks) - 1 and random.random() < 0.45:   # ~"4 in 10" mismatch, skewed up
        return ranks[idx + 1]
    if idx > 0 and random.random() < 0.10:                 # occasionally one below
        return ranks[idx - 1]
    return true_variant


def simulate_resolver(model, true_variant, rng):
    """Run the real resolver, answering from the TRUE variant's features, with a small
    chance of a mistaken answer (sellers misread a feature). Returns (variant, confidence,
    price_spread)."""
    answers = {}
    for _ in range(6):
        r = vr.resolve(model.make, model.model, answers)
        if r["resolved"] or not r["next_question"]:
            return r["top_variant"], r["confidence"], r["price_spread"]
        feat = r["next_question"]["feature"]
        true_val = true_variant.features.get(feat)
        # 8% chance the seller answers a visible feature wrong.
        if rng.random() < 0.08:
            opts = [o["value"] for o in r["next_question"]["options"] if o["value"] != true_val]
            answers[feat] = rng.choice(opts) if opts else true_val
        else:
            answers[feat] = true_val
    return r["top_variant"], r["confidence"], r["price_spread"]


def run(n=1500, seed=2024):
    rng = random.Random(seed)
    a_below = b_below = 0
    a_gap = b_gap = 0.0          # mean signed gap (final - floor), in ₹
    a_wid = b_wid = 0.0

    for _ in range(n):
        car = gd.sample_car(rng)
        model = get_model(car["make"], car["model"])
        true_variant = next(v for v in model.variants if v.name == car["variant"])
        final = gd.realized_price(car, rng)     # reality pays for the TRUE variant
        disc = {k: car[k] for k in
                ["accident", "aftermarket_cng", "service_records", "tyres", "insurance"]}

        # WORLD A: entered (possibly wrong) variant, falsely confident.
        entered = aspirational_variant(model, true_variant)
        carA = dict(car, variant=entered.name)
        eA = pricing.estimate(carA, model.segment, variant_confidence=1.0,
                              variant_price_spread=0.0, disclosures=disc,
                              include_breakdown=False)
        if final < eA["range_low"]:
            a_below += 1
        a_gap += final - eA["range_low"]
        a_wid += eA["width_pct"]

        # WORLD B: resolved variant + honest widening.
        rv, conf, spread = simulate_resolver(model, true_variant, rng)
        carB = dict(car, variant=rv)
        eB = pricing.estimate(carB, model.segment, variant_confidence=conf,
                              variant_price_spread=spread, disclosures=disc,
                              include_breakdown=False)
        if final < eB["range_low"]:
            b_below += 1
        b_gap += final - eB["range_low"]
        b_wid += eB["width_pct"]

    print("=" * 64)
    print(f"TruePrice backtest — {n:,} simulated sellers")
    print("=" * 64)
    print(f"{'':32s}{'Old front door':>15s}{'TruePrice':>15s}")
    print(f"{'Below-floor rate (the pain)':32s}"
          f"{a_below/n*100:>14.1f}%{b_below/n*100:>14.1f}%")
    print(f"{'Avg range width':32s}{a_wid/n:>14.1f}%{b_wid/n:>14.1f}%")
    print(f"{'Avg final − floor (₹)':32s}"
          f"{a_gap/n:>15,.0f}{b_gap/n:>15,.0f}")
    print("=" * 64)
    reduction = (a_below - b_below) / max(a_below, 1) * 100
    print(f"Below-floor rate cut by {reduction:.0f}% "
          f"({a_below/n*100:.1f}% → {b_below/n*100:.1f}%).")
    print("Mechanism: resolving the true variant removes the aspiration-bias overshoot;")
    print("honest widening covers the residual uncertainty instead of hiding it.")
    return {"a_below": a_below/n, "b_below": b_below/n}


if __name__ == "__main__":
    run()
