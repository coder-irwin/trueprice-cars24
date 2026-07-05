# 07 · Runbook

Operational guide: run it, rebuild it, troubleshoot it. Everything free & local.

## Prerequisites
- Python 3 (tested on 3.14) and a POSIX shell. Node is optional (only for `node --check`).

## One-time setup
```bash
cd cars24_project
python3 -m venv .venv
.venv/bin/python -m pip install -U pip numpy scikit-learn pandas joblib "fastapi" "uvicorn[standard]"
```

## Build the model artifacts (required before first run)
```bash
.venv/bin/python model/generate_data.py --rows 24000   # -> data/used_cars.csv
.venv/bin/python model/train.py                        # -> model/pricing_model.joblib
```

## Run the product
```bash
.venv/bin/python backend/run.py            # http://127.0.0.1:8000  (Ctrl-C to stop)
# override host/port:
HOST=0.0.0.0 PORT=9000 .venv/bin/python backend/run.py
```
Open the URL and walk the wizard. API docs at `/docs`.

## Verify
```bash
.venv/bin/python tests/test_core.py    # 11 unit tests (the honesty invariants)
.venv/bin/python tests/backtest.py     # below-floor-rate: old vs TruePrice (~1–2 min)
curl -s http://127.0.0.1:8000/api/health   # liveness + model metrics
```

## Common tasks
- **Retrain after changing the DGP or catalog:** rerun `generate_data.py` then `train.py`.
- **Add a car model:** edit `model/catalog.py` (one place); regenerate data + retrain.
- **Add a pricing feature:** add it to `model/features.py` once; regenerate + retrain.

## Troubleshooting
| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: sklearn/pandas` | deps not in venv | rerun the pip install |
| `externally-managed-environment` on pip | using system Python | use `.venv/bin/python`, not system `python3` |
| `FileNotFoundError: pricing_model.joblib` | model not built | run `generate_data.py` then `train.py` |
| Server starts but `/` 404s | run from repo root | launch via `.venv/bin/python backend/run.py` |
| Port already in use | stale server | `pkill -f backend/run.py` then restart |
| Estimate feels slow | single-row predict overhead | already batched; ~200ms/estimate is expected locally |

## Notes
- Raw media for the camera/vision features is analyzed **client-side** and is not uploaded —
  only compact evidence summaries reach the API (see `docs/08-vision.md`).
- This is a demonstration MVP on synthetic data; do not treat rupee figures as market prices.
