# 08 · Guided AI Inspection (Camera + Upload)

Two features, one honest design: (1) upload photos/video for AI analysis, and (2) a live camera
that walks you around the car with real-time guidance ("move closer", "hold steady"), the way a
human inspector works. This doc covers the research, the exact methodology, the **objective
reliability proof**, and — importantly — the honest scope: what is real today and what is
roadmap.

> **The honesty stance (read this first).** No computer-vision system is "100% accurate," and
> claiming it would recreate the very problem TruePrice exists to solve — a confident number that
> reality can't honour. So we do not claim to have *classified* your car from pixels. We do
> something reliable and provable instead: **real image-quality analysis** that guides capture,
> **structured evidence collection** that mirrors a manual inspection, and **honest confidence**
> that rises when inputs are photo-backed. Automated damage/variant *classification* is a
> documented roadmap stage (see §6), gated behind real labelled data and measured accuracy.

---

## 1. What a human inspector actually does (the research)
A field inspection is a fixed walk-around that gathers evidence at specific points, each of which
maps to a price factor. We encoded that same sequence (`frontend/vision.js` → `POINTS`,
`backend/app/evidence.py` → `REQUIRED_POINTS`):

| Inspection point | What it establishes | Pricing signal |
|---|---|---|
| Front / Rear / Left / Right | panel condition, alignment, repaint tells | exterior condition |
| Roof | sunroof presence/type | **variant** (sunroof) |
| Front wheel (close) | alloy vs steel | **variant** (wheels) |
| Dashboard & screen | touchscreen/infotainment tier | **variant** (infotainment) |
| Odometer (close) | true kilometres | **km** |
| Engine bay | aftermarket CNG kit | **condition** (CNG) |
| Tyre tread (close) | tyre wear | **condition** (tyres) |

This is why the flow is *guided* and *sequenced* rather than "upload some pics" — the sequence is
the domain knowledge.

## 2. The real computer vision (what runs on every frame)
All analysis runs **on the device** (browser). Raw pixels never leave — only a compact quality
summary reaches the server (privacy by design). The metrics are standard CV measures on the
frame's luminance (`backend/app/vision_metrics.py`, ported verbatim to `frontend/vision.js`):

| Metric | Method | Drives |
|---|---|---|
| **Sharpness / focus** | variance of the Laplacian (Pech-Pacheco et al., 2000 — the classic focus measure) | "Hold steady to focus" |
| **Exposure** | mean luminance + blown/crushed pixel fractions | "Too dark" / "Too much glare" |
| **Stability** | mean absolute frame-to-frame difference | "Hold steady" |
| **Framing** | edge density (fraction of pixels on a strong gradient) | "Move closer to fill the frame" |
| **Glare** | fraction of near-saturated specular pixels | "Change your angle" |

These combine into a transparent 0–100 **quality score** and a single, priority-ordered guidance
message (fix the most disqualifying problem first). A shot **auto-captures** only when it stays
"good" (quality ≥ 65, in focus, steady, well-lit) for several consecutive frames.

**Device independence:** absolute Laplacian variance varies by camera and scene, so the *live*
focus decision is scored **relative to a rolling session peak** — no magic per-device threshold.
The offline reference uses fixed thresholds for reproducible validation.

## 3. Reliability — the objective proof
"Reliable" has a precise, testable meaning for these metrics: they must respond correctly and
**monotonically** to controlled changes in the input. `tests/vision_validation.py` constructs
synthetic frames with *known* properties and checks every metric. Actual run — **11/11 pass**:

```
[1] Sharpness vs known blur radius 0,1,2,4,8 -> [25140, 528, 110, 20, 4]   (strictly decreasing ✓)
[2] Exposure   dark/normal/bright mean luma  -> 24 / 121 / 191             (tracks brightness ✓)
[3] Stability  still/shifted frame-diff       -> 0.0000 / 0.1844            (motion detected ✓)
[4] Framing    far/near edge density          -> 0.0021 / 0.6161           ('move closer' fires ✓)
[5] Glare      hotspot raises glare & flags it                              (✓)
[6] End-to-end clean frame -> quality 98, capturable                       (✓)
```
This is deterministic (seeded) and reproducible: `.venv/bin/python tests/vision_validation.py`.
It is the evidence that the guidance is driven by real image properties, not static rules.

## 4. From evidence to a better estimate (the payoff)
Captured, quality-gated shots become an **Evidence Pack**, scored by `backend/app/evidence.py`
into a `coverage`, `avg_quality`, and `evidence_strength` (0–1). Two honest effects on the
estimate (`backend/app/pricing.py`):
1. **Confidence uplift** — a small, capped bonus (`+6 × evidence_strength`): a timestamped,
   quality-gated photo backing an input is more trustworthy than a typed dropdown (recall: 4 in
   10 typed variants are wrong).
2. **Tighter range** — residual input uncertainty is reduced (`× (1 − 0.4 × evidence_strength)`),
   because the variant and condition are now confirmed by images.

**Measured effect** (same car, self-report vs evidence-backed): range width **23.9% → 16.8%**,
confidence **85 → 100**. Deliberately modest and capped — evidence improves *input trust*; it
never replaces the physical inspection or claims to have classified anything.

## 5. Upload path
Same engine, no camera required: per-part photo upload (each graded, low-quality shots rejected
with a reason) and an optional walkaround video (frames sampled, graded; a good video backs the
four exterior points). Signals (sunroof, wheels, CNG, tyres, odometer) are confirmed by the
seller against the captured image — evidence-backed self-report.

## 5b. Optional Smart Assist (Gemini) — opt-in, off by default
The on-device CV above is the **default** and always runs (free, private, validated). Smart
Assist is a **purely optional** layer: when — and only when — a `GEMINI_API_KEY` is configured,
a captured frame for a signal point (roof, wheel, dashboard, engine bay, tyre, odometer) can also
be sent to Google's Gemini multimodal model to *suggest* the answer, pre-filling the confirm step.

**How it stays honest and safe:**
- **Suggestion, never verdict.** Gemini returns one of the *same allowed option values* the manual
  flow uses (from the catalog/condition specs) plus a self-reported confidence. The seller still
  taps to confirm; the inspector still verifies. The UI shows "✨ AI suggests … — tap to confirm".
- **Opt-in + off by default.** The toggle only appears if a key is set, and defaults to off.
- **Privacy is explicit.** With Smart Assist ON, a captured frame leaves the device to Google —
  the UI says so. The default on-device path sends nothing.
- **Graceful degradation.** No key, an error, a timeout, or an "unsure" answer all fall back to
  the normal on-device confirm flow — the product never breaks.
- **Not "100% accurate" either.** Gemini is a strong model, not an oracle; we show its confidence
  and keep the human-confirm loop. Same honesty rule as everywhere else.

**Architecture:** `backend/app/smart_assist.py` (REST call, stdlib only — no extra dependency),
gated by `backend/app/config.py` (`.env` loader). Endpoints: `GET /api/smart-assist/status`
(cheap, drives the toggle visibility), `GET /api/smart-assist/health` (makes one real Gemini call
so the UI shows the *true* reachability state — `ready` / `quota_exhausted` / `invalid_key` /
`error` — instead of a silent fallback the first time it's needed), and
`POST /api/smart-assist/analyze`. Full request/response shapes in `docs/05-api.md`. Enable via
`.env` (see `.env.example`).

**Why a separate health probe matters:** a key can be syntactically valid but functionally dead
(e.g. Google's prepay-billing model returns HTTP 429 "credits depleted" even though the key
authenticates fine). Checking `/status` alone would show the toggle as available and then fail
silently on first use. `/health` is called the moment the user opts in, so a dead key is visible
immediately with the real reason, not discovered mid-inspection.

> *Implementation note:* for analyzing a captured frame, the `generateContent` multimodal call is
> the right tool (structured JSON output, cheaper, reliable). The streaming **Gemini Live** API
> suits a real-time conversational walk-through — a heavier future option; the live "move closer"
> guidance here is already handled for free on-device.

## 6. Honest scope & roadmap
**Real today:** guided sequence; real per-frame quality analysis (validated); auto-capture;
evidence-backed confidence + tighter ranges; on-device privacy.

**Not claimed today (and why):** automatic *classification* of variant, damage severity, or a CNG
kit purely from pixels. Production-grade classifiers need thousands of labelled images and report
a *measured* accuracy — they are never "100%". Building one on free resources without that data
would be exactly the kind of confident-but-unreliable output this product refuses to ship.

**Roadmap (designed-for seams):**
- **Odometer OCR** → auto-read km from the odometer shot (validate against typed value).
- **Repaint/panel classifier** → flag *possible* repaint from color/gloss discontinuity, always
  with honest confidence + human confirm.
- **Variant feature classifier** (sunroof/alloys/screen) → pre-fill the confirm step; the resolver
  already consumes exactly these signals, so it drops in.
- **Per-device threshold calibration** and a labelled validation set with published accuracy/PR
  curves — so any future "the AI detected X" comes with a real, honest number.

Each of these plugs into the existing evidence pipeline without reshaping it.
