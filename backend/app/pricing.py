"""
pricing.py — the honest estimate engine (Pillar 3).

Turns a fully-specified car into a seller-facing estimate that is honest in three ways:

  1. RANGE, not a point. We predict P10/P50/P90 directly (quantile models), so the
     spread reflects genuine data uncertainty — never a cosmetic ± band.

  2. WIDENED under input uncertainty. The model's own range assumes the variant and
     condition are known-true. When the Variant Resolver is unsure, or condition is
     undisclosed, we WIDEN the range and lower the confidence — because that is the
     real source of the estimate-to-final gap (variant mismatch worth 15-20%).

  3. EXPLAINED. Every estimate ships with a factor breakdown (computed by ablating the
     actual model) and a plain-language "what could change at inspection." No black box.

This is the operationalization of docs/00-research.md §4 (Responsible AI).
"""

from __future__ import annotations
import os
from typing import Dict, Optional

import numpy as np
import pandas as pd
from joblib import load

from features import build_feature_row, FEATURE_COLUMNS
import condition as cond

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..",
                           "model", "pricing_model.joblib")

_BUNDLE = None


def _bundle():
    global _BUNDLE
    if _BUNDLE is None:
        _BUNDLE = load(_MODEL_PATH)
    return _BUNDLE


def _predict_quantiles(feature_row: Dict[str, object]) -> Dict[str, float]:
    df = pd.DataFrame([feature_row], columns=FEATURE_COLUMNS)
    models = _bundle()["models"]
    p10 = float(models["p10"].predict(df)[0])
    p50 = float(models["p50"].predict(df)[0])
    p90 = float(models["p90"].predict(df)[0])
    # Guard against quantile crossing.
    lo, hi = min(p10, p50, p90), max(p10, p50, p90)
    p50 = min(max(p50, lo), hi)
    return {"p10": lo, "p50": p50, "p90": hi}


def _round_k(x: float) -> int:
    return int(round(x, -3))


def explain(car: dict, segment: str) -> list:
    """Model-based breakdown: how much each real-world factor moves THIS car's price,
    measured by ablating the actual model against a clean reference of the same variant.

    Reference = same car but 1 owner, expected km for its age, and best-case condition.
    Each factor's contribution is the change in P50 when we flip just that factor from
    its clean value to the car's actual value. Honest, model-derived, additive-in-story.
    """
    models = _bundle()["models"]

    clean = dict(car)
    clean.update({"owners": 1, "km": car["age"] * 12000, "accident": "none",
                  "aftermarket_cng": "no", "service_records": "full", "tyres": "good",
                  "insurance": "comprehensive"})

    # Build every mutated-car scenario, then predict them all in ONE batched call
    # (single-row predict has a fixed ~50ms overhead; batching keeps explain cheap).
    scenarios = []  # (label, note, mutated_car)
    if car["km"] > clean["km"] * 1.05 or car["km"] < clean["km"] * 0.95:
        c = dict(clean); c["km"] = car["km"]
        scenarios.append(("Odometer vs typical for age",
                          f"{car['km']:,} km vs ~{clean['km']:,} km expected at "
                          f"{car['age']} yr", c))
    if car["owners"] > 1:
        c = dict(clean); c["owners"] = car["owners"]
        scenarios.append(("Ownership", f"{car['owners']} owners", c))
    if car.get("accident", "none") != "none":
        c = dict(clean); c["accident"] = car["accident"]
        scenarios.append(("Accident / repaint",
                          cond.describe("accident", car["accident"])["label"], c))
    if car.get("aftermarket_cng", "no") == "yes":
        c = dict(clean); c["aftermarket_cng"] = "yes"
        scenarios.append(("Aftermarket CNG",
                          cond.describe("aftermarket_cng", "yes")["label"], c))
    if car.get("service_records", "full") != "full":
        c = dict(clean); c["service_records"] = car["service_records"]
        scenarios.append(("Service history",
                          cond.describe("service_records", car["service_records"])["label"], c))
    if car.get("tyres", "good") != "good":
        c = dict(clean); c["tyres"] = car["tyres"]
        scenarios.append(("Tyres", cond.describe("tyres", car["tyres"])["label"], c))
    if car.get("insurance", "comprehensive") != "comprehensive":
        c = dict(clean); c["insurance"] = car["insurance"]
        scenarios.append(("Insurance / NCB",
                          cond.describe("insurance", car["insurance"])["label"], c))

    rows = [build_feature_row(clean, segment)] + \
           [build_feature_row(s[2], segment) for s in scenarios]
    preds = models["p50"].predict(pd.DataFrame(rows, columns=FEATURE_COLUMNS))
    base = float(preds[0])

    factors = []
    for (label, note, _), pred in zip(scenarios, preds[1:]):
        delta = float(pred) - base
        if abs(delta) >= 1000:
            factors.append({"label": label, "delta": _round_k(delta), "note": note})

    return {"clean_reference": _round_k(base), "factors": factors}


def estimate(car: dict, segment: str,
             variant_confidence: float = 1.0,
             variant_price_spread: float = 0.0,
             disclosures: Optional[Dict[str, str]] = None,
             include_breakdown: bool = True,
             evidence_strength: float = 0.0) -> dict:
    """Produce the honest estimate for a fully-specified car.

    variant_confidence  : top posterior from the resolver (1.0 if user is certain).
    variant_price_spread : ₹ spread across still-plausible variants (epistemic $ risk).
    disclosures          : condition answers, for completeness scoring + widening.
    """
    disclosures = disclosures or cond.default_disclosures()
    feature_row = build_feature_row(car, segment)
    q = _predict_quantiles(feature_row)
    p50 = q["p50"]

    # --- Confidence score (0-100) -------------------------------------------------
    disc_complete = cond.completeness(disclosures)
    confidence = 100.0 * (0.6 * variant_confidence + 0.4 * disc_complete)
    # Photo/video evidence is a modest, honest uplift: a quality-gated, timestamped image
    # backing an input is more trustworthy than a typed dropdown. Capped small on purpose —
    # evidence raises input trust, it does not replace the physical inspection.
    evidence_strength = max(0.0, min(1.0, evidence_strength))
    confidence += 6.0 * evidence_strength
    confidence = max(20.0, min(100.0, confidence))

    # --- Honest range widening ----------------------------------------------------
    # Start from the model's own quantile band, then add uncertainty from (a) unresolved
    # variant (worth real money = price_spread) and (b) undisclosed condition.
    base_low = p50 - q["p10"]
    base_high = q["p90"] - p50

    # Variant uncertainty: a fraction of the ₹ spread across plausible variants, scaled
    # by how UNsure we are. If fully confident, contributes ~0.
    variant_widen = variant_price_spread * 0.5 * (1.0 - variant_confidence)
    # Undisclosed-condition uncertainty: up to ~4% of p50 when nothing is disclosed.
    disclosure_widen = p50 * 0.04 * (1.0 - disc_complete)

    # Evidence you captured confirms inputs, so it shrinks the residual input uncertainty.
    extra = (variant_widen + disclosure_widen) * (1.0 - 0.4 * evidence_strength)
    low = p50 - (base_low + extra)
    high = p50 + (base_high + extra)

    return {
        "point": _round_k(p50),
        "range_low": _round_k(low),
        "range_high": _round_k(high),
        "confidence": int(round(confidence)),
        "confidence_band": _confidence_band(confidence),
        "width_pct": round((high - low) / p50 * 100, 1),
        "breakdown": explain(car, segment) if include_breakdown else None,
        "what_could_change": cond.negative_disclosures(disclosures),
        "uncertainty_sources": _uncertainty_sources(
            variant_confidence, variant_price_spread, disc_complete),
        "evidence_note": (
            f"Backed by your inspection photos — inputs are confirmed with images, not just "
            f"typed. This tightened your range and lifted confidence."
            if evidence_strength >= 0.3 else None),
        "disclaimer": (
            "This is a data-driven prediction, not a final offer. The final price is set "
            "after a physical inspection and a live auction. The range reflects how "
            "certain we are given what you've told us — a wider range means more to "
            "confirm at inspection."
        ),
    }


def _confidence_band(c: float) -> str:
    if c >= 80:
        return "high"
    if c >= 55:
        return "medium"
    return "low"


def _uncertainty_sources(variant_confidence, spread, disc_complete) -> list:
    out = []
    if variant_confidence < 0.85:
        out.append({
            "source": "Variant not fully confirmed",
            "detail": f"The exact variant is still uncertain, which is worth about "
                      f"₹{int(spread):,} of price difference. Confirming it will tighten "
                      f"this range — this is the single biggest driver of surprises.",
        })
    if disc_complete < 1.0:
        out.append({
            "source": "Condition not fully disclosed",
            "detail": "Some condition details (accident/repaint, CNG, service records) "
                      "aren't confirmed yet. Disclosing them now avoids a surprise at "
                      "inspection.",
        })
    if not out:
        out.append({
            "source": "Inspection & live auction",
            "detail": "Even with everything confirmed, the final price is discovered at a "
                      "live auction, which moves a few percent either way.",
        })
    return out
