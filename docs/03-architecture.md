# 03 · Architecture

How TruePrice is built, and why each piece exists. Builds on `docs/01-product.md`.

## System overview

```
                       ┌───────────────────────── Browser (frontend/) ─────────────────────────┐
                       │  Seller wizard (vanilla HTML/CSS/JS, no build step)                    │
                       │   Step 1 Basics → Step 2 Variant Resolver → Step 3 Condition → Result  │
                       └───────────────┬───────────────────────────────────────────────────────┘
                                       │  fetch() JSON
                       ┌───────────────▼──────────────── FastAPI (backend/app/main.py) ─────────┐
                       │  /api/catalog   /api/variant/resolve   /api/estimate   /api/health     │
                       └───────┬─────────────────┬────────────────────────┬─────────────────────┘
                               │                 │                        │
                 ┌─────────────▼──┐   ┌──────────▼─────────┐   ┌──────────▼──────────┐
                 │ variant_resolver│   │   condition.py     │   │     pricing.py      │
                 │  (Pillar 1)     │   │   (Pillar 2)       │   │     (Pillar 3)      │
                 │ Bayesian +      │   │ disclosure specs + │   │ quantile predict +  │
                 │ info-gain Qs    │   │ transparent effects│   │ honest widening +   │
                 └───────┬─────────┘   └─────────┬──────────┘   │ model-based explain │
                         │                       │              └──────────┬──────────┘
                         └───────────┬───────────┘                         │
                            ┌────────▼─────────┐                ┌──────────▼──────────┐
                            │  catalog.py      │                │ pricing_model.joblib│
                            │ (market truth:   │                │ 3× HistGBR quantile │
                            │  models/variants/│                │ (trained offline)   │
                            │  features/prices)│                └──────────┬──────────┘
                            └────────┬─────────┘                           │
                                     │        features.py (shared schema)  │
                                     └──────────────┬──────────────────────┘
                                        ┌───────────▼───────────┐
                                        │  model/ offline build │
                                        │ generate_data → train │
                                        └───────────────────────┘
```

## Why this shape

- **One source of market truth (`catalog.py`).** The variant ladders, distinguishing features,
  and reference prices live in exactly one place, imported by the resolver, the data generator,
  and the pricing explanations. This is what stops the UI, the model, and the explanations from
  ever telling the seller three different stories.
- **One shared feature schema (`features.py`).** The trainer and the live server import the same
  column definitions, so training/serving skew is structurally impossible.
- **Pure-function pillars.** `variant_resolver`, `condition`, and `pricing` are framework-free
  and independently testable (`tests/test_core.py`). FastAPI is a thin transport layer.
- **Offline model, online serve.** `generate_data.py` → `train.py` produce `pricing_model.joblib`
  once; the server just loads and predicts. Fast, reproducible, cache-friendly.
- **No build step on the frontend.** Vanilla JS keeps the free/zero-dependency promise and makes
  the whole product runnable with one Python process.

## The three pillars in detail

### Pillar 1 — Variant Resolver (`variant_resolver.py`)
A small Bayesian disambiguator. Prior = uniform over the model's variants. Each visible-feature
answer applies a **soft** likelihood (0.96 match / 0.04 mismatch — soft because sellers
misremember), producing a posterior over variants. The next question is chosen by **maximum
information gain**: we compute the expected posterior entropy after each candidate question and
ask the one that shrinks uncertainty most — so we reach certainty in the fewest questions.
It also returns `price_spread`: the ₹ gap across still-plausible variants, i.e. *how much money
the remaining uncertainty is worth*. That number feeds Pillar 3's honest widening.

### Pillar 2 — Condition Disclosure (`condition.py`)
A declarative spec of the high-impact, commonly-hidden condition items (accident/repaint,
aftermarket CNG, service records, tyres, insurance), each with a plain-language, definition-led
question and a transparent price multiplier that **mirrors the data-generating process** — so
the seller's explanation matches the world the model learned. Also computes disclosure
`completeness` (feeds confidence) and `negative_disclosures` (feeds "what could change").

### Pillar 3 — Honest Estimate (`pricing.py`)
Loads three quantile models and predicts P10/P50/P90. Then:
- **Confidence** = `0.6 × variant_confidence + 0.4 × disclosure_completeness`, in [20, 100].
- **Honest widening**: the model's own band assumes inputs are known-true; we add width from
  unresolved variant (`price_spread × 0.5 × (1 − variant_confidence)`) and undisclosed condition
  (`≤ 4% of P50`). Less certainty → wider range → lower confidence. This is the core promise.
- **Explanation** by *ablation on the real model*: hold the car against a clean reference of the
  same variant and attribute each factor's ₹ effect. Honest, model-derived, additive-in-story.

## Data flow for one estimate
1. UI collects basics → calls `/api/variant/resolve` repeatedly until `resolved` (or manual pick).
2. UI collects condition disclosures.
3. UI calls `/api/estimate` with the car + `variant_confidence` + `variant_price_spread`.
4. `pricing.estimate` returns point, range, confidence, breakdown, what-could-change, sources.

## Tech stack (all free / open-source)
Python 3, scikit-learn, numpy, pandas, joblib, FastAPI, Uvicorn; vanilla HTML/CSS/JS.
No paid services, no external data feeds, no CDN dependency.

## Extension seams (designed-for, not built in MVP)
- **Photo CV** for variant/damage detection → drop-in evidence source for the resolver.
- **RTO / registration decode** → strong prior for the resolver before any question.
- **Real transaction data** → swap the synthetic DGP; `features.py` schema stays.
- **Conformal calibration** → tighten P10–P90 coverage to nominal (see model card).
