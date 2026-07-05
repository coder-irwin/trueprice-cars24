"""
main.py — TruePrice API + static frontend host.

Endpoints:
  GET  /api/health              liveness + model metrics
  GET  /api/catalog             models/variants/fuels/transmissions for the UI
  POST /api/variant/resolve     evidence-based variant disambiguation (Pillar 1)
  POST /api/estimate            honest, explainable estimate (Pillars 2 & 3)

Also serves the vanilla frontend at / so the whole product runs from one process.
Run via backend/run.py (which wires sys.path). Free stack only: FastAPI + Uvicorn.
"""

from __future__ import annotations
import os
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from catalog import CATALOG, get_model, FEATURE_QUESTIONS
from features import CATEGORY_VALUES
import variant_resolver
import pricing
import condition as cond
import evidence as ev
import smart_assist
import config

app = FastAPI(title="TruePrice API",
              description="Variant-aware, condition-honest, confidence-scored used-car "
                          "estimates for Cars24 sellers.",
              version="1.0.0")

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")


# ---- Schemas --------------------------------------------------------------------------
class ResolveRequest(BaseModel):
    make: str
    model: str
    fuel: str = "petrol"
    transmission: str = "manual"
    answers: Dict[str, object] = Field(default_factory=dict)


class CarInput(BaseModel):
    make: str
    model: str
    variant: str
    fuel: str = "petrol"
    transmission: str = "manual"
    age: int = Field(ge=0, le=25)
    km: int = Field(ge=0, le=500000)
    owners: int = Field(ge=1, le=6)
    # condition disclosures (optional; default to best-case with 'unknown' allowed)
    accident: str = "none"
    aftermarket_cng: str = "no"
    service_records: str = "full"
    tyres: str = "good"
    insurance: str = "comprehensive"
    city_tier: str = "metro"
    color: str = "neutral"
    # optional signals from the resolver step
    variant_confidence: float = 1.0
    variant_price_spread: float = 0.0
    # optional signal from the guided-inspection evidence pack (0-1)
    evidence_strength: float = 0.0


# ---- Routes ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok", "model_metrics": pricing._bundle()["metrics"]}


@app.get("/api/catalog")
def catalog():
    out = []
    for m in CATALOG:
        out.append({
            "make": m.make, "model": m.model, "segment": m.segment,
            "fuels": m.fuels, "transmissions": m.transmissions,
            "variants": [{"name": v.name, "trim_rank": v.trim_rank,
                          "price_new": v.price_new} for v in m.variants],
        })
    # Expose condition disclosures from the single source of truth so the UI can't drift.
    disclosures = []
    for field, spec in cond.DISCLOSURES.items():
        disclosures.append({
            "field": field,
            "question": spec["question"],
            "why_it_matters": spec["why_it_matters"],
            "options": [{"value": val, "label": opt["label"]}
                        for val, opt in spec["options"].items()],
        })
    # Expose the variant feature questions so the camera flow can confirm what it captured.
    feature_questions = []
    for feat, spec in FEATURE_QUESTIONS.items():
        feature_questions.append({
            "feature": feat, "question": spec["question"],
            "options": [{"value": val, "label": lbl}
                        for val, lbl in spec["options"].items()],
        })
    return {"models": out, "category_values": CATEGORY_VALUES,
            "disclosures": disclosures, "feature_questions": feature_questions}


class EvidencePack(BaseModel):
    points: List[Dict[str, object]] = Field(default_factory=list)


@app.post("/api/evidence/score")
def evidence_score(pack: EvidencePack):
    return ev.score(pack.points)


@app.get("/api/smart-assist/status")
def smart_assist_status():
    # Lets the UI show the opt-in toggle only when a Gemini key is configured.
    # Cheap/instant — does NOT call Gemini. Use /health for a real reachability probe.
    return {"enabled": config.smart_assist_enabled(),
            "model": config.GEMINI_MODEL if config.smart_assist_enabled() else None}


@app.get("/api/smart-assist/health")
def smart_assist_health():
    # Makes one real call to Gemini so the UI can show the TRUE state:
    # disabled (no key) / ready / quota_exhausted / invalid_key / error.
    # Called on demand (when the user opts in), not on every page load.
    return smart_assist.health()


class SmartAssistRequest(BaseModel):
    point_id: str
    image: str                 # base64 JPEG (no data: prefix)
    make: str = ""
    model: str = ""


@app.post("/api/smart-assist/analyze")
def smart_assist_analyze(req: SmartAssistRequest):
    # Strip a data-URL prefix if the client sent one.
    img = req.image.split(",", 1)[-1] if req.image.startswith("data:") else req.image
    return smart_assist.analyze(req.point_id, img, req.make, req.model)


@app.post("/api/variant/resolve")
def resolve(req: ResolveRequest):
    try:
        return variant_resolver.resolve(
            req.make, req.model, req.answers, req.fuel, req.transmission)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/estimate")
def estimate(car: CarInput):
    m = get_model(car.make, car.model)
    if not m:
        raise HTTPException(status_code=400, detail=f"Unknown model {car.make} {car.model}")
    car_dict = car.model_dump()
    disclosures = {k: car_dict[k] for k in
                   ["accident", "aftermarket_cng", "service_records", "tyres", "insurance"]}
    try:
        result = pricing.estimate(
            car_dict, segment=m.segment,
            variant_confidence=car.variant_confidence,
            variant_price_spread=car.variant_price_spread,
            disclosures=disclosures,
            evidence_strength=car.evidence_strength,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    result["input_echo"] = {"make": car.make, "model": car.model, "variant": car.variant}
    return result


# ---- Static frontend (mounted last so /api/* wins) ------------------------------------
@app.get("/")
def index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")
