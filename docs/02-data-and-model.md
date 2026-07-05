# 02 · Data & Model

Short companion to `model/MODEL_CARD.md` (the formal card) — this is the "how it hangs
together" narrative.

## Why synthetic data
Real Cars24 transaction data is proprietary and not a free resource. So we generate a
**transparent, reproducible** dataset from an explicit data-generating process (DGP). The point
of the MVP is to demonstrate the *product mechanics and honesty properties*, and a documented
DGP makes accuracy/calibration metrics meaningful (the model has to recover a known process).

## The data-generating process (`model/generate_data.py`)
Realized auction **final price** =
```
ref_price_new(variant, fuel, transmission)      # catalog MSRP anchor
  × depreciation(age)                            # ~15% yr1, ~12%/yr after, floored
  × km_factor(km, age)                           # usage vs ~12k km/yr + high-odo cliffs
  × owner_factor(owners)                         # 1st owner premium, step discounts
  × condition_mult(accident, CNG, service, tyres, insurance)
  × city_factor(city_tier) × color_factor(color)
  × auction_noise (lognormal ~5%)                # live-auction discovery
```
Each factor is grounded in public Indian-market knowledge (`docs/00-research.md` §3). Defaults:
24,000 rows, seed 42.

## The model (`model/train.py`)
Three `HistGradientBoostingRegressor` models with **quantile loss** at α = 0.10 / 0.50 / 0.90.
- **P50** = point estimate; **P10–P90** = honest range (data-driven, not a cosmetic ± band).
- One numeric anchor (`ref_price_new`) + vehicle features; categoricals one-hot encoded.
- Shared schema in `model/features.py` → no train/serve skew.
- Quantile crossing is guarded at predict time (sort P10 ≤ P50 ≤ P90).

## The key nuance (where honesty comes from)
The model's ~13% band assumes the variant and condition are **known-true**. In real life they
often aren't — that's the CEO's whole point. So at serve time (`backend/app/pricing.py`) we
**widen** the range and lower confidence when the Variant Resolver is unsure or condition is
undisclosed. The model gives the data-driven core; the product layer adds honesty about *input*
uncertainty. See `docs/03-architecture.md` (Pillar 3).

## Reproduce
```bash
.venv/bin/python model/generate_data.py --rows 24000
.venv/bin/python model/train.py            # prints held-out metrics, saves .joblib
```
