# 05 · API Reference

Base URL (local): `http://127.0.0.1:8000`. All bodies are JSON. Interactive docs (Swagger) are
auto-served by FastAPI at `/docs`.

---

## `GET /api/health`
Liveness + the trained model's held-out metrics.
```json
{ "status": "ok",
  "model_metrics": { "point_mape": 4.30, "coverage_p10_p90": 74.19,
                     "avg_width_pct": 12.87, "test_rows": 4800 } }
```

## `GET /api/catalog`
Everything the UI needs to render dropdowns and the condition step.
```json
{ "models": [ { "make": "Kia", "model": "Seltos", "segment": "suv",
                "fuels": ["petrol","diesel"], "transmissions": ["manual","cvt","dct","torque_converter"],
                "variants": [ { "name": "HTE", "trim_rank": 0, "price_new": 1100000 }, … ] } ],
  "category_values": { "accident": ["none","minor","major"], … },
  "disclosures": [ { "field": "accident", "question": "…", "why_it_matters": "…",
                     "options": [ { "value": "none", "label": "No — original paint…" }, … ] } ] }
```

## `POST /api/variant/resolve`  — Pillar 1
Given the answers gathered so far, return the posterior over variants and the next best
question. Call repeatedly until `resolved` is true (or `next_question` is null).

**Request**
```json
{ "make": "Hyundai", "model": "Creta", "fuel": "diesel", "transmission": "torque_converter",
  "answers": { "sunroof": "single" } }
```
**Response**
```json
{ "make": "Hyundai", "model": "Creta",
  "candidates": [ { "variant": "SX", "posterior": 0.71, "price_new": 1799000, "trim_rank": 3 }, … ],
  "top_variant": "SX", "confidence": 0.71, "resolved": false,
  "next_question": { "feature": "headlamps", "question": "What kind of headlamps…",
                     "options": [ { "value": "halogen", "label": "Standard halogen bulbs" }, … ] },
  "price_spread": 200000, "answers": { "sunroof": "single" } }
```
- `confidence` — posterior of the top variant (0–1).
- `price_spread` — ₹ spread across still-plausible variants; how much money the remaining
  uncertainty is worth. Pass this to `/api/estimate` as `variant_price_spread`.
- `resolved` — true once `confidence ≥ 0.85`.

## `POST /api/estimate`  — Pillars 2 & 3
Produce the honest, explainable estimate for a fully-specified car.

**Request**
```json
{ "make":"Hyundai","model":"Creta","variant":"SX","fuel":"diesel",
  "transmission":"torque_converter","age":4,"km":60000,"owners":2,
  "accident":"minor","aftermarket_cng":"no","service_records":"partial",
  "tyres":"good","insurance":"comprehensive","city_tier":"metro","color":"neutral",
  "variant_confidence":1.0, "variant_price_spread":0 }
```
**Response** (abridged)
```json
{ "point": 919000, "range_low": 866000, "range_high": 927000,
  "confidence": 100, "confidence_band": "high", "width_pct": 6.6,
  "breakdown": { "clean_reference": 1123000,
    "factors": [ { "label": "Ownership", "delta": -90000, "note": "2 owners" }, … ] },
  "what_could_change": [ { "field":"accident","label":"Minor — a repaint…",
                           "impact_pct":-7.0,"why_it_matters":"…" } ],
  "uncertainty_sources": [ { "source":"…","detail":"…" } ],
  "disclaimer": "This is a data-driven prediction, not a final offer. …",
  "input_echo": { "make":"Hyundai","model":"Creta","variant":"SX" } }
```

### Field notes
| Field | Meaning |
|---|---|
| `point` | P50 — the mid-point estimate |
| `range_low` / `range_high` | honest range (model quantiles widened by input uncertainty) |
| `confidence` | 0–100; `0.6 × variant_confidence + 0.4 × disclosure_completeness` |
| `confidence_band` | `high` (≥80) / `medium` (≥55) / `low` |
| `width_pct` | range width as % of point — grows as certainty drops |
| `breakdown` | model-ablation attribution of each factor's ₹ effect |
| `what_could_change` | disclosed items that pull price down, for inspection expectation |

## Errors
`400` with `{ "detail": "…" }` for unknown model/variant or invalid input (validated by
Pydantic: `age` 0–25, `km` 0–500000, `owners` 1–6, etc.).

---

## Smart Assist (optional Gemini layer) — see `docs/08-vision.md` §5b
Off by default; only meaningful if `GEMINI_API_KEY` is set in `.env`.

### `GET /api/smart-assist/status`
Cheap, instant — does **not** call Gemini. Tells the UI whether to show the opt-in toggle.
```json
{ "enabled": true, "model": "gemini-2.5-flash" }
```

### `GET /api/smart-assist/health`
Makes **one real call** to Gemini so the caller sees the true reachability state, rather than
discovering a bad key only when an analysis silently falls back. Called on demand (e.g. when the
user flips the toggle on), not on every page load.
```json
{ "state": "ready", "model": "gemini-2.5-flash" }
```
`state` is one of:
| State | Meaning |
|---|---|
| `disabled` | No `GEMINI_API_KEY` configured |
| `ready` | Key is valid and the API responded normally |
| `quota_exhausted` | Key is valid but out of prepay credits / rate-limited (HTTP 429) |
| `invalid_key` | Google rejected the key (HTTP 400/403) |
| `error` | Network issue or a transient upstream error (e.g. HTTP 503) — usually worth retrying |

### `POST /api/smart-assist/analyze`
Suggests a value for one captured inspection-point photo. Always safe to call — degrades to
`available: false` if Smart Assist isn't configured or reachable.
```json
// request
{ "point_id": "roof", "image": "<base64 jpeg, no data: prefix>",
  "make": "Hyundai", "model": "Creta" }
// response (suggestion made)
{ "available": true, "detected": "single", "kind": "enum", "label": "Yes, a single sunroof",
  "confidence": 0.82, "reason": "…", "note": "AI suggestion — please confirm." }
// response (unsure / not configured / unreachable)
{ "available": true, "detected": null, "confidence": 0.0,
  "note": "AI wasn't sure — please pick what you see." }
```
The seller/inspector always makes the final choice — this only pre-fills a suggestion.
