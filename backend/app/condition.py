"""
condition.py — condition disclosure engine (Pillar 2).

The CEO's #2 driver of the gap: "undisclosed condition issues: repaints, aftermarket
CNG, missing service records." These are the things a seller either doesn't think to
mention or doesn't realise matter — until they're discovered at inspection and held
against them on the doorstep.

So we ask about them *up front*, with plain-language, definition-led options (the
KBB/Edmunds pattern), and we tie each answer to a transparent price effect and a
human explanation. Nothing affects the price without appearing here.

The multipliers mirror the data-generating process in model/generate_data.py, so the
seller-facing explanation is consistent with the world the pricing model learned.
"""

from __future__ import annotations
from typing import Dict, List

# Each disclosure field: the question, options (value -> human label), and per-value
# price effect (multiplier) + a short explanation for the breakdown.
DISCLOSURES: Dict[str, dict] = {
    "accident": {
        "question": "Has the car had any accident, repaint, or panel/structural repair?",
        "why_it_matters": "Repaints and panel work are the clearest signal of prior "
                          "damage and are always checked at inspection.",
        "options": {
            "none":  {"label": "No — original paint, no repairs", "mult": 1.00},
            "minor": {"label": "Minor — a repaint or a small dent/scratch repair",
                      "mult": 0.93},
            "major": {"label": "Major — structural/panel replacement after an accident",
                      "mult": 0.80},
        },
    },
    "aftermarket_cng": {
        "question": "Is there an aftermarket (externally fitted) CNG kit?",
        "why_it_matters": "Aftermarket CNG (not factory-fitted) affects safety, warranty "
                          "and resale, and is priced differently from a factory CNG car.",
        "options": {
            "no":  {"label": "No aftermarket CNG kit", "mult": 1.00},
            "yes": {"label": "Yes, an aftermarket CNG kit is fitted", "mult": 0.90},
        },
    },
    "service_records": {
        "question": "Do you have the service records / service history?",
        "why_it_matters": "Full records let a buyer verify how the car was maintained; "
                          "missing history reduces trust and value.",
        "options": {
            "full":    {"label": "Full service history available", "mult": 1.00},
            "partial": {"label": "Some records available", "mult": 0.97},
            "none":    {"label": "No service records", "mult": 0.92},
        },
    },
    "tyres": {
        "question": "What condition are the tyres in?",
        "why_it_matters": "Worn tyres are an immediate cost the next owner has to bear.",
        "options": {
            "good": {"label": "Good tread remaining", "mult": 1.00},
            "worn": {"label": "Worn / need replacement soon", "mult": 0.98},
        },
    },
    "insurance": {
        "question": "What is the insurance status?",
        "why_it_matters": "Comprehensive cover with a high No-Claim Bonus signals careful, "
                          "claim-free ownership.",
        "options": {
            "comprehensive_highncb": {"label": "Comprehensive, high No-Claim Bonus",
                                      "mult": 1.02},
            "comprehensive": {"label": "Comprehensive cover", "mult": 1.00},
            "thirdparty_or_expired": {"label": "Third-party only / expired", "mult": 0.97},
        },
    },
}

# The disclosures that materially move price and are commonly hidden — used to compute
# disclosure completeness for the confidence score.
KEY_FIELDS: List[str] = ["accident", "aftermarket_cng", "service_records"]


def default_disclosures() -> Dict[str, str]:
    """Neutral/best-case defaults, used before the seller answers."""
    return {"accident": "none", "aftermarket_cng": "no", "service_records": "full",
            "tyres": "good", "insurance": "comprehensive"}


def describe(field: str, value: str) -> dict:
    """Return {label, mult, why_it_matters} for a disclosure answer."""
    spec = DISCLOSURES[field]
    opt = spec["options"][value]
    return {"label": opt["label"], "mult": opt["mult"],
            "why_it_matters": spec["why_it_matters"]}


def completeness(disclosures: Dict[str, str]) -> float:
    """Fraction of KEY disclosure fields the seller has actually answered (0..1)."""
    answered = sum(1 for f in KEY_FIELDS if disclosures.get(f) not in (None, "unknown"))
    return answered / len(KEY_FIELDS)


def negative_disclosures(disclosures: Dict[str, str]) -> List[dict]:
    """Items that pull price DOWN — surfaced in 'what could change at inspection'."""
    out = []
    for field, value in disclosures.items():
        if field not in DISCLOSURES or value in (None, "unknown"):
            continue
        opt = DISCLOSURES[field]["options"].get(value)
        if opt and opt["mult"] < 1.0:
            out.append({
                "field": field,
                "label": opt["label"],
                "impact_pct": round((opt["mult"] - 1.0) * 100, 1),
                "why_it_matters": DISCLOSURES[field]["why_it_matters"],
            })
    return sorted(out, key=lambda d: d["impact_pct"])
