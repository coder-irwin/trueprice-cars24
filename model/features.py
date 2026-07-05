"""
features.py — the shared feature schema for TruePrice.

Both the trainer (model/train.py) and the live pricing service
(backend/app/pricing.py) import this so the columns can never drift apart. If you add a
pricing feature, add it here once and both sides pick it up.

The design keeps ONE strong numeric anchor — `ref_price_new`, the variant's reference
ex-showroom price from the catalog — and lets the model learn depreciation and all the
adjustments from the remaining features. This mirrors how a real pricing desk keys off
the variant MSRP and then adjusts.
"""

from __future__ import annotations
from typing import Dict, List

from catalog import reference_price

# Numeric model inputs.
NUMERIC_FEATURES: List[str] = ["ref_price_new", "age", "km", "owners"]

# Categorical model inputs (one-hot encoded in the pipeline).
CATEGORICAL_FEATURES: List[str] = [
    "fuel", "transmission", "segment",
    "accident", "aftermarket_cng", "service_records", "tyres",
    "insurance", "city_tier", "color",
]

FEATURE_COLUMNS: List[str] = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET: str = "final_price"

# Allowed categorical values — also used to validate API input.
CATEGORY_VALUES: Dict[str, List] = {
    "fuel": ["petrol", "diesel", "cng", "hybrid"],
    "transmission": ["manual", "amt", "cvt", "dct", "torque_converter"],
    "segment": ["hatchback", "sedan", "compact_suv", "suv", "muv"],
    "accident": ["none", "minor", "major"],
    "aftermarket_cng": ["no", "yes"],
    "service_records": ["full", "partial", "none"],
    "tyres": ["good", "worn"],
    "insurance": ["comprehensive_highncb", "comprehensive", "thirdparty_or_expired"],
    "city_tier": ["metro", "tier2", "tier3"],
    "color": ["neutral", "standard", "niche"],
}


def build_feature_row(car: dict, segment: str) -> Dict[str, object]:
    """Assemble the model-input row from a raw car dict + resolved segment.

    `car` must contain: make, model, variant, fuel, transmission, age, km, owners,
    accident, aftermarket_cng, service_records, tyres, insurance, city_tier, color.
    """
    ref = reference_price(car["make"], car["model"], car["variant"],
                          car.get("fuel", "petrol"),
                          car.get("transmission", "manual"))
    if ref is None:
        raise ValueError(f"Unknown variant: {car.get('make')} {car.get('model')} "
                         f"{car.get('variant')}")
    return {
        "ref_price_new": ref,
        "age": car["age"],
        "km": car["km"],
        "owners": car["owners"],
        "fuel": car.get("fuel", "petrol"),
        "transmission": car.get("transmission", "manual"),
        "segment": segment,
        "accident": car.get("accident", "none"),
        "aftermarket_cng": car.get("aftermarket_cng", "no"),
        "service_records": car.get("service_records", "full"),
        "tyres": car.get("tyres", "good"),
        "insurance": car.get("insurance", "comprehensive"),
        "city_tier": car.get("city_tier", "metro"),
        "color": car.get("color", "neutral"),
    }
