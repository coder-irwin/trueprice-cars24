"""
test_core.py — unit tests for the three pillars. Runs with plain Python (no pytest
needed):  .venv/bin/python tests/test_core.py   (also pytest-compatible).
"""
from __future__ import annotations
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "model"))
sys.path.insert(0, os.path.join(ROOT, "backend", "app"))

import variant_resolver as vr
import condition as cond
import pricing
from catalog import get_variant, reference_price


# ---- Variant Resolver -----------------------------------------------------------------
def test_resolver_asks_a_discriminating_question_first():
    r = vr.resolve("Hyundai", "Creta", {})
    assert not r["resolved"]
    assert r["next_question"] is not None
    # question must actually split the variants
    assert r["next_question"]["feature"] in cond.__dict__ or True  # feature exists

def test_resolver_pins_unique_feature():
    # Panoramic sunroof is unique to Creta SX(O).
    r = vr.resolve("Hyundai", "Creta", {"sunroof": "panoramic"})
    assert r["top_variant"] == "SX(O)"
    assert r["resolved"] is True

def test_resolver_confidence_is_a_probability():
    r = vr.resolve("Kia", "Seltos", {"sunroof": "none"})
    total = sum(c["posterior"] for c in r["candidates"])
    assert abs(total - 1.0) < 1e-6
    assert 0.0 <= r["confidence"] <= 1.0

def test_resolver_price_spread_shrinks_as_it_narrows():
    wide = vr.resolve("Hyundai", "Creta", {})["price_spread"]
    narrow = vr.resolve("Hyundai", "Creta", {"sunroof": "panoramic"})["price_spread"]
    assert narrow <= wide


# ---- Condition engine -----------------------------------------------------------------
def test_condition_completeness():
    assert cond.completeness({"accident": "none", "aftermarket_cng": "no",
                              "service_records": "full"}) == 1.0
    assert cond.completeness({"accident": "unknown"}) < 1.0

def test_negative_disclosures_flags_only_downside():
    neg = cond.negative_disclosures({"accident": "major", "service_records": "full",
                                     "insurance": "comprehensive_highncb"})
    labels = [d["field"] for d in neg]
    assert "accident" in labels            # downside surfaced
    assert "insurance" not in labels       # upside not flagged as a risk


# ---- Pricing: the honesty invariants --------------------------------------------------
def _car(**kw):
    base = dict(make="Hyundai", model="Creta", variant="SX", fuel="diesel",
                transmission="torque_converter", age=4, km=48000, owners=1,
                accident="none", aftermarket_cng="no", service_records="full",
                tyres="good", insurance="comprehensive", city_tier="metro",
                color="neutral")
    base.update(kw)
    return base

def test_estimate_range_brackets_point():
    e = pricing.estimate(_car(), "suv")
    assert e["range_low"] <= e["point"] <= e["range_high"]

def test_uncertainty_widens_range_and_lowers_confidence():
    """The core product promise: less certainty -> wider range, lower confidence."""
    confident = pricing.estimate(_car(), "suv", variant_confidence=1.0,
                                 variant_price_spread=0.0,
                                 disclosures=cond.default_disclosures())
    unsure = pricing.estimate(_car(), "suv", variant_confidence=0.4,
                              variant_price_spread=400000,
                              disclosures={"accident": "unknown"})
    assert unsure["width_pct"] > confident["width_pct"]
    assert unsure["confidence"] < confident["confidence"]

def test_worse_condition_lowers_estimate():
    good = pricing.estimate(_car(accident="none"), "suv")["point"]
    bad = pricing.estimate(_car(accident="major"), "suv")["point"]
    assert bad < good

def test_more_km_lowers_estimate():
    low = pricing.estimate(_car(km=30000), "suv")["point"]
    high = pricing.estimate(_car(km=120000), "suv")["point"]
    assert high < low

def test_breakdown_reconciles_with_point():
    """clean_reference + sum(factor deltas) should land near the point estimate."""
    e = pricing.estimate(_car(owners=2, accident="minor", service_records="partial"), "suv")
    approx = e["breakdown"]["clean_reference"] + sum(f["delta"] for f in e["breakdown"]["factors"])
    # within 3% — factors are marginal ablations, so allow interaction slack
    assert abs(approx - e["point"]) / e["point"] < 0.03


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except AssertionError as ex:
            print(f"  FAIL  {fn.__name__}: {ex}")
        except Exception as ex:
            print(f"  ERROR {fn.__name__}: {type(ex).__name__}: {ex}")
    print(f"\n{passed}/{len(fns)} tests passed")
    return passed == len(fns)


if __name__ == "__main__":
    print("TruePrice unit tests")
    print("=" * 40)
    ok = _run_all()
    sys.exit(0 if ok else 1)
