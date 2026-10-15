"""Inference API for workshop triage (uvicorn aps_intel.service:app).

One request = one or more trucks' 170 anonymised readings; missing readings may be
null or omitted. The response gives the model score, the frozen decision
(inspect APS / no action) and, on request, the readings that pushed the score most.

Scope: the decision is a classification of the current readings under the official
cost matrix. It is not a prediction of when a failure will occur.
"""
from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from aps_intel.cost import COST_FN, COST_FP
from aps_intel.data import ROOT

MODEL_PATH = Path(os.environ.get("APS_MODEL_PATH", ROOT / "artifacts/model/aps_lightgbm.joblib"))
DECISION_PATH = Path(os.environ.get("APS_DECISION_PATH", ROOT / "reports/final/execution.json"))
MAX_RECORDS = 1000


class Truck(BaseModel):
    readings: dict[str, float | None] = Field(..., description="Feature name -> value; null or absent = missing")


class ScoreRequest(BaseModel):
    trucks: list[Truck] = Field(..., min_length=1, max_length=MAX_RECORDS)


@lru_cache(maxsize=1)
def bundle():
    model = joblib.load(MODEL_PATH)
    decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
    return dict(model=model, threshold=float(decision["threshold"]),
                features=list(model.steps[0][1].columns_) + ["cd_000"],
                sha256=hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest())


def _frame(trucks: list[Truck], features: list[str]) -> pd.DataFrame:
    unknown = sorted({k for t in trucks for k in t.readings} - set(features))
    if unknown:
        raise HTTPException(422, f"Unknown readings: {unknown[:10]}")
    rows = [{f: (t.readings.get(f) if t.readings.get(f) is not None else np.nan) for f in features} for t in trucks]
    return pd.DataFrame(rows, columns=features, dtype=float)


def _drivers(model, X: pd.DataFrame, k: int) -> list[list[dict]]:
    Z = model[:-1].transform(X)
    contrib = model[-1].booster_.predict(Z, pred_contrib=True)[:, :-1]
    names = np.asarray(Z.columns)
    out = []
    for row in contrib:
        top = np.argsort(-np.abs(row))[:k]
        out.append([dict(feature=str(names[i]), contribution=round(float(row[i]), 4)) for i in top])
    return out


app = FastAPI(title="APS workshop triage", version="1.0.0")


@app.get("/health")
def health():
    b = bundle()
    return dict(status="ok", model_sha256=b["sha256"], threshold=b["threshold"],
                cost_false_alarm=COST_FP, cost_missed_failure=COST_FN, n_features=len(b["features"]))


@app.post("/score")
def score(request: ScoreRequest, explain: int = 0):
    b = bundle()
    X = _frame(request.trucks, b["features"])
    p = b["model"].predict_proba(X)[:, 1]
    drivers = _drivers(b["model"], X, explain) if explain > 0 else [None] * len(p)
    return dict(threshold=b["threshold"], results=[
        dict(score=round(float(s), 6), decision="inspect_aps" if s >= b["threshold"] else "no_action",
             missing_readings=int(X.iloc[i].isna().sum()), drivers=drivers[i])
        for i, s in enumerate(p)])
