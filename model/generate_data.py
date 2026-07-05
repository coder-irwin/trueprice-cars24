"""
generate_data.py — synthetic Indian used-car dataset generator.

We do NOT have Cars24's proprietary transaction data, and using it would violate the
free-resources-only constraint. Instead we generate a transparent, reproducible dataset
from an explicit *data-generating process* (DGP) that encodes realistic pricing physics.
The ML model in train.py then has to *recover* this process — which makes our accuracy
and calibration metrics meaningful.

The DGP for a car's realized auction FINAL price:

    final = ref_price_new                     # variant MSRP anchor (catalog)
            × depreciation(age)               # value lost to age
            × km_factor(km, age)              # usage vs expected
            × owner_factor(owners)            # ownership chain
            × condition_mult(...)             # accident/repaint, CNG, service, tyres, ins
            × city_factor(city_tier)          # demand geography
            × color_factor(color)
            × auction_noise                   # live-auction discovery randomness

Everything here is approximate, public-knowledge, and documented in docs/00-research.md
§3. Run:  .venv/bin/python model/generate_data.py --rows 24000
"""

from __future__ import annotations
import argparse
import csv
import os
import random

from catalog import CATALOG, reference_price
from features import build_feature_row, FEATURE_COLUMNS, TARGET

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")

CITY_TIERS = {"metro": 1.00, "tier2": 0.975, "tier3": 0.95}
COLOR_FACTOR = {"neutral": 1.00, "standard": 0.99, "niche": 0.965}
OWNER_FACTOR = {1: 1.00, 2: 0.93, 3: 0.86, 4: 0.80}
ACCIDENT_MULT = {"none": 1.00, "minor": 0.93, "major": 0.80}
SERVICE_MULT = {"full": 1.00, "partial": 0.97, "none": 0.92}
TYRE_MULT = {"good": 1.00, "worn": 0.98}
INSURANCE_MULT = {"comprehensive_highncb": 1.02, "comprehensive": 1.00,
                  "thirdparty_or_expired": 0.97}


def depreciation(age: int) -> float:
    """Indian retail depreciation: ~15% year one, ~12%/yr compounding after, floored."""
    if age <= 0:
        return 1.0
    retain = 0.85 * (0.88 ** (age - 1))
    return max(retain, 0.22)


def km_factor(km: int, age: int) -> float:
    """Usage penalty relative to ~12,000 km/yr expectation, plus high-odometer cliffs."""
    expected = max(age * 12000, 6000)
    rel = (km - expected) / expected
    f = 1.0 - 0.10 * rel
    f = max(0.75, min(1.08, f))
    if km > 100000:
        f -= 0.05
    if km > 130000:
        f -= 0.03
    return max(0.68, f)


def condition_mult(accident, aftermarket_cng, service_records, tyres, insurance) -> float:
    m = ACCIDENT_MULT[accident] * SERVICE_MULT[service_records] * TYRE_MULT[tyres] \
        * INSURANCE_MULT[insurance]
    if aftermarket_cng == "yes":
        m *= 0.90  # aftermarket CNG: safety + resale + warranty penalty
    return m


def sample_car(rng: random.Random) -> dict:
    model = rng.choice(CATALOG)
    variant = rng.choice(model.variants)
    fuel = rng.choice(model.fuels)
    transmission = rng.choice(model.transmissions)
    age = rng.randint(1, 9)

    # km correlated with age but noisy.
    expected = age * 12000
    km = int(max(3000, rng.gauss(expected, expected * 0.45)))

    # ownership skews toward fewer owners.
    owners = rng.choices([1, 2, 3, 4], weights=[0.55, 0.30, 0.11, 0.04])[0]

    accident = rng.choices(["none", "minor", "major"], weights=[0.72, 0.22, 0.06])[0]
    # aftermarket CNG only realistic on petrol cars.
    aftermarket_cng = "no"
    if fuel == "petrol" and rng.random() < 0.10:
        aftermarket_cng = "yes"
    service_records = rng.choices(["full", "partial", "none"],
                                  weights=[0.5, 0.33, 0.17])[0]
    tyres = rng.choices(["good", "worn"], weights=[0.7, 0.3])[0]
    insurance = rng.choices(
        ["comprehensive_highncb", "comprehensive", "thirdparty_or_expired"],
        weights=[0.3, 0.5, 0.2])[0]
    city_tier = rng.choices(["metro", "tier2", "tier3"], weights=[0.5, 0.33, 0.17])[0]
    color = rng.choices(["neutral", "standard", "niche"], weights=[0.55, 0.35, 0.10])[0]

    return {
        "make": model.make, "model": model.model, "segment": model.segment,
        "variant": variant.name, "fuel": fuel, "transmission": transmission,
        "age": age, "km": km, "owners": owners, "accident": accident,
        "aftermarket_cng": aftermarket_cng, "service_records": service_records,
        "tyres": tyres, "insurance": insurance, "city_tier": city_tier, "color": color,
    }


def realized_price(car: dict, rng: random.Random) -> int:
    ref = reference_price(car["make"], car["model"], car["variant"],
                          car["fuel"], car["transmission"])
    value = (ref
             * depreciation(car["age"])
             * km_factor(car["km"], car["age"])
             * OWNER_FACTOR[car["owners"]]
             * condition_mult(car["accident"], car["aftermarket_cng"],
                              car["service_records"], car["tyres"], car["insurance"])
             * CITY_TIERS[car["city_tier"]]
             * COLOR_FACTOR[car["color"]])
    # Live-auction discovery noise (multiplicative, ~5%).
    value *= rng.lognormvariate(0, 0.05)
    return int(round(value, -3))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=24000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=os.path.join(DATA_DIR, "used_cars.csv"))
    args = ap.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)
    rng = random.Random(args.seed)

    # Full descriptive columns (for the resolver/backtest) + model feature columns.
    descriptive = ["make", "model", "variant"]
    fieldnames = descriptive + FEATURE_COLUMNS + [TARGET]

    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for _ in range(args.rows):
            car = sample_car(rng)
            final = realized_price(car, rng)
            feat = build_feature_row(car, car["segment"])
            row = {"make": car["make"], "model": car["model"], "variant": car["variant"]}
            row.update(feat)
            row[TARGET] = final
            w.writerow(row)

    print(f"Wrote {args.rows} rows -> {os.path.relpath(args.out, HERE)}")


if __name__ == "__main__":
    main()
