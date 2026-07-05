# 01 · Product — Vision, Personas, PRD & Metrics

> Builds directly on `docs/00-research.md`. If you haven't read that, read it first — the
> numbers and the thesis live there.

---

## Product name: **TruePrice**

**A variant-aware, condition-honest, confidence-scored estimate engine for Cars24 sellers.**

> *"The estimate you can trust — because we nail the variant and the condition before we quote,
> and we tell you exactly what could change."*

---

## 1. Vision & strategy

**Vision.** A seller should never be surprised at the door. The number we show online should be
the number reality can honour — and where it can't be exact, the *range should tell the truth
about why.*

**Strategic bet.** The estimate-to-final gap is Cars24's most persistent seller-trust wound
(per the CEO). Trust compounds: a seller who feels fairly treated returns, refers, and
converts. **TruePrice turns the estimate from a marketing teaser into a trust instrument.**

**Where TruePrice sits.** It replaces the "type your details → see a range" front door with a
guided flow that (a) resolves the true variant, (b) captures condition honestly, and (c)
returns an explainable confidence-scored range. It hands a *clean, structured, confidence-
tagged lead* to the inspection/auction systems downstream.

```
  Seller  ──▶  TruePrice front door  ──▶  Inspection  ──▶  Live auction  ──▶  Final price
              (resolve variant,            (verify)         (discover)
               capture condition,
               honest range + why)
              ▲ we shrink the gap here, before it becomes a broken promise
```

---

## 2. Personas & pain points (research the pain for *everyone*)

The CEO's post is about the seller, but the gap radiates outward. We map the pain for each
stakeholder so the product serves the whole system.

### 👤 Priya — the **Seller** (primary)
- **Who:** owns a 2019 Maruti Baleno, wants to upgrade, comparing Cars24 vs Spinny vs OLX.
- **Job:** get a fair price fast, without feeling tricked.
- **Pains:** sees ₹8–9.5L online, gets ₹7L at the door; feels bait-and-switched; doesn't know
  her exact variant; doesn't know a repaint or aftermarket CNG matters until it's held against
  her; can't tell if the drop is fair or a lowball.
- **TruePrice wins:** she's guided to her true variant, told up front what moves price, and
  shown an honest range with a plain-language "why." Fewer, smaller surprises → trust.

### 👤 Rahul — the **Buyer / Dealer** (auction side)
- **Job:** buy good inventory at the right price, fast, with low post-purchase surprise.
- **Pains:** listings with wrong variant / hidden condition waste inspection and bidding time;
  mispriced leads erode auction efficiency.
- **TruePrice wins:** cleaner, variant-correct, condition-disclosed leads → more efficient
  auctions, less adverse selection.

### 👤 Sunita — the **Inspector** (field ops)
- **Job:** verify the car quickly and correctly at the seller's door.
- **Pains:** arrives to find a different variant / undisclosed CNG → awkward, adversarial
  renegotiation on the doorstep; seller anger lands on her; longer inspections.
- **TruePrice wins:** most variant/condition surprises resolved *before* she arrives; she
  verifies rather than re-discovers; shorter, calmer inspections.

### 👤 Arjun — **Pricing / Data Science** (internal)
- **Job:** keep estimates accurate and well-calibrated.
- **Pains:** garbage-in inputs (wrong variant) cap model accuracy no matter how good the model;
  no clean signal on input reliability.
- **TruePrice wins:** structured inputs + a **confidence score** per lead; the model can widen
  ranges under uncertainty instead of being confidently wrong.

### 👤 Meera — **Ops / Trust & Safety / CX** (internal)
- **Job:** reduce complaints, refunds, drop-offs, and CSAT damage.
- **Pains:** the "estimate vs final" complaint is the top recurring ticket; each one is a manual
  soothe.
- **TruePrice wins:** fewer below-floor surprises → fewer complaints; the explanation is
  self-serve, deflecting tickets.

### 🏢 The **Business** (Cars24)
- **Job:** win seller trust at scale without over-paying or under-converting.
- **Pains:** trust erosion → churn, bad word-of-mouth, CAC pressure; every renegotiation is
  friction and cost.
- **TruePrice wins:** trust as a moat; higher completion and repeat/referral; efficient
  auctions; a defensible "we're the honest one" position.

---

## 3. PRD — Product Requirements

### 3.1 Objectives (what "done" means)
1. **Reduce the below-floor rate** — fewer sellers whose final price falls under the quoted
   floor (the ~40% the CEO describes).
2. **Resolve the true variant before the estimate** — attack the #1 driver (15–20% swing) at
   the source, via evidence, not a harder dropdown.
3. **Surface condition honestly up front** — repaints, aftermarket CNG, missing service records
   captured before the number, not discovered at inspection.
4. **Communicate the estimate honestly** — a confidence-scored range labelled as a prediction,
   with a transparent "why" and "what could change." (The CEO's "clearer communication.")

### 3.2 In scope (MVP)
- Guided seller flow: **basics → Variant Resolver → Condition Disclosure → Honest Estimate.**
- **Variant Resolver:** disambiguation via distinguishing features; confidence per candidate.
- **Condition Disclosure:** definition-led capture of the high-impact, often-hidden items.
- **Pricing model:** scikit-learn quantile model → P10/P50/P90 + a confidence score driven by
  input completeness and variant certainty.
- **Explainability:** per-estimate factor breakdown + "what could change at inspection."
- **API + web UI**, fully runnable locally, free stack only.

### 3.3 Out of scope (MVP — named so scope is honest)
- Real Cars24 transaction data / live pricing (proprietary; we use a synthetic dataset).
- Photo-based CV variant/damage detection (future; we design the seam for it).
- RTO/registration API integration (future; we simulate the evidence-based decode).
- Auth, payments, real auction integration, mobile-native apps.

### 3.4 Functional requirements
| # | Requirement | Attacks |
|---|---|---|
| F1 | Capture make/model/year/fuel/transmission/km/owners/city | baseline |
| F2 | Variant Resolver narrows to the true variant via feature questions, returns candidates with confidence | **variant mismatch (#1)** |
| F3 | If variant stays uncertain, the estimate range **widens** and says so | expectation-setting |
| F4 | Condition Disclosure captures accident/repaint, aftermarket CNG, service records, tyres, insurance/NCB | **undisclosed condition (#2)** |
| F5 | Estimate returns P10/P50/P90 + confidence score (0–100) | honest range |
| F6 | Every estimate includes a factor breakdown ("why") and "what could change at inspection" | responsible AI |
| F7 | All logic reproducible & documented | trust |

### 3.5 Non-functional requirements
- **Honesty:** never narrower/higher than evidence supports (enforced by confidence→width link).
- **Latency:** estimate < 300 ms locally.
- **Transparency:** no factor influences price without appearing in the breakdown.
- **Reproducibility:** `make` / documented commands rebuild data, model, and app from scratch.
- **Accessibility:** semantic HTML, keyboard-navigable, legible contrast.

---

## 4. Success metrics (how we'd measure it in production)

### North-star
- **Below-floor rate** ↓ — % of sellers whose final price < quoted floor. Baseline ~40%
  (implied). **Primary success signal.**

### Supporting / driver metrics
- **Variant-correction rate** — % sessions where the Resolver changed the seller's first guess
  (proof it's working; expect meaningful given "4 of 10" mismatch).
- **Range coverage (calibration)** — % of final prices inside the quoted P10–P90 band; target a
  well-calibrated ~80% for an 80% band.
- **Confidence↔width calibration** — low-confidence sessions get wider ranges *and* those wider
  ranges still cover reality.
- **Estimate MAPE** vs realized auction price.
- **Complaint rate / CSAT** on "estimate vs final."
- **Completion rate** through the flow (honesty shouldn't tank conversion — trust should lift it).

### Guardrail metrics (don't win the wrong way)
- **Under-quote drift** — don't just lower every estimate to be "safe." Watch the *25% who beat
  the upper end* stays healthy; the goal is calibration, not pessimism.
- **Flow drop-off** — the guided steps must not add enough friction to lose sellers.

### MVP instrumentation (what this repo actually demonstrates)
Because we can't measure real sellers here, the repo ships a **backtest harness** that runs the
model over a held-out synthetic set and reports MAPE, P10–P90 coverage, below-floor rate, and
confidence↔width calibration — the same metric shapes we'd track in production. See
`docs/04-metrics.md` and `tests/`.

---

## 5. The three pillars → the rest of the build

| Pillar | Doc | Code |
|---|---|---|
| Variant Resolver | `docs/03-architecture.md` | `backend/app/variant_resolver.py` |
| Condition Disclosure | `docs/03-architecture.md` | `backend/app/condition.py` |
| Honest Estimate | `model/MODEL_CARD.md`, `docs/04-metrics.md` | `model/`, `backend/app/pricing.py` |

→ Continue to `docs/02-data-and-model.md`.
