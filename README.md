# TruePrice

**A variant-aware, condition-honest, confidence-scored used-car estimate engine — built to
close the estimate-to-final-price gap that Cars24 sellers complain about most.**

> *"The most persistent complaint we hear from sellers on Cars24 is about the gap between the
> online estimate and the final price."* — Vikram Chopra, Founder & CEO, Cars24 (the LinkedIn
> post in [`image.png`](image.png) that started this project).

TruePrice is a working MVP + full product documentation, built end-to-end from that problem
statement, on a **100% free and open-source stack**.

---

## The problem in one picture

```
Seller types details ──▶  ₹8–9.5L estimate  ──▶  inspection + auction  ──▶  ₹7L final
                              (a prediction)                                   (reality)
                                                          ▲
                        ~40% of sellers land BELOW the quoted floor → broken trust
      Drivers (per CEO): (1) VARIANT MISMATCH — 4/10 cars, 15–20% swing
                         (2) UNDISCLOSED CONDITION — repaints, aftermarket CNG, no records
```

**Our thesis:** the gap is an *input-accuracy and expectation* problem, not mainly a
pricing-accuracy problem. So we fix the inputs and the expectation:

| Pillar | What it does | Attacks |
|---|---|---|
| 🔎 **Variant Resolver** | Pins the exact variant from visible-feature evidence (not a dropdown), using information-gain questioning | Variant mismatch (#1) |
| 📋 **Condition Disclosure** | Definition-led capture of repaints / CNG / service records, each tied to a transparent price effect | Undisclosed condition (#2) |
| 🎯 **Honest Estimate** | Quantile model → P10/P50/P90 range + confidence score; the range **widens** when inputs are uncertain | Expectation-setting |
| 📷 **Guided AI Inspection** | Live camera walk-around with real on-device CV ("move closer / hold steady"), or photo/video upload — captures evidence that **tightens the range and lifts confidence** | Input trust |

### On the camera/vision features (`/inspect.html`, [`docs/08-vision.md`](docs/08-vision.md))
Real, on-device computer vision guides capture (focus via Laplacian variance, exposure,
stability, framing, glare) — **validated objectively** by `tests/vision_validation.py` (11/11
monotonicity checks pass). We deliberately **do not** claim "100% accurate" pixel classification
— that would recreate the exact broken-promise problem this product solves. Instead: reliable
capture guidance + evidence-backed confidence (measured: range width 23.9% → 16.8%, confidence
85 → 100) + a documented roadmap to trained classifiers with real accuracy numbers. Raw media
never leaves the device.

---

## Does it actually work? (backtest)

`tests/backtest.py` simulates two worlds over the same cars & realized auction prices — the
only difference is the front door. It measures the **below-floor rate** (the CEO's ~40% pain).
See the printed result after running; TruePrice cuts the below-floor rate substantially by
removing the aspiration-bias variant overshoot and widening honestly for the rest.

---

## Quick start

```bash
# 1. Environment (one-time)
python3 -m venv .venv
.venv/bin/python -m pip install -U pip numpy scikit-learn pandas joblib "fastapi" "uvicorn[standard]"

# 2. Build data + train model (reproducible)
.venv/bin/python model/generate_data.py --rows 24000
.venv/bin/python model/train.py

# 3. Run the product
.venv/bin/python backend/run.py        # -> http://127.0.0.1:8000

# 4. Verify
.venv/bin/python tests/test_core.py          # unit tests (3 pillars)
.venv/bin/python tests/backtest.py           # below-floor-rate demonstration
.venv/bin/python tests/vision_validation.py  # CV metric reliability proof
```

Open **http://127.0.0.1:8000** and walk the seller wizard: basics → variant resolver →
condition → honest estimate. Or try **http://127.0.0.1:8000/inspect.html** for the guided
camera / upload inspection (use a device with a camera for the live flow).

---

## Repository map

```
cars24_project/
├── README.md                  ← you are here
├── image.png                  ← the source LinkedIn post (problem statement)
├── docs/                      ← full product documentation (read 00 → 09)
│   ├── 00-research.md            problem framing, landscape, features, responsible-AI
│   ├── 01-product.md             vision, personas & pain, PRD, success metrics
│   ├── 02-data-and-model.md      the synthetic DGP + quantile model design
│   ├── 03-architecture.md        system design & the four pillars
│   ├── 04-metrics.md             what we measure & how (incl. backtest)
│   ├── 05-api.md                 API reference
│   ├── 06-responsible-ai.md      the trust/ethics commitments, operationalized
│   ├── 07-runbook.md             run, rebuild, troubleshoot
│   ├── 08-vision.md              guided AI inspection: CV methodology + reliability proof
│   └── 09-pitch.md               founder pitch: market, pain, UX, traction, moat, the ask
├── model/                     ← market catalog, data generator, trainer, MODEL_CARD
├── backend/                   ← FastAPI: variant_resolver, condition, pricing, main
├── frontend/                  ← vanilla HTML/CSS/JS seller wizard (no build step)
└── tests/                     ← unit tests + backtest harness
```

## Design principles
- **Honesty over optimism** — the range width tells the truth about uncertainty.
- **Explainable by default** — every estimate ships with a "why" and a "what could change."
- **Fair by construction** — price is a function of the car, never the seller.
- **Free & reproducible** — every number rebuilds from open code (see the model card).

> **Scope honesty:** this is a demonstration MVP on a *synthetic* dataset (real Cars24 data is
> proprietary and not a free resource). The deliverable is the **product mechanics and honesty
> properties**, not market-accurate rupee figures. Not affiliated with Cars24.
