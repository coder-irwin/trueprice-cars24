/* TruePrice guided inspection — real on-device computer vision + guided capture.
 *
 * The metric functions below are a faithful port of backend/app/vision_metrics.py, which is
 * validated by tests/vision_validation.py (the objective proof they behave correctly). All
 * analysis runs here in the browser on live frames / uploaded media — raw pixels never leave
 * the device.
 */
(() => {
"use strict";
const $ = (id) => document.getElementById(id);
const inr = (n) => "₹" + Number(n).toLocaleString("en-IN");
const lakh = (n) => "₹" + (n / 100000).toFixed(2) + "L";

// ---- 1. VISION METRICS (port of vision_metrics.py) -----------------------------------
function toLuma(data, W, H) {           // data = Uint8ClampedArray RGBA
  const l = new Float32Array(W * H);
  for (let i = 0, p = 0; i < l.length; i++, p += 4)
    l[i] = 0.299 * data[p] + 0.587 * data[p + 1] + 0.114 * data[p + 2];
  return l;
}
function sharpness(l, W, H) {            // variance of Laplacian
  let sum = 0, sum2 = 0, n = 0;
  for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) {
    const i = y * W + x;
    const lap = -4 * l[i] + l[i - 1] + l[i + 1] + l[i - W] + l[i + W];
    sum += lap; sum2 += lap * lap; n++;
  }
  const m = sum / n; return sum2 / n - m * m;
}
function exposure(l) {
  let sum = 0, blown = 0;
  for (let i = 0; i < l.length; i++) { sum += l[i]; if (l[i] > 240) blown++; }
  return { mean: sum / l.length, blown: blown / l.length };
}
function stability(l, prev) {
  if (!prev || prev.length !== l.length) return 0;
  let s = 0; for (let i = 0; i < l.length; i++) s += Math.abs(l[i] - prev[i]);
  return s / l.length / 255;
}
function framing(l, W, H) {              // edge density
  let e = 0, n = 0;
  for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) {
    const i = y * W + x;
    const gx = l[i + 1] - l[i - 1], gy = l[i + W] - l[i - W];
    if (Math.hypot(gx, gy) > 40) e++; n++;
  }
  return e / n;
}
function glare(l) { let g = 0; for (let i = 0; i < l.length; i++) if (l[i] > 250) g++; return g / l.length; }

const TH = { dark: 55, bright: 205, blown: 0.12, unstable: 0.045, framing_min: 0.02, glare: 0.06 };

/* Live assessment. Sharpness is scored RELATIVE to a rolling session peak so focus detection
 * is device/scene independent (absolute Laplacian variance varies by camera & content). */
function assess(l, W, H, prev, session) {
  const s = sharpness(l, W, H), ex = exposure(l), st = stability(l, prev),
        fr = framing(l, W, H), gl = glare(l);
  session.maxSharp = Math.max(session.maxSharp * 0.995, s);
  const focus = clip01(s / (session.maxSharp * 0.55 + 1e-6));

  let guidance = "Looks great — hold still", status = "good";
  if (ex.mean < TH.dark) { guidance = "Too dark — find better light"; status = "bad"; }
  else if (ex.mean > TH.bright || ex.blown > TH.blown || gl > TH.glare) { guidance = "Too much glare — change your angle"; status = "bad"; }
  else if (fr < TH.framing_min) { guidance = "Move closer to fill the frame"; status = "bad"; }
  else if (st > TH.unstable) { guidance = "Hold steady"; status = "warn"; }
  else if (focus < 0.6) { guidance = "Hold steady to focus"; status = "warn"; }

  const qExpo = clip01(1 - Math.abs(ex.mean - 130) / 130) * (1 - clip01(ex.blown / 0.25));
  const qFrame = clip01(fr / 0.06), qStable = prev ? clip01(1 - st / TH.unstable) : 1;
  const qGlare = clip01(1 - gl / 0.12);
  const quality = Math.round(100 * (0.35 * focus + 0.25 * qExpo + 0.2 * qFrame + 0.12 * qStable + 0.08 * qGlare));
  const capturable = status === "good" && quality >= 65;
  return { guidance, status, quality, capturable, focus };
}
const clip01 = (x) => Math.max(0, Math.min(1, x));

// ---- 2. STATE + INSPECTION POINTS ----------------------------------------------------
const POINTS = [
  { id: "front", icon: "🚗", title: "Front of the car", instr: "Stand ~2m back and fit the whole front in the frame." },
  { id: "rear", icon: "🔙", title: "Rear of the car", instr: "Fit the whole rear — bumper to roofline." },
  { id: "left", icon: "⬅️", title: "Left side profile", instr: "Step back and capture the full left side." },
  { id: "right", icon: "➡️", title: "Right side profile", instr: "Step back and capture the full right side." },
  { id: "roof", icon: "☀️", title: "The roof", instr: "Angle up to show the roof — we'll confirm any sunroof.", signal: { type: "variant", feature: "sunroof" } },
  { id: "wheel", icon: "🛞", title: "A front wheel (close-up)", instr: "Get close to one front wheel.", signal: { type: "variant", feature: "wheels" } },
  { id: "dash", icon: "📟", title: "Dashboard & screen", instr: "From the driver's door, show the dashboard and screen.", signal: { type: "variant", feature: "infotainment" } },
  { id: "odo", icon: "🔢", title: "Odometer reading", instr: "Close-up of the odometer (ignition on).", signal: { type: "odometer" } },
  { id: "engine", icon: "🔧", title: "Engine bay", instr: "Open the bonnet — we check for an aftermarket CNG kit.", signal: { type: "condition", field: "aftermarket_cng" } },
  { id: "tyre", icon: "🌀", title: "A tyre tread (close-up)", instr: "Close-up of one tyre's tread.", signal: { type: "condition", field: "tyres" } },
];

const state = {
  catalog: null, featureQ: {}, disclosures: {},
  car: {}, captures: {}, // id -> {quality, thumb}
  variantAnswers: {}, conditionAnswers: {}, odometer: null,
  smart: { enabled: false }, useSmart: false,
};

async function api(path, body) {
  const opt = body ? { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) } : {};
  const r = await fetch(path, opt);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json();
}

async function init() {
  state.catalog = await api("/api/catalog");
  state.catalog.feature_questions.forEach(q => state.featureQ[q.feature] = q);
  state.catalog.disclosures.forEach(d => state.disclosures[d.field] = d);
  const sel = $("model");
  state.catalog.models.forEach((m, i) => {
    const o = document.createElement("option"); o.value = i; o.textContent = `${m.make} ${m.model}`; sel.appendChild(o);
  });
  sel.onchange = onModel; onModel();
  const yr = $("year"), now = new Date().getFullYear();
  for (let y = now; y >= now - 12; y--) { const o = document.createElement("option"); o.value = y; o.textContent = y; yr.appendChild(o); }
  yr.value = now - 4;
  $("mode-camera").onclick = () => { readBasics(); startCamera(); };
  $("mode-upload").onclick = () => { readBasics(); startUpload(); };
  // Smart Assist (Gemini) — only surfaced if the server has a key configured.
  try {
    state.smart = await api("/api/smart-assist/status");
    if (state.smart.enabled) {
      $("smart-toggle").classList.remove("hidden");
      $("smart-check").addEventListener("change", (e) => { state.useSmart = e.target.checked; });
    }
  } catch (e) { /* smart assist optional; ignore */ }
}

// Ask Gemini to suggest a signal from a captured frame. Always safe; returns null on any issue.
async function smartSuggest(point, thumb) {
  if (!state.smart.enabled || !state.useSmart || !point.signal) return null;
  try {
    const r = await api("/api/smart-assist/analyze",
      { point_id: point.id, image: thumb, make: state.car.make, model: state.car.model });
    return r && r.available ? r : null;
  } catch (e) { return null; }
}
function curModel() { return state.catalog.models[+$("model").value]; }
function onModel() {
  const m = curModel();
  const fill = (id, arr, fmt) => { const s = $(id); s.innerHTML = ""; arr.forEach(v => { const o = document.createElement("option"); o.value = v; o.textContent = fmt ? fmt(v) : v; s.appendChild(o); }); };
  const cap = s => s[0].toUpperCase() + s.slice(1);
  fill("fuel", m.fuels, cap);
  fill("transmission", m.transmissions, t => ({ manual: "Manual", amt: "AMT", cvt: "CVT", dct: "DCT", torque_converter: "Automatic" }[t] || t));
}
function readBasics() {
  const m = curModel(), now = new Date().getFullYear();
  state.car = { make: m.make, model: m.model, segment: m.segment, fuel: $("fuel").value,
    transmission: $("transmission").value, age: now - +$("year").value, owners: +$("owners").value,
    city_tier: $("city_tier").value, color: $("color").value };
}
function show(stage) { ["basics", "camera", "upload", "result"].forEach(s => $("stage-" + s).classList.toggle("hidden", s !== stage)); window.scrollTo({ top: 0, behavior: "smooth" }); }

// ---- 3. LIVE CAMERA CONTROLLER -------------------------------------------------------
let cam = null;
async function startCamera() {
  show("camera");
  const video = $("video");
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false });
    video.srcObject = stream;
    await video.play();
  } catch (e) {
    $("guidance-txt").textContent = "Camera unavailable — try Upload instead";
    $("guidance").className = "guidance bad";
    return;
  }
  cam = { stream, idx: 0, prev: null, session: { maxSharp: 1 }, stableCount: 0, running: true, video };
  $("cam-skip").onclick = () => nextPoint(true);
  $("cam-manual").onclick = () => grab(true);
  loadPoint();
  requestAnimationFrame(analyzeLoop);
}
function loadPoint() {
  const p = POINTS[cam.idx];
  $("cam-progress").textContent = `${cam.idx + 1} / ${POINTS.length}`;
  $("cam-title").textContent = p.title;
  $("cam-instruction").textContent = p.instr;
  cam.session.maxSharp = 1; cam.stableCount = 0;
}
let lastAnalyze = 0;
function analyzeLoop(ts) {
  if (!cam || !cam.running) return;
  if (ts - lastAnalyze > 110 && cam.video.videoWidth) {
    lastAnalyze = ts;
    const ac = $("analysis"), W = ac.width, H = ac.height, ctx = ac.getContext("2d", { willReadFrequently: true });
    ctx.drawImage(cam.video, 0, 0, W, H);
    const l = toLuma(ctx.getImageData(0, 0, W, H).data, W, H);
    const a = assess(l, W, H, cam.prev, cam.session);
    cam.prev = l;
    // UI
    $("guidance-txt").textContent = a.guidance;
    $("guidance").className = "guidance " + a.status;
    $("qval").textContent = a.quality;
    $("qprog").style.strokeDashoffset = 276 * (1 - a.quality / 100);
    $("qprog").style.stroke = a.status === "good" ? "var(--good)" : a.status === "warn" ? "var(--warn)" : "var(--bad)";
    // auto-capture when sustained-good
    cam.stableCount = a.capturable ? cam.stableCount + 1 : 0;
    if (cam.stableCount >= 3) { grab(false, a.quality); }
    cam._lastQ = a.quality;
  }
  requestAnimationFrame(analyzeLoop);
}
function grab(manual, quality) {
  if (!cam) return;
  const q = quality != null ? quality : (cam._lastQ || 60);
  const cap = $("capture"), v = cam.video;
  cap.width = 480; cap.height = Math.round(480 * v.videoHeight / v.videoWidth);
  cap.getContext("2d").drawImage(v, 0, 0, cap.width, cap.height);
  const thumb = cap.toDataURL("image/jpeg", 0.55);
  const p = POINTS[cam.idx];
  state.captures[p.id] = { quality: q, thumb };
  addFilm(p.id, thumb, q);
  document.querySelector(".camstage").classList.add("flash");
  setTimeout(() => document.querySelector(".camstage").classList.remove("flash"), 500);
  cam.stableCount = 0;
  if (p.signal) { pauseAndConfirm(p, thumb, () => nextPoint(false)); }
  else nextPoint(false);
}
function addFilm(id, thumb, q) {
  const s = document.createElement("div"); s.className = "shot";
  s.innerHTML = `<img src="${thumb}"><span class="q">${q}</span>`; $("filmstrip").appendChild(s);
}
function nextPoint(skipped) {
  if (skipped) { /* leave uncaptured */ }
  cam.idx++;
  if (cam.idx >= POINTS.length) { finishCamera(); return; }
  loadPoint();
}
function finishCamera() {
  cam.running = false;
  if (cam.stream) cam.stream.getTracks().forEach(t => t.stop());
  finalize();
}

// ---- 4. CONFIRM MODAL ----------------------------------------------------------------
async function pauseAndConfirm(point, thumb, done) {
  const modal = $("confirm-modal");
  $("confirm-thumb").style.backgroundImage = `url(${thumb})`;
  const sig = point.signal;
  if (sig.type === "odometer") { showOdo(modal, point, thumb, done); return; }

  let question, why, options, onPick;
  if (sig.type === "variant") {
    const q = state.featureQ[sig.feature]; question = q.question; why = "Confirm what your captured photo shows.";
    options = q.options; onPick = (v) => { state.variantAnswers[sig.feature] = v; };
  } else { // condition
    const d = state.disclosures[sig.field]; question = d.question; why = d.why_it_matters;
    options = d.options; onPick = (v) => { state.conditionAnswers[sig.field] = v; };
  }
  $("confirm-q").textContent = question; $("confirm-why").textContent = why;
  const box = $("confirm-choices"); box.innerHTML = "";
  const badge = smartBadge(box);
  const btns = {};
  options.forEach(opt => {
    const b = document.createElement("button"); b.className = "choice";
    b.innerHTML = `<span class="dot"></span><span>${opt.label}</span>`;
    b.onclick = () => { onPick(opt.value); modal.classList.add("hidden"); done(); };
    box.appendChild(b); btns[opt.value] = b;
  });
  modal.classList.remove("hidden");
  // Optional Gemini suggestion — highlights a choice, never auto-submits.
  const s = await smartSuggest(point, thumb);
  if (s && s.detected && btns[s.detected]) {
    btns[s.detected].classList.add("ai");
    badge.className = "ai-badge";
    badge.innerHTML = `✨ AI suggests: <b style="margin-left:4px">${btns[s.detected].textContent.trim()}</b> · ${Math.round((s.confidence||0)*100)}% — tap to confirm`;
  } else if (s) {
    badge.className = "ai-badge thinking"; badge.textContent = `✨ ${s.note || "AI wasn't sure — pick what you see"}`;
  } else { badge.remove(); }
}
function smartBadge(box) {
  const badge = document.createElement("div");
  if (state.useSmart && state.smart.enabled) { badge.className = "ai-badge thinking"; badge.textContent = "✨ Smart Assist analysing…"; }
  box.parentNode.insertBefore(badge, box);
  return badge;
}
function showOdo(modal, point, thumb, done) {
  $("confirm-q").textContent = "What does the odometer read?";
  $("confirm-why").textContent = "Enter the exact number your photo shows (in km).";
  const box = $("confirm-choices"); box.innerHTML = "";
  const badge = smartBadge(box);
  const inp = document.createElement("input"); inp.type = "number"; inp.min = 0; inp.placeholder = "e.g. 45000";
  inp.style.marginBottom = "10px";
  const b = document.createElement("button"); b.className = "btn-primary"; b.textContent = "Confirm reading";
  b.onclick = () => { state.odometer = +inp.value || null; modal.classList.add("hidden"); done(); };
  box.appendChild(inp); box.appendChild(b);
  modal.classList.remove("hidden");
  smartSuggest(point, thumb).then(s => {
    if (s && s.detected != null) { inp.value = s.detected; badge.className = "ai-badge"; badge.innerHTML = `✨ AI read <b style="margin-left:4px">${(+s.detected).toLocaleString("en-IN")} km</b> · ${Math.round((s.confidence||0)*100)}% — check &amp; confirm`; }
    else if (s) { badge.className = "ai-badge thinking"; badge.textContent = `✨ ${s.note || "Couldn't read it — type it in"}`; }
    else badge.remove();
  });
}

// ---- 5. UPLOAD PATH ------------------------------------------------------------------
function startUpload() {
  show("upload");
  const host = $("upload-points"); host.innerHTML = "";
  POINTS.forEach(p => {
    const row = document.createElement("div"); row.className = "uprow";
    const inputId = "up-" + p.id;
    row.innerHTML = `<div class="icon">${p.icon}</div>
      <div class="meta"><b>${p.title}</b><span>${p.instr}</span></div>
      <span class="status none" id="st-${p.id}">Not added</span>
      <label class="up" for="${inputId}">Upload</label>
      <input type="file" accept="image/*" id="${inputId}">`;
    host.appendChild(row);
    row.querySelector("input").addEventListener("change", (e) => handleUploadImage(p, e.target.files[0]));
  });
  $("videofile").addEventListener("change", (e) => handleUploadVideo(e.target.files[0]));
  $("upload-done").onclick = finalize;
}
async function gradeImageFile(file) {
  const img = await loadImage(URL.createObjectURL(file));
  const W = 160, H = Math.round(160 * img.height / img.width) || 120;
  const c = document.createElement("canvas"); c.width = W; c.height = H;
  const ctx = c.getContext("2d", { willReadFrequently: true }); ctx.drawImage(img, 0, 0, W, H);
  const l = toLuma(ctx.getImageData(0, 0, W, H).data, W, H);
  const a = assess(l, W, H, null, { maxSharp: sharpness(l, W, H) / 0.55 }); // self-normalize single image
  // thumbnail
  const tc = document.createElement("canvas"); tc.width = 480; tc.height = Math.round(480 * img.height / img.width);
  tc.getContext("2d").drawImage(img, 0, 0, tc.width, tc.height);
  return { quality: a.quality, status: a.status, guidance: a.guidance, thumb: tc.toDataURL("image/jpeg", 0.55) };
}
async function handleUploadImage(point, file) {
  if (!file) return;
  const st = $("st-" + point.id); st.textContent = "Analysing…"; st.className = "status none";
  const r = await gradeImageFile(file);
  if (r.quality >= 55) {
    state.captures[point.id] = { quality: r.quality, thumb: r.thumb };
    st.textContent = `Clear · ${r.quality}`; st.className = "status ok";
    if (point.signal) pauseAndConfirm(point, r.thumb, () => {});
  } else {
    st.textContent = `${r.guidance}`; st.className = "status bad";
  }
}
async function handleUploadVideo(file) {
  if (!file) return;
  const vs = $("video-status"); vs.textContent = "Sampling frames…";
  const v = document.createElement("video"); v.src = URL.createObjectURL(file); v.muted = true;
  await new Promise(res => v.addEventListener("loadedmetadata", res, { once: true }));
  const W = 160, H = Math.round(160 * v.videoHeight / v.videoWidth) || 120;
  const c = document.createElement("canvas"); c.width = W; c.height = H; const ctx = c.getContext("2d", { willReadFrequently: true });
  const N = 8, quals = []; let best = { quality: -1 };
  for (let i = 1; i <= N; i++) {
    const t = v.duration * i / (N + 1);
    await seek(v, t); ctx.drawImage(v, 0, 0, W, H);
    const l = toLuma(ctx.getImageData(0, 0, W, H).data, W, H);
    const a = assess(l, W, H, null, { maxSharp: sharpness(l, W, H) / 0.55 });
    quals.push(a.quality);
    if (a.quality > best.quality) {
      const tc = document.createElement("canvas"); tc.width = 480; tc.height = Math.round(480 * v.videoHeight / v.videoWidth);
      tc.getContext("2d").drawImage(v, 0, 0, tc.width, tc.height);
      best = { quality: a.quality, thumb: tc.toDataURL("image/jpeg", 0.55) };
    }
  }
  const avg = Math.round(quals.reduce((a, b) => a + b, 0) / quals.length);
  // A good walkaround video backs the 4 exterior points.
  if (avg >= 55) {
    ["front", "rear", "left", "right"].forEach(id => {
      if (!state.captures[id]) { state.captures[id] = { quality: avg, thumb: best.thumb }; $("st-" + id).textContent = `From video · ${avg}`; $("st-" + id).className = "status ok"; }
    });
    vs.textContent = `Video analysed — avg quality ${avg}/100. Exterior shots covered; confirm the rest below.`;
  } else {
    vs.textContent = `Video is a bit low-quality (avg ${avg}/100) — add clearer photos for the parts that matter.`;
  }
}
const seek = (v, t) => new Promise(res => { v.addEventListener("seeked", res, { once: true }); v.currentTime = t; });
const loadImage = (src) => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = src; });

// ---- 6. FINALIZE: resolve variant + evidence + estimate ------------------------------
async function finalize() {
  show("result");
  $("result-body").innerHTML = '<div style="text-align:center;padding:40px"><span class="spinner"></span><div class="muted" style="margin-top:10px">Analysing your inspection & building the estimate…</div></div>';
  // evidence score
  const pack = POINTS.map(p => ({ id: p.id, captured: !!state.captures[p.id], quality: state.captures[p.id]?.quality || 0 }));
  const evScore = await api("/api/evidence/score", { points: pack });
  // resolve variant from captured+confirmed feature answers
  const rv = await api("/api/variant/resolve", { make: state.car.make, model: state.car.model,
    fuel: state.car.fuel, transmission: state.car.transmission, answers: state.variantAnswers });
  // km: from odometer if captured, else estimate from age
  const km = state.odometer != null ? state.odometer : state.car.age * 12000;
  const payload = {
    ...state.car, variant: rv.top_variant, km,
    accident: "none", tyres: state.conditionAnswers.tyres || "good",
    aftermarket_cng: state.conditionAnswers.aftermarket_cng || "no",
    service_records: "full", insurance: "comprehensive",
    variant_confidence: rv.confidence, variant_price_spread: rv.price_spread,
    evidence_strength: evScore.evidence_strength,
  };
  try {
    const e = await api("/api/estimate", payload);
    renderResult(e, evScore, rv);
  } catch (err) {
    $("result-body").innerHTML = `<div class="panel"><div class="h">Something went wrong</div><div class="d">${err.message}</div></div>`;
  }
}
function renderResult(e, ev, rv) {
  const band = e.confidence_band, gc = band === "high" ? "var(--good)" : band === "medium" ? "var(--warn)" : "var(--bad)";
  const factors = (e.breakdown?.factors || []).map(f =>
    `<div class="factor"><div><div class="lab">${f.label}</div><div class="note">${f.note}</div></div><div class="amt neg">${f.delta < 0 ? "−" : "+"}${inr(Math.abs(f.delta))}</div></div>`).join("");
  const shots = POINTS.filter(p => state.captures[p.id]).map(p =>
    `<div class="shot"><img src="${state.captures[p.id].thumb}"><span class="q">${state.captures[p.id].quality}</span></div>`).join("");
  const evNote = e.evidence_note ? `<div class="panel"><div class="h">📸 Evidence-backed</div><div class="d">${e.evidence_note}</div></div>` : "";
  $("result-body").innerHTML = `
    <h2 style="text-align:center">${e.input_echo.make} ${e.input_echo.model} · ${e.input_echo.variant}</h2>
    <p class="sub" style="text-align:center">Variant confirmed from your photos (${Math.round(rv.confidence * 100)}% match)</p>
    <div class="range-hero"><div class="pt">${inr(e.point)}</div>
      <div class="rg">Honest range: ${inr(e.range_low)} – ${inr(e.range_high)} <span class="muted">(±${(e.width_pct / 2).toFixed(1)}%)</span></div></div>
    <div class="confrow">
      <div class="gauge" style="--v:${e.confidence};--c:${gc}"><div class="inner">${e.confidence}</div></div>
      <div class="txt"><div>Confidence <span class="badge ${band}">${band.toUpperCase()}</span></div>
      <small>Inspection evidence: ${ev.captured_count}/${ev.required_count} shots captured, avg quality ${ev.avg_quality}/100.</small></div>
    </div>
    ${evNote}
    <div class="section-t">Your captured evidence</div>
    <div class="filmstrip">${shots || '<span class="muted">No shots captured</span>'}</div>
    <div class="section-t">Why this number</div>
    <div class="factor"><div class="lab">A clean ${e.input_echo.variant}, low use</div><div class="amt base">${inr(e.breakdown.clean_reference)}</div></div>
    ${factors}
    <div class="factor"><div class="lab"><b>Your estimate (mid-point)</b></div><div class="amt"><b>${inr(e.point)}</b></div></div>
    <div class="disclaimer">${e.disclaimer}</div>`;
}

document.addEventListener("DOMContentLoaded", init);
})();
