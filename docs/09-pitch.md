# 09 · Founder Pitch — TruePrice

Everything you need to pitch TruePrice: the problem, the market, the pain for every stakeholder,
the solution, the UX, the proof, the business case, and the moat. Written to be a founder's — and
Cars24 leadership's — first choice.

> Market figures below are **directional, from public sources and industry reporting**, and are
> labelled approximate. They frame the opportunity; they are not audited financials.

---

## 1. One line
**TruePrice makes the online estimate a promise you can keep** — by resolving the exact variant
and true condition *before* the quote, then showing an honest, confidence-scored range. It kills
the estimate-to-final-price gap that is the #1 seller complaint in online used-car sales.

## 2. The problem (in the founder's own words)
Cars24's CEO, publicly: *"The most persistent complaint we hear from sellers is about the gap
between the online estimate and the final price."* You see ₹8–9.5L, you get ₹7L.

Per Cars24's own FY26 data (1,00,000+ monthly inspections):
- **35%** land within the range, **25%** beat it — but **~40% land BELOW the quoted floor.**
- Drivers: **variant mismatch** (4 of 10 cars are a different variant than entered; 15–20% price
  swing) and **undisclosed condition** (repaints, aftermarket CNG, missing service records).

**Reframed as a wedge:** this is not a pricing-accuracy problem, it's an **input-accuracy and
expectation** problem. That is a *fixable* problem — and whoever fixes it owns seller trust.

## 3. Why this matters — the market
India's used-car market is large, under-penetrated by organized players, and consolidating online
— which is exactly when trust becomes the deciding moat.

| Metric (approx., public/industry sources) | Figure |
|---|---|
| Used cars sold in India / year | ~**5–5.4 million** units and rising |
| Used-to-new ratio | ~**1.4:1**, trending toward mature-market 2–2.5:1 |
| Market value | ~**$32–34B**, ~**15%+ CAGR** |
| Organized/online penetration | ~**20–25%** (long runway) |
| Cars24 scale | operating at large multi-lakh annual volumes across India + international |

**TAM → SAM → SOM (directional):**
- **TAM:** every online C2B/C2C used-car transaction in India where an instant estimate is shown.
- **SAM:** Cars24's own seller funnel — 1,00,000+ inspections/month is the beachhead named by the
  CEO. The ~40% below-floor cohort is the immediate wound.
- **SOM (beachhead):** the variant-mismatch + undisclosed-condition slice of that cohort — the
  cases TruePrice provably improves today (see §7).

**Why now:** (a) the CEO has *publicly committed* to building exactly this ("better input
validation to catch variant mismatches"); (b) smartphone cameras make on-device guided inspection
viable at zero marginal cost; (c) responsible-AI expectations are rising, making "the honest
estimate" a marketable differentiator, not just a compliance checkbox.

## 4. Pain points — for everyone (not just the seller)
The gap radiates through the whole system. TruePrice serves each stakeholder:

| Stakeholder | Pain today | TruePrice win |
|---|---|---|
| **Seller** (Priya) | feels bait-and-switched: ₹9.5L → ₹7L; can't name her variant; blindsided by a repaint held against her | guided to true variant; told up front what moves price; honest range with a plain "why" |
| **Buyer / Dealer** (Rahul) | wrong-variant, hidden-condition leads waste inspection & bidding; adverse selection | cleaner, variant-correct, condition-disclosed leads → efficient auctions |
| **Inspector** (Sunita) | doorstep renegotiation when reality ≠ listing; seller anger lands on her | most surprises resolved before arrival; she verifies, not re-discovers |
| **Pricing / DS** (Arjun) | garbage-in inputs cap model accuracy; no input-reliability signal | structured inputs + confidence score; widen honestly instead of being confidently wrong |
| **Ops / CX** (Meera) | "estimate vs final" is the top recurring ticket | fewer below-floor surprises + self-serve explanation → ticket deflection |
| **The business** (Cars24) | trust erosion → churn, bad word-of-mouth, CAC pressure | trust as a moat; higher completion, repeat & referral; efficient auctions |

## 5. The solution — four pillars
1. **🔎 Variant Resolver** — pins the exact variant from *visible-feature evidence* via
   information-gain questioning (not a harder dropdown). Attacks the 15–20% swing at the source.
2. **📋 Condition Disclosure** — definition-led capture of the high-impact, commonly-hidden items,
   each tied to a transparent price effect. No doorstep surprises.
3. **🎯 Honest Estimate** — a quantile model returns P10/P50/P90 + a confidence score; the range
   **widens when inputs are uncertain**. Width tells the truth.
4. **📷 Guided AI Inspection** — live camera walk-around with real on-device CV ("move closer /
   hold steady"), or photo/video upload. Evidence **tightens the range and lifts confidence** —
   measured, not asserted.

**The through-line — Responsible AI as the wedge:** every estimate is explainable ("why this
number, what could change"), never overclaims, and prices the car, not the person. In a category
built on distrust, *being the honest one is the growth strategy.*

## 6. The UX (why sellers will love it)
Designed to feel effortless and trustworthy — the opposite of a form.

```
 Basics ─▶ Variant Resolver ─▶ Condition ─▶ Honest Estimate
 (30s)     2–3 tap questions    tap choices   range + confidence + "why" + "what could change"
                    │
                    └── or ── 📷 Guided Camera: we direct each shot, auto-capture, confirm from photos
```
- **Two or three taps** pin the variant — the app asks the single most informative question each
  time (information gain), so it's fast.
- **Definition-led choices** ("Minor — a repaint or small dent repair") teach as they ask.
- **The result screen is the product:** a big honest range, a confidence gauge, a factor-by-factor
  "why this number," a "what could change at inspection" panel, and a plain-English disclaimer.
- **Guided camera** feels like a friendly inspector in your pocket: real-time "move closer / too
  dark / great, captured ✓", a quality ring, a filmstrip of your shots — all analysed on-device
  (private).
- **Accessibility & polish:** semantic HTML, keyboard-navigable, light/dark, no build step.

Try it: `/` (wizard) and `/inspect.html` (camera). See `docs/03-architecture.md` for how it's built.

## 7. Traction / proof (this repo runs it)
Not slideware — reproducible results from the code:

| Proof | Result | Where |
|---|---|---|
| **Below-floor rate cut** | **34.9% → 15.2% (−56%)**, *without* ballooning range width (12.9%→13.1%) | `tests/backtest.py` |
| **Point accuracy** | **4.3% MAPE** on held-out data | `model/train.py` |
| **Evidence value** | photo-backed inputs: width **23.9% → 16.8%**, confidence **85 → 100** | `docs/08-vision.md` |
| **CV reliability** | **11/11** monotonicity checks on controlled inputs | `tests/vision_validation.py` |
| **Honesty invariants** | **11/11** unit tests (less certainty ⇒ wider range, lower confidence) | `tests/test_core.py` |

## 8. Business case — what it's worth to Cars24
The mechanism is trust → retention → GMV, plus cost-out:
- **Retention & referral:** a seller treated honestly returns and refers; a bait-and-switched one
  churns and warns others. Even a few points of the ~40% below-floor cohort converting to
  "fairly treated" compounds into repeat GMV and lower CAC.
- **Ticket & renegotiation cost-out:** "estimate vs final" is the top recurring complaint; fewer
  surprises + a self-serve explanation deflect tickets and shorten doorstep renegotiations.
- **Auction efficiency:** variant-correct, condition-disclosed leads reduce adverse selection and
  wasted inspector/bidder time.
- **Brand:** "the honest estimate" is a defensible, marketable position in a low-trust category.

*(A quantified model plugs Cars24's own funnel numbers into these levers — the levers are the
pitch; the exact figures are theirs to fill.)*

## 9. Moat / defensibility
- **The variant/condition knowledge graph** (`catalog.py`) + resolver logic compounds with every
  inspection: real inspection outcomes label real inputs → the resolver and pricing get better,
  and the evidence pipeline turns each session into training data for future classifiers.
- **Trust brand** is a slow-to-copy moat; being *first and consistent* on honesty wins it.
- **On-device CV** = zero marginal inference cost and a privacy story competitors relying on
  server-side pipelines can't easily match.
- **Data flywheel:** guided evidence → labelled images → trained classifiers (odometer OCR,
  repaint detection) → even tighter estimates → more trust → more sellers.

## 10. Roadmap
- **Now (this MVP):** 3 pillars + guided inspection + honest estimate, validated end-to-end.
- **Next:** odometer OCR; repaint/panel classifier (honest confidence + human confirm); variant
  feature classifier pre-filling the resolver; RTO/registration decode as a strong prior.
- **Then:** conformal calibration to hit nominal coverage; per-device threshold auto-calibration;
  live A/B on below-floor rate, completion, and CSAT; B2B "trust infrastructure" licensing to the
  wider C2B auto market.

## 11. The ask / next steps
1. **Pilot** on a slice of the live seller funnel; instrument the north-star **below-floor rate**
   plus completion and CSAT (the offline backtest predicts a large drop).
2. **Wire real transaction data** behind the same `features.py` schema (drop-in) to replace the
   synthetic DGP.
3. **Fund the classifier flywheel** (odometer OCR first — highest reliability, immediate value).

---

### Appendix — the honesty guarantee (why this is safe to put in front of customers)
TruePrice never claims more certainty than it has: it prices the car not the person, explains
every number, shows uncertainty as range width, and — for the camera — does **validated** capture
guidance rather than unproven pixel classification. In a trust category, that guarantee *is* the
product. See `docs/06-responsible-ai.md`.
