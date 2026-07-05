# 00 · Research & Problem Framing

> **Source of truth for this project.** Everything downstream — the PRD, the model, the
> product — traces back to the problem stated here. Read this first.

---

## 0. Provenance — where the problem came from

This project starts from a public LinkedIn post by **Vikram Chopra (Founder & CEO, Cars24)**,
captured in `image.png` at the repo root. OCR transcription of the post:

> **The most persistent complaint we hear from sellers on Cars24 is about the gap between the
> online estimate and the final price.**
>
> I understand why it feels wrong. You enter your car details, see a range of ₹8 to ₹9.5 lakhs,
> and then the final price comes in at ₹7 lakhs.
>
> Here is what is actually happening:
> - The online estimate is a **prediction**. It takes your inputs, matches them against
>   historical transaction data, and generates a range. The final price is determined after
>   **physical inspection and live auction**. These are two different systems.
> - As per our FY26 data across **1,00,000+ monthly inspections: 35% of sellers get a final
>   price within the estimate range. 25% get more than the upper end.**
>
> For the remaining, the biggest driver is **variant mismatch. 4 out of 10 inspected cars show
> a different variant than what the seller entered online. That alone can shift the price by
> 15–20%.** The second driver is **undisclosed condition issues: repaints, aftermarket CNG,
> missing service records.**
>
> We are building better input validation to catch variant mismatches before the estimate is
> generated. We are also working on making the estimate communication clearer about what it is
> and what it is not.
>
> A handful of complaints do not define pricing competitiveness across tens of thousands of
> cars. But they do tell us what we need to fix. And that's what we are working on.

**This is not a hypothetical.** The CEO named the problem, quantified it, and named the two
root causes. Our job is to build the thing he says they are building — and go further.

---

## 1. The problem, stated precisely

**Sellers lose trust when the online estimate is materially higher than the final offer.**

The estimate and the final price come from **two different systems**:

| | Online estimate | Final price |
|---|---|---|
| **Method** | ML prediction on self-reported inputs | Physical inspection + live auction |
| **Inputs** | What the seller *typed* | What the inspector *found* + what buyers *bid* |
| **Failure mode** | Optimistic / wide / wrong variant | Reality |

The gap is not (mostly) a pricing-accuracy problem. **It is an input-accuracy and
expectation-setting problem.** The model is fed wrong or incomplete inputs, then communicates a
confident-looking range that reality can't honour.

### The numbers (from the post, FY26, 1,00,000+ monthly inspections)

```
┌─────────────────────────────────────────────────────────────┐
│ 35%  final price WITHIN the estimate range      ✅ good      │
│ 25%  final price ABOVE the upper end            ✅ upside    │
│ 40%  final price BELOW the range  ← THE PROBLEM  ❌ trust hit │
└─────────────────────────────────────────────────────────────┘
```

So **60% of sellers already get a fair or better outcome.** The reputational damage comes from
the **~40%** who land below the quoted floor. Within that 40%, the CEO names the drivers:

1. **Variant mismatch — the #1 driver.** 4 of 10 inspected cars are a *different variant* than
   the seller selected online. Variant alone moves price **15–20%**. On a ₹9L car that is
   **₹1.35L–₹1.8L** — more than enough to blow through the bottom of a quoted range.
2. **Undisclosed condition — the #2 driver.** Repaints (prior accident/panel damage),
   aftermarket CNG (safety + resale hit), missing service records (unverifiable history).

### Why variant mismatch is so common (root-cause analysis)

Indian car variants are genuinely confusing, and the confusion is structural, not careless:

- **Trim ladders are long and cryptic.** One model-year can have 8–15 variants: `LXI / VXI /
  ZXI / ZXI+`, `Sigma / Delta / Zeta / Alpha`, `E / S / SX / SX(O)`, `Ambition / Highline`.
  Sellers routinely pick the wrong rung.
- **Fuel/transmission combinations multiply trims.** Petrol vs diesel vs CNG-from-factory,
  manual vs AMT vs CVT vs DCT — each is a different price line.
- **Feature-based sub-variants are invisible to owners.** Alloys vs steel wheels, projector vs
  halogen lamps, touchscreen vs basic head-unit, 2 vs 6 airbags, sunroof — these separate
  variants that owners can't name.
- **Facelifts reuse names across price points.** The "same" ZXI spans years with very different
  values.
- **Aspiration bias.** Given a dropdown, sellers round *up* to the fancier-sounding trim.

**Implication:** you cannot fix this by asking the seller "which variant?" harder. You fix it
by **resolving the variant from evidence the seller can actually provide** — registration
details, visible features, photos — and by pricing *honestly under uncertainty* until the
variant is pinned.

---

## 2. Existing solutions — landscape scan (free/public knowledge)

> Scope note: this is a synthesis from publicly known product behaviour of these companies. No
> proprietary data or paid sources were used. It is directional, not a citation-grade survey.

### 2a. Instant-offer / C2B players (most similar to the problem)

| Player | Estimate approach | Gap handling | Gap for us |
|---|---|---|---|
| **Cars24** (IN) | ML range from typed inputs → inspection → auction | Range shown; gap is the stated pain | This *is* the target |
| **Spinny** (IN) | Assured buy price, heavier human curation upfront | Fewer surprises but slower, narrower inventory | — |
| **CarDekho / OLX Autos** (IN) | Instant quote + home inspection | Similar two-system gap | — |
| **Carvana / Vroom** (US) | Instant online offer, firm for 7 days | Offer is a *commitment*, not a teaser range | Different market/logistics |
| **Kelley Blue Book / Edmunds** (US) | Reference valuation, condition-tiered | Educational; user self-selects condition tier | Good pattern to borrow |
| **We Buy Any Car** (UK) | Online value → branch inspection → adjusted | Explicit "price may change on inspection" framing | Good expectation pattern |

### 2b. What the good ones do that Cars24's stated pain implies is missing

1. **KBB/Edmunds** make **condition explicit and self-selected** ("Fair / Good / Very Good /
   Excellent" with concrete definitions). The user is *taught* what moves price before seeing a
   number. → We adopt **condition-first, definition-led disclosure.**
2. **Carvana/We Buy Any Car** treat the number as a **near-commitment with a stated
   revision-on-inspection rule**, not a marketing range. → We adopt **honest, confidence-scored
   ranges** whose *width is a feature*, not a bug.
3. **VIN/registration decoders** (used widely in the US via VIN) resolve trim from the vehicle
   identity rather than a dropdown. India has no clean VIN-trim decode, but the **registration
   number + RTO + a short guided feature check** can get most of the way. → We adopt an
   **evidence-based Variant Resolver.**

### 2c. The white space (our opportunity)

Nobody in the instant-offer space combines all three:

```
   Evidence-based        Honest, confidence-       Radical transparency
   variant resolution  +  scored range under     +  ("here's exactly why,
   (not a dropdown)       uncertainty                and what could change")
```

That combination is exactly what the CEO's post says is missing. **That is our product.**

---

## 3. What actually drives a used-car price (feature & metric research)

To price honestly we must know what moves value. Grounded in Indian-market used-car valuation
practice:

### 3a. Identity features (define the baseline — must be exact)
- **Make / Model / Year (age)** — the primary anchor.
- **Variant / Trim** — **the 15–20% swing the CEO calls out.** Highest-leverage input.
- **Fuel type** — petrol / diesel / CNG(factory) / hybrid / electric. Diesel and CNG carry
  regional and regulatory premiums/discounts (e.g. NCR 10yr diesel / 15yr petrol de-reg rules).
- **Transmission** — manual / AMT / CVT / DCT / torque-converter.

### 3b. Usage & wear features (depreciate the baseline)
- **Odometer (km driven)** — non-linear; penalty accelerates past ~register thresholds
  (~80–100k km).
- **Number of owners** — 1st owner commands a clear premium; each subsequent owner discounts.
- **Age × km interaction** — a 3-yr car with 90k km ≠ a 3-yr car with 25k km.

### 3c. Condition & provenance features (the #2 driver — often undisclosed)
- **Accident / structural repair history** — repaints and panel replacements are the tell.
- **Aftermarket CNG** — safety, warranty, and resale penalty distinct from factory CNG.
- **Service history completeness** — full service records vs missing → verifiability premium.
- **Tyres, battery, clutch** — consumable state.
- **Insurance type & No-Claim Bonus** — comprehensive + high NCB signals careful ownership.
- **Exterior/interior wear, cosmetic** — dents, scratches, upholstery.

### 3d. Market & context features (shift the whole curve)
- **City / RTO tier** — metro vs tier-2 demand, and regulatory de-registration age limits.
- **Color** — white/silver/grey liquidate faster; niche colors discount.
- **Seasonality & demand** — model desirability, fuel-price regime, festive demand.
- **Registration validity / RC status, hypothecation (loan) clearance.**

### 3e. Metrics used to *evaluate the pricing system* (our KPIs)
- **MAPE / MAE** of point estimate vs realized auction price.
- **Range coverage** — % of final prices that fall inside the quoted P10–P90 band (target:
  well-calibrated, e.g. ~80% inside an 80% band).
- **Below-floor rate** — % of sellers whose final price is *below* the quoted floor. **This is
  the north-star pain metric** the CEO is describing. Goal: drive it down from ~40%.
- **Variant-correction rate** — % of sessions where the resolver changed the seller's initial
  variant guess (proof the resolver is doing work).
- **Range width vs confidence calibration** — do low-confidence sessions get appropriately
  wider ranges?

---

## 4. Responsible-AI framing (this is a trust product first)

A pricing model that quietly shapes what someone is paid for their car is a **high-stakes,
consumer-facing AI system.** Trust is the entire point. Principles we commit to and design for:

1. **Honesty over optimism.** Never show a tighter or higher range than the evidence supports.
   Width encodes uncertainty; we do not hide uncertainty to look confident.
2. **Explainability by default.** Every estimate ships with a plain-language breakdown of *why*
   this number and *what could change* at inspection. No black-box number.
3. **Expectation-setting, not bait.** The estimate is explicitly labelled a prediction, with
   the inspection/auction step named — exactly the "clearer communication" the CEO asks for.
4. **Fairness.** Price on the car, not the person. No features that proxy for the seller's
   identity, negotiating savvy, or protected attributes. Documented in the model card.
5. **Data honesty.** For this MVP we use a **synthetic, transparently-generated dataset**
   (real Cars24 transaction data is proprietary and not a free resource). Every claim the model
   makes is reproducible from open code. Limitations are stated, not buried.
6. **Contestability.** The breakdown shows which inputs drove the number, so a seller can see
   *"ah, it's the aftermarket CNG"* and act on it — or dispute it at inspection with context.

See `docs/06-responsible-ai.md` and `model/MODEL_CARD.md` for the operationalization.

---

## 5. Free-resources-only constraint (how we honour it)

Everything in this project is free and open:

- **Language/runtime:** Python 3 + Node (already on the machine).
- **ML:** scikit-learn, numpy (open-source, pip).
- **Backend:** FastAPI + Uvicorn (open-source).
- **Frontend:** vanilla HTML/CSS/JS — no paid framework, no build step, no CDN dependency.
- **Data:** synthetic dataset generated by our own open code, grounded in public market
  knowledge. No paid data feeds, no proprietary Cars24 data.
- **Everything reproducible** from the repo with the documented commands.

---

## 6. From research → build (the thesis)

> **The estimate-to-final-price gap is an input-accuracy and expectation problem, not primarily
> a pricing-accuracy problem. So we fix the inputs (resolve the variant from evidence, capture
> condition honestly) and we fix the expectation (an explainable, confidence-scored range whose
> width tells the truth). Do those two things and the ~40% below-floor rate falls.**

That thesis produces exactly three product pillars, carried through the rest of the docs:

1. **Variant Resolver** — evidence-based, kills the 15–20% variant swing before it happens.
2. **Condition Disclosure** — definition-led, surfaces the repaints/CNG/service gaps up front.
3. **Honest Estimate** — confidence-scored P10–P50–P90 range with a full "why + what could
   change" explanation.

→ Continue to `docs/01-product.md` (vision, personas, PRD, metrics).
