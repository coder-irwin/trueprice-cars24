"""
train.py — trains the TruePrice quantile pricing model.

We train THREE gradient-boosted models for the P10 / P50 / P90 quantiles of the final
auction price. The median (P50) is our point estimate; the P10–P90 spread is our honest
range. Training quantiles directly (rather than faking a symmetric ± band) means the
range width reflects genuine, data-driven uncertainty — which is the whole point of an
honest estimate (docs/00-research.md §4).

Artifacts are saved to model/pricing_model.joblib and consumed by the backend.

Run:  .venv/bin/python model/train.py
"""

from __future__ import annotations
import os
import numpy as np
import pandas as pd
from joblib import dump
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import train_test_split

from features import NUMERIC_FEATURES, CATEGORICAL_FEATURES, FEATURE_COLUMNS, TARGET

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "used_cars.csv")
OUT = os.path.join(HERE, "pricing_model.joblib")

QUANTILES = {"p10": 0.10, "p50": 0.50, "p90": 0.90}


def make_pipeline(quantile: float) -> Pipeline:
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ("num", "passthrough", NUMERIC_FEATURES),
    ])
    model = HistGradientBoostingRegressor(
        loss="quantile", quantile=quantile,
        max_iter=400, learning_rate=0.05, max_depth=6,
        min_samples_leaf=40, l2_regularization=1.0, random_state=7,
    )
    return Pipeline([("pre", pre), ("gb", model)])


def mape(y_true, y_pred) -> float:
    return float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100)


def main():
    df = pd.read_csv(DATA)
    X = df[FEATURE_COLUMNS]
    y = df[TARGET].values

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=7)

    models = {}
    preds_te = {}
    for name, q in QUANTILES.items():
        pipe = make_pipeline(q)
        pipe.fit(X_tr, y_tr)
        models[name] = pipe
        preds_te[name] = pipe.predict(X_te)

    # Enforce monotonic quantiles (guard against occasional crossing).
    p10 = np.minimum.reduce([preds_te["p10"], preds_te["p50"], preds_te["p90"]])
    p90 = np.maximum.reduce([preds_te["p10"], preds_te["p50"], preds_te["p90"]])
    p50 = np.clip(preds_te["p50"], p10, p90)

    # ---- Honest evaluation --------------------------------------------------------
    point_mape = mape(y_te, p50)
    coverage = float(np.mean((y_te >= p10) & (y_te <= p90)) * 100)
    avg_width_pct = float(np.mean((p90 - p10) / p50) * 100)

    print("=" * 60)
    print("TruePrice model — held-out evaluation (20% test)")
    print("=" * 60)
    print(f"  Test rows            : {len(y_te):,}")
    print(f"  Point (P50) MAPE     : {point_mape:.2f}%   (lower is better)")
    print(f"  P10–P90 coverage     : {coverage:.1f}%    (target ≈ 80%)")
    print(f"  Avg range width      : {avg_width_pct:.1f}% of the point estimate")
    print("=" * 60)

    dump({"models": models, "quantiles": QUANTILES,
          "metrics": {"point_mape": point_mape, "coverage_p10_p90": coverage,
                      "avg_width_pct": avg_width_pct, "test_rows": int(len(y_te))}},
         OUT)
    print(f"Saved -> {os.path.relpath(OUT, HERE)}")


if __name__ == "__main__":
    main()
