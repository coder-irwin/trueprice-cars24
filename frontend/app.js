/* TruePrice seller wizard — vanilla JS client. */
const App = (() => {
  const state = {
    catalog: null, disclosures: [],
    car: { fuel: "petrol", transmission: "manual", owners: 1, km: 45000,
           city_tier: "metro", color: "neutral" },
    resolver: { answers: {}, confidence: 1.0, price_spread: 0, resolved: false, variant: null },
    condition: {},
  };
  const $ = (id) => document.getElementById(id);
  const inr = (n) => "₹" + Number(n).toLocaleString("en-IN");
  const lakh = (n) => "₹" + (n / 100000).toFixed(2) + "L";

  const STEPS = ["basics", "variant", "condition", "result"];
  function goto(step) {
    STEPS.forEach((s, i) => {
      $("step-" + s).classList.toggle("active", s === step);
      const chip = $("steps").children[i];
      chip.className = "s" + (s === step ? " active" : (STEPS.indexOf(step) > i ? " done" : ""));
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function api(path, body) {
    const opt = body ? { method: "POST", headers: { "content-type": "application/json" },
                         body: JSON.stringify(body) } : {};
    const r = await fetch(path, opt);
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
    return r.json();
  }

  // ---- Init: load catalog, populate basics ------------------------------------------
  async function init() {
    state.catalog = await api("/api/catalog");
    state.disclosures = state.catalog.disclosures;
    const sel = $("model");
    state.catalog.models.forEach((m, i) => {
      const o = document.createElement("option");
      o.value = i; o.textContent = `${m.make} ${m.model}`;
      sel.appendChild(o);
    });
    sel.onchange = onModelChange;
    onModelChange();
    // year dropdown (age 0..12)
    const yr = $("year"), now = new Date().getFullYear();
    for (let y = now; y >= now - 12; y--) {
      const o = document.createElement("option"); o.value = y; o.textContent = y; yr.appendChild(o);
    }
    yr.value = now - 4;
  }

  function currentModel() { return state.catalog.models[+$("model").value]; }

  function onModelChange() {
    const m = currentModel();
    const fill = (id, arr, fmt) => {
      const s = $(id); s.innerHTML = "";
      arr.forEach(v => { const o = document.createElement("option");
        o.value = v; o.textContent = fmt ? fmt(v) : v; s.appendChild(o); });
    };
    fill("fuel", m.fuels, cap);
    fill("transmission", m.transmissions, txLabel);
  }
  const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
  const txLabel = (t) => ({ manual: "Manual", amt: "AMT (auto)", cvt: "CVT (auto)",
    dct: "DCT (auto)", torque_converter: "Automatic (TC)" }[t] || t);

  function readBasics() {
    const m = currentModel();
    const now = new Date().getFullYear();
    Object.assign(state.car, {
      make: m.make, model: m.model, segment: m.segment,
      fuel: $("fuel").value, transmission: $("transmission").value,
      age: now - +$("year").value, km: +$("km").value, owners: +$("owners").value,
      city_tier: $("city_tier").value, color: $("color").value,
    });
  }

  // ---- Step 2: Variant resolver ------------------------------------------------------
  async function toResolver() {
    readBasics();
    state.resolver = { answers: {}, confidence: 1.0, price_spread: 0, resolved: false, variant: null };
    goto("variant");
    await stepResolver();
  }

  async function stepResolver() {
    const body = $("resolver-body");
    body.innerHTML = '<span class="spinner"></span> <span class="muted">Working it out…</span>';
    const r = await api("/api/variant/resolve", {
      make: state.car.make, model: state.car.model,
      fuel: state.car.fuel, transmission: state.car.transmission,
      answers: state.resolver.answers,
    });
    state.resolver.confidence = r.confidence;
    state.resolver.price_spread = r.price_spread;
    state.resolver.resolved = r.resolved;
    state.resolver.variant = r.top_variant;
    renderCandidates(r.candidates);

    if (r.resolved || !r.next_question) {
      body.innerHTML =
        `<div class="panel"><div class="h">✓ Looks like your car is the
         <b>${r.top_variant}</b> variant</div>
         <div class="d">We're ${Math.round(r.confidence * 100)}% confident based on your answers.
         You can continue, or refine below.</div></div>`;
      if (r.next_question) appendRefine(body, r.next_question);
      $("variant-next").disabled = false;
      $("variant-next").textContent = `Continue with ${r.top_variant} →`;
      state.car.variant = r.top_variant;
    } else {
      renderQuestion(body, r.next_question);
      $("variant-next").disabled = true;
    }
  }

  function renderQuestion(container, q) {
    container.innerHTML = `<div style="font-weight:700;font-size:17px">${q.question}</div>
      <div class="qmeta">Answer what you can see — it narrows down the variant fast.</div>
      <div class="choices" id="choices"></div>`;
    const c = $("choices");
    q.options.forEach(opt => {
      const b = document.createElement("button");
      b.className = "choice";
      b.innerHTML = `<span class="dot"></span><span>${opt.label}</span>`;
      b.onclick = async () => {
        state.resolver.answers[q.feature] = opt.value;
        await stepResolver();
      };
      c.appendChild(b);
    });
  }

  function appendRefine(container, q) {
    const d = document.createElement("div");
    d.className = "hint";
    d.innerHTML = `Not sure? One more check: `;
    const btn = document.createElement("button");
    btn.className = "linkbtn"; btn.textContent = q.question;
    btn.onclick = () => renderQuestion($("resolver-body"), q);
    d.appendChild(btn);
    container.appendChild(d);
  }

  function renderCandidates(cands) {
    const el = $("candidates");
    el.innerHTML = "";
    cands.filter(c => c.posterior >= 0.02).forEach(c => {
      const span = document.createElement("span");
      span.className = "cand";
      span.innerHTML = `<b>${c.variant}</b> · ${Math.round(c.posterior * 100)}% · ${lakh(c.price_new)} new`;
      el.appendChild(span);
    });
  }

  function showManualVariant() {
    const m = currentModel();
    const body = $("resolver-body");
    body.innerHTML = `<div style="font-weight:700;font-size:17px">Pick your variant</div>
      <div class="qmeta">If you're sure, choose it here. We'll treat it as confirmed.</div>
      <div class="choices" id="choices"></div>`;
    m.variants.slice().sort((a,b)=>a.trim_rank-b.trim_rank).forEach(v => {
      const b = document.createElement("button");
      b.className = "choice";
      b.innerHTML = `<span class="dot"></span><span>${v.name} · <span class="muted">${lakh(v.price_new)} when new</span></span>`;
      b.onclick = () => {
        state.car.variant = v.name;
        state.resolver = { answers: {}, confidence: 1.0, price_spread: 0, resolved: true, variant: v.name };
        $("candidates").innerHTML = "";
        body.innerHTML = `<div class="panel"><div class="h">✓ ${v.name} selected</div>
          <div class="d">Treated as confirmed by you.</div></div>`;
        $("variant-next").disabled = false;
        $("variant-next").textContent = `Continue with ${v.name} →`;
      };
      $("choices").appendChild(b);
    });
  }

  // ---- Step 3: Condition -------------------------------------------------------------
  function toCondition() {
    // defaults
    state.condition = { accident: "none", aftermarket_cng: "no",
      service_records: "full", tyres: "good", insurance: "comprehensive" };
    const body = $("condition-body");
    body.innerHTML = "";
    state.disclosures.forEach(d => {
      const wrap = document.createElement("div");
      wrap.style.marginBottom = "22px";
      wrap.innerHTML = `<div style="font-weight:700">${d.question}</div>
        <div class="qmeta">${d.why_it_matters}</div>`;
      const choices = document.createElement("div");
      choices.className = "choices";
      d.options.forEach((opt, idx) => {
        const b = document.createElement("button");
        b.className = "choice" + (idx === 0 ? " sel" : "");
        b.innerHTML = `<span class="dot"></span><span>${opt.label}</span>`;
        b.onclick = () => {
          state.condition[d.field] = opt.value;
          [...choices.children].forEach(c => c.classList.remove("sel"));
          b.classList.add("sel");
        };
        choices.appendChild(b);
      });
      wrap.appendChild(choices);
      body.appendChild(wrap);
    });
    goto("condition");
  }

  // ---- Step 4: Estimate --------------------------------------------------------------
  async function getEstimate() {
    goto("result");
    $("result-body").innerHTML = '<div style="text-align:center;padding:40px"><span class="spinner"></span><div class="muted" style="margin-top:10px">Building your honest estimate…</div></div>';
    const payload = {
      ...state.car, ...state.condition,
      variant_confidence: state.resolver.confidence,
      variant_price_spread: state.resolver.price_spread,
    };
    try {
      const e = await api("/api/estimate", payload);
      renderResult(e);
    } catch (err) {
      $("result-body").innerHTML = `<div class="panel"><div class="h">Something went wrong</div>
        <div class="d">${err.message}</div></div>`;
    }
  }

  function renderResult(e) {
    const gaugeColor = e.confidence_band === "high" ? "var(--good)"
      : e.confidence_band === "medium" ? "var(--warn)" : "var(--bad)";
    // range bar geometry
    const span = e.range_high - e.range_low || 1;
    const ptPct = ((e.point - e.range_low) / span) * 100;

    const factors = e.breakdown.factors.map(f =>
      `<div class="factor"><div><div class="lab">${f.label}</div>
        <div class="note">${f.note}</div></div>
        <div class="amt neg">${f.delta < 0 ? "−" : "+"}${inr(Math.abs(f.delta))}</div></div>`).join("");

    const changes = e.what_could_change.length
      ? e.what_could_change.map(c => `<div class="panel"><div class="h">${c.label}
          <span class="muted">(${c.impact_pct}%)</span></div>
          <div class="d">${c.why_it_matters}</div></div>`).join("")
      : `<div class="panel"><div class="d">Nothing you've disclosed pulls the price down —
          the main remaining variable is the live auction itself.</div></div>`;

    const sources = e.uncertainty_sources.map(s =>
      `<div class="panel"><div class="h">${s.source}</div><div class="d">${s.detail}</div></div>`).join("");

    $("result-body").innerHTML = `
      <h2 style="text-align:center">${e.input_echo.make} ${e.input_echo.model} · ${e.input_echo.variant}</h2>
      <div class="range-hero">
        <div class="pt">${inr(e.point)}</div>
        <div class="rg">Honest range: ${inr(e.range_low)} – ${inr(e.range_high)}
          <span class="muted">(±${(e.width_pct/2).toFixed(1)}%)</span></div>
      </div>
      <div class="rangebar">
        <div class="fill" style="left:8%;right:8%"></div>
        <div class="mark" style="left:${8 + ptPct*0.84}%"></div>
        <div class="lbl" style="left:8%">${lakh(e.range_low)}</div>
        <div class="lbl" style="left:92%">${lakh(e.range_high)}</div>
      </div>
      <div class="confrow">
        <div class="gauge" style="--v:${e.confidence};--c:${gaugeColor}">
          <div class="inner">${e.confidence}</div></div>
        <div class="txt">
          <div>Confidence <span class="badge ${e.confidence_band}">${e.confidence_band.toUpperCase()}</span></div>
          <small>How sure we are given what you've told us. Higher = tighter, more reliable range.</small>
        </div>
      </div>

      <div class="section-t">Why this number</div>
      <div class="factor"><div class="lab">A clean ${e.input_echo.variant}, low use</div>
        <div class="amt base">${inr(e.breakdown.clean_reference)}</div></div>
      ${factors}
      <div class="factor"><div class="lab"><b>Your estimate (mid-point)</b></div>
        <div class="amt"><b>${inr(e.point)}</b></div></div>

      <div class="section-t">What could change at inspection</div>
      ${changes}

      <div class="section-t">Why the range isn't tighter</div>
      ${sources}

      <div class="disclaimer">${e.disclaimer}</div>`;
  }

  function restart() { goto("basics"); }

  document.addEventListener("DOMContentLoaded", init);
  return { goto, toResolver, toCondition, getEstimate, showManualVariant, restart };
})();
