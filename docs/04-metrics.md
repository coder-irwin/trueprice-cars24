# 04 · Metrics — what we measure & how

Ties the success metrics in `docs/01-product.md` §4 to the code that actually measures them.

## North-star: below-floor rate
The share of sellers whose **final price lands below the quoted floor** — the CEO's ~40% pain.
This is the metric TruePrice exists to move.

### Offline proof (the backtest)
`tests/backtest.py` simulates two worlds over the same cars and realized auction prices; the
only difference is the front door (typed variant vs resolved variant + honest widening).

**Actual result (1,500 simulated sellers, seed 2024):**

| | Old front door | TruePrice |
|---|---|---|
| **Below-floor rate** (the pain) | **34.9%** | **15.2%** |
| Avg range width | 12.9% | 13.1% |
| Avg (final − floor) | ₹19,193 | ₹39,089 |

> **Below-floor rate cut by 56% (34.9% → 15.2%).**

**Why this result is trustworthy, not a trick:**
- The range width barely moved (12.9% → 13.1%). We did **not** win by ballooning ranges to
  swallow every outcome — the improvement comes from **resolving the true variant** and removing
  the aspiration-bias overshoot. Honest widening only mops up the residual uncertainty.
- Reproduce: `.venv/bin/python tests/backtest.py` (deterministic seed).

## Model quality (point + calibration)
From `model/train.py` on a held-out 20% test set:

| Metric | Value | Meaning |
|---|---|---|
| Point (P50) MAPE | **4.3%** | mid-point accuracy on the DGP |
| P10–P90 coverage | **74.2%** | measured; nominal 80% (calibration = future work) |
| Avg range width | **12.9%** of point | tight *when inputs are known-true* |

## Driver / supporting metrics (production)
- **Variant-correction rate** — % sessions where the Resolver changed the seller's first guess.
- **Confidence↔width calibration** — do low-confidence sessions get wider ranges that *still*
  cover reality? (The backtest is the offline version of this.)
- **Completion rate** through the wizard — honesty must not tank conversion.
- **Complaint rate / CSAT** on "estimate vs final."

## Guardrail metrics (don't win the wrong way)
- **Under-quote drift** — don't lower every estimate to be "safe." Watch that the ~25% who beat
  the upper end stays healthy (the backtest's "avg final − floor" rising is expected and fine;
  a *collapse* of the upper tail would be the warning sign).
- **Flow drop-off** per wizard step.

## How to run every metric in this repo
```bash
.venv/bin/python model/train.py       # prints MAPE, coverage, width
.venv/bin/python tests/backtest.py    # prints below-floor rate: old vs TruePrice
.venv/bin/python tests/test_core.py   # asserts the honesty invariants hold
```
