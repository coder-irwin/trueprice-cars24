"""
catalog.py — the single source of market truth for TruePrice.

This module encodes a compact but realistic catalog of popular Indian cars, their
variant ladders, the *distinguishing features* that separate adjacent variants, and
reference new-car prices. It is deliberately the one place market knowledge lives, so
that THREE things stay perfectly consistent:

  1. the synthetic data generator (model/generate_data.py),
  2. the Variant Resolver (backend/app/variant_resolver.py), and
  3. the pricing explanations shown to the seller.

Prices are in Indian Rupees (INR), expressed as a reference ex-showroom price when the
variant was new. Depreciation/condition/market effects are applied downstream.

Everything here is public-knowledge, free-resource-only, and approximate. It is NOT
scraped from Cars24 or any proprietary source. See docs/00-research.md §5.

Feature vocabulary (canonical across all models so the resolver can ask uniform
questions). Values are ordinal-ish where noted:

    sunroof       : "none" | "single" | "panoramic"
    wheels        : "steel" | "alloy"
    infotainment  : "none" | "basic" | "touchscreen"
    airbags       : 2 | 6
    climate       : "manual" | "auto"
    headlamps     : "halogen" | "projector" | "led"
    rear_ac_vents : False | True
    cruise        : False | True
    rear_camera   : False | True
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# The set of features the Variant Resolver may ask about, with the human question and
# the possible answers. Order matters only for display; the resolver picks the most
# *informative* question dynamically.
FEATURE_QUESTIONS: Dict[str, dict] = {
    "sunroof": {
        "question": "Does your car have a sunroof?",
        "options": {"none": "No sunroof", "single": "Yes, a single sunroof",
                    "panoramic": "Yes, a large panoramic sunroof"},
    },
    "wheels": {
        "question": "What kind of wheels does it have?",
        "options": {"steel": "Steel wheels with plastic covers",
                    "alloy": "Alloy wheels"},
    },
    "infotainment": {
        "question": "What is the music/infotainment system like?",
        "options": {"none": "Basic — no display screen",
                    "basic": "Small display, no touchscreen",
                    "touchscreen": "Touchscreen infotainment"},
    },
    "airbags": {
        "question": "How many airbags does it have?",
        "options": {2: "2 airbags (driver + front passenger)",
                    6: "6 airbags"},
    },
    "climate": {
        "question": "What is the air-conditioning control like?",
        "options": {"manual": "Manual AC (knobs/dials)",
                    "auto": "Automatic climate control (set a temperature)"},
    },
    "headlamps": {
        "question": "What kind of headlamps does it have?",
        "options": {"halogen": "Standard halogen bulbs",
                    "projector": "Projector headlamps",
                    "led": "LED headlamps"},
    },
    "rear_ac_vents": {
        "question": "Are there AC vents for the rear passengers?",
        "options": {False: "No rear AC vents", True: "Yes, rear AC vents"},
    },
    "cruise": {
        "question": "Does it have cruise control?",
        "options": {False: "No cruise control", True: "Yes, cruise control"},
    },
    "rear_camera": {
        "question": "Does it have a reverse/rear-view camera?",
        "options": {False: "No rear camera", True: "Yes, rear camera"},
    },
}


@dataclass
class Variant:
    name: str
    trim_rank: int                 # ordinal position in the ladder (0 = base)
    price_new: int                 # reference ex-showroom price when new, INR
    features: Dict[str, object]    # subset of FEATURE_QUESTIONS keys -> value


@dataclass
class Model:
    make: str
    model: str
    segment: str                   # hatchback | sedan | compact_suv | suv | muv
    launch_year: int               # nominal year the reference prices anchor to
    fuels: List[str]               # available fuel types
    transmissions: List[str]       # available transmissions
    variants: List[Variant] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.make} {self.model}"


# Transmission price adjustment (automatic variants cost more new and hold value slightly
# differently). Multiplicative on the variant base.
TRANSMISSION_ADJ = {
    "manual": 1.00,
    "amt": 1.05,
    "cvt": 1.08,
    "torque_converter": 1.09,
    "dct": 1.10,
}

# Fuel adjustment multipliers applied to the base (relative to petrol). Factory CNG is
# cheaper new; diesel commands a premium in SUVs. These are approximate market effects.
FUEL_ADJ = {
    "petrol": 1.00,
    "diesel": 1.09,
    "cng": 0.96,       # factory-fitted CNG
    "hybrid": 1.12,
}


def _v(name, rank, price, **features) -> Variant:
    return Variant(name=name, trim_rank=rank, price_new=price, features=features)


# ---------------------------------------------------------------------------------------
# THE CATALOG. Eight popular models spanning hatchback → MUV, each with a realistic
# variant ladder and the distinguishing features that separate adjacent trims. Feature
# values increase (roughly) monotonically with trim, but WHICH feature separates two
# adjacent trims varies — that is exactly what makes disambiguation informative.
# ---------------------------------------------------------------------------------------
CATALOG: List[Model] = [
    Model("Maruti Suzuki", "WagonR", "hatchback", 2020, ["petrol", "cng"],
          ["manual", "amt"], [
        _v("LXI", 0, 550000, sunroof="none", wheels="steel", infotainment="none",
           airbags=2, climate="manual", headlamps="halogen", rear_ac_vents=False,
           cruise=False, rear_camera=False),
        _v("VXI", 1, 620000, sunroof="none", wheels="steel", infotainment="basic",
           airbags=2, climate="manual", headlamps="halogen", rear_ac_vents=False,
           cruise=False, rear_camera=False),
        _v("ZXI", 2, 700000, sunroof="none", wheels="steel", infotainment="touchscreen",
           airbags=2, climate="manual", headlamps="halogen", rear_ac_vents=False,
           cruise=False, rear_camera=True),
        _v("ZXI+", 3, 750000, sunroof="none", wheels="alloy", infotainment="touchscreen",
           airbags=2, climate="auto", headlamps="halogen", rear_ac_vents=False,
           cruise=False, rear_camera=True),
    ]),
    Model("Maruti Suzuki", "Swift", "hatchback", 2020, ["petrol", "cng"],
          ["manual", "amt"], [
        _v("LXI", 0, 650000, sunroof="none", wheels="steel", infotainment="none",
           airbags=2, climate="manual", headlamps="halogen", rear_ac_vents=False,
           cruise=False, rear_camera=False),
        _v("VXI", 1, 720000, sunroof="none", wheels="steel", infotainment="basic",
           airbags=2, climate="manual", headlamps="halogen", rear_ac_vents=False,
           cruise=False, rear_camera=False),
        _v("ZXI", 2, 830000, sunroof="none", wheels="alloy", infotainment="touchscreen",
           airbags=2, climate="auto", headlamps="projector", rear_ac_vents=False,
           cruise=False, rear_camera=True),
        _v("ZXI+", 3, 920000, sunroof="none", wheels="alloy", infotainment="touchscreen",
           airbags=6, climate="auto", headlamps="led", rear_ac_vents=False,
           cruise=False, rear_camera=True),
    ]),
    Model("Maruti Suzuki", "Baleno", "hatchback", 2021, ["petrol", "cng"],
          ["manual", "amt"], [
        _v("Sigma", 0, 700000, sunroof="none", wheels="steel", infotainment="none",
           airbags=2, climate="manual", headlamps="halogen", rear_ac_vents=False,
           cruise=False, rear_camera=False),
        _v("Delta", 1, 800000, sunroof="none", wheels="steel", infotainment="touchscreen",
           airbags=2, climate="auto", headlamps="halogen", rear_ac_vents=False,
           cruise=True, rear_camera=False),
        _v("Zeta", 2, 880000, sunroof="none", wheels="alloy", infotainment="touchscreen",
           airbags=2, climate="auto", headlamps="projector", rear_ac_vents=False,
           cruise=True, rear_camera=True),
        _v("Alpha", 3, 970000, sunroof="none", wheels="alloy", infotainment="touchscreen",
           airbags=6, climate="auto", headlamps="led", rear_ac_vents=False,
           cruise=True, rear_camera=True),
    ]),
    Model("Hyundai", "i20", "hatchback", 2021, ["petrol"],
          ["manual", "cvt", "dct"], [
        _v("Magna", 0, 750000, sunroof="none", wheels="steel", infotainment="basic",
           airbags=2, climate="manual", headlamps="halogen", rear_ac_vents=False,
           cruise=False, rear_camera=False),
        _v("Sportz", 1, 880000, sunroof="none", wheels="alloy", infotainment="touchscreen",
           airbags=2, climate="manual", headlamps="projector", rear_ac_vents=True,
           cruise=False, rear_camera=True),
        _v("Asta", 2, 1000000, sunroof="single", wheels="alloy", infotainment="touchscreen",
           airbags=6, climate="auto", headlamps="projector", rear_ac_vents=True,
           cruise=True, rear_camera=True),
        _v("Asta(O)", 3, 1150000, sunroof="single", wheels="alloy",
           infotainment="touchscreen", airbags=6, climate="auto", headlamps="led",
           rear_ac_vents=True, cruise=True, rear_camera=True),
    ]),
    Model("Tata", "Nexon", "compact_suv", 2021, ["petrol", "diesel"],
          ["manual", "amt", "dct"], [
        _v("XE", 0, 800000, sunroof="none", wheels="steel", infotainment="none",
           airbags=2, climate="manual", headlamps="halogen", rear_ac_vents=False,
           cruise=False, rear_camera=False),
        _v("XM", 1, 950000, sunroof="none", wheels="steel", infotainment="touchscreen",
           airbags=2, climate="manual", headlamps="projector", rear_ac_vents=False,
           cruise=False, rear_camera=False),
        _v("XZ", 2, 1150000, sunroof="none", wheels="alloy", infotainment="touchscreen",
           airbags=2, climate="auto", headlamps="projector", rear_ac_vents=True,
           cruise=True, rear_camera=True),
        _v("XZ+", 3, 1300000, sunroof="single", wheels="alloy", infotainment="touchscreen",
           airbags=6, climate="auto", headlamps="led", rear_ac_vents=True,
           cruise=True, rear_camera=True),
    ]),
    Model("Honda", "City", "sedan", 2020, ["petrol", "diesel", "hybrid"],
          ["manual", "cvt"], [
        _v("SV", 0, 1150000, sunroof="none", wheels="steel", infotainment="basic",
           airbags=2, climate="auto", headlamps="halogen", rear_ac_vents=True,
           cruise=False, rear_camera=True),
        _v("V", 1, 1300000, sunroof="none", wheels="alloy", infotainment="touchscreen",
           airbags=2, climate="auto", headlamps="projector", rear_ac_vents=True,
           cruise=True, rear_camera=True),
        _v("VX", 2, 1450000, sunroof="single", wheels="alloy", infotainment="touchscreen",
           airbags=4, climate="auto", headlamps="led", rear_ac_vents=True,
           cruise=True, rear_camera=True),
        _v("ZX", 3, 1600000, sunroof="single", wheels="alloy", infotainment="touchscreen",
           airbags=6, climate="auto", headlamps="led", rear_ac_vents=True,
           cruise=True, rear_camera=True),
    ]),
    Model("Hyundai", "Creta", "suv", 2020, ["petrol", "diesel"],
          ["manual", "cvt", "torque_converter"], [
        _v("E", 0, 1100000, sunroof="none", wheels="steel", infotainment="basic",
           airbags=2, climate="manual", headlamps="halogen", rear_ac_vents=True,
           cruise=False, rear_camera=False),
        _v("EX", 1, 1250000, sunroof="none", wheels="alloy", infotainment="touchscreen",
           airbags=2, climate="auto", headlamps="projector", rear_ac_vents=True,
           cruise=False, rear_camera=True),
        _v("S", 2, 1450000, sunroof="none", wheels="alloy", infotainment="touchscreen",
           airbags=6, climate="auto", headlamps="projector", rear_ac_vents=True,
           cruise=True, rear_camera=True),
        _v("SX", 3, 1650000, sunroof="single", wheels="alloy", infotainment="touchscreen",
           airbags=6, climate="auto", headlamps="led", rear_ac_vents=True,
           cruise=True, rear_camera=True),
        _v("SX(O)", 4, 1850000, sunroof="panoramic", wheels="alloy",
           infotainment="touchscreen", airbags=6, climate="auto", headlamps="led",
           rear_ac_vents=True, cruise=True, rear_camera=True),
    ]),
    Model("Kia", "Seltos", "suv", 2020, ["petrol", "diesel"],
          ["manual", "cvt", "dct", "torque_converter"], [
        _v("HTE", 0, 1100000, sunroof="none", wheels="steel", infotainment="basic",
           airbags=2, climate="manual", headlamps="halogen", rear_ac_vents=True,
           cruise=False, rear_camera=False),
        _v("HTK", 1, 1250000, sunroof="none", wheels="alloy", infotainment="touchscreen",
           airbags=2, climate="manual", headlamps="projector", rear_ac_vents=True,
           cruise=False, rear_camera=True),
        _v("HTX", 2, 1550000, sunroof="single", wheels="alloy", infotainment="touchscreen",
           airbags=6, climate="auto", headlamps="projector", rear_ac_vents=True,
           cruise=True, rear_camera=True),
        _v("GTX+", 3, 1850000, sunroof="panoramic", wheels="alloy",
           infotainment="touchscreen", airbags=6, climate="auto", headlamps="led",
           rear_ac_vents=True, cruise=True, rear_camera=True),
    ]),
]


# ---- Lookup helpers -------------------------------------------------------------------

_BY_KEY: Dict[str, Model] = {m.key: m for m in CATALOG}


def get_model(make: str, model: str) -> Optional[Model]:
    return _BY_KEY.get(f"{make} {model}")


def all_model_keys() -> List[str]:
    return [m.key for m in CATALOG]


def get_variant(make: str, model: str, variant_name: str) -> Optional[Variant]:
    m = get_model(make, model)
    if not m:
        return None
    for v in m.variants:
        if v.name.lower() == variant_name.lower():
            return v
    return None


def reference_price(make: str, model: str, variant_name: str,
                    fuel: str = "petrol", transmission: str = "manual") -> Optional[int]:
    """New-car reference price for a variant with a given fuel/transmission."""
    v = get_variant(make, model, variant_name)
    if not v:
        return None
    price = v.price_new * FUEL_ADJ.get(fuel, 1.0) * TRANSMISSION_ADJ.get(transmission, 1.0)
    return int(round(price, -3))  # round to nearest 1000


if __name__ == "__main__":
    # Quick sanity dump.
    total_variants = sum(len(m.variants) for m in CATALOG)
    print(f"Catalog: {len(CATALOG)} models, {total_variants} variants")
    for m in CATALOG:
        print(f"  {m.key:28s} [{m.segment}]  "
              f"{', '.join(v.name for v in m.variants)}")
