from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException

from learning.data_schema import ensure_engine
from learning.features.offline import build_offline_dataset, dataset_hash
from learning.models.supervised import SupervisedResult, train_classifier
from learning.policy import registry
from learning.policy.rollout import promote
from telemetry.learning_metrics import learning_train_runs_total

DEFAULT_DB = os.getenv("MOTHER_LEARNING_DB", "sqlite:///mother_learning.db")


@dataclass
class _LearningState:
    engine: Any
    model: Optional[SupervisedResult] = None
    last_train_ts: float = 0.0


state = _LearningState(engine=ensure_engine(DEFAULT_DB))
app = FastAPI(title="Learning API", version="1.0.0")


@app.post("/learning/train")
async def train(payload: Dict[str, Any]) -> Dict[str, Any]:
    symbol = payload.get("symbol", "BTC/USDT")
    dataset = build_offline_dataset(state.engine, symbol)
    if not dataset:
        raise HTTPException(status_code=400, detail="no data")
    result = train_classifier(dataset, "label")
    state.model = result
    state.last_train_ts = time.time()
    learning_train_runs_total.labels("shadow").inc()
    return {"metrics": result.metrics, "dataset_hash": dataset_hash(dataset)}


@app.get("/learning/policy/latest")
async def policy_latest(stage: str = "shadow") -> Dict[str, Any]:
    policy = registry.latest_policy(state.engine, stage)
    if not policy:
        raise HTTPException(status_code=404, detail="no policy")
    return {"version": policy.version, "stage": policy.stage, "payload": json.loads(policy.payload_json)}


@app.post("/learning/policy/promote")
async def policy_promote(payload: Dict[str, Any]) -> Dict[str, Any]:
    policy_id = int(payload["policy_id"])
    to_stage = payload.get("to_stage", "canary")
    thresholds = payload.get("thresholds", {})
    result = promote(state.engine, policy_id, to_stage, thresholds)
    if not result.ok:
        raise HTTPException(status_code=400, detail=result.reason)
    return {"ok": True, "new_stage": result.new_stage}


@app.post("/learning/score")
async def score(payload: Dict[str, Any]) -> Dict[str, Any]:
    if state.model is None:
        raise HTTPException(status_code=400, detail="model_not_trained")
    symbol = payload.get("symbol", "BTC/USDT")
    features = payload.get("features", {})
    df = state.model.model.columns  # type: ignore[attr-defined]
    # Build DataFrame manually to avoid pandas dependency in scoring path
    score_val = state.model.model.bias  # type: ignore[attr-defined]
    for col, weight in zip(df, state.model.model.weights):  # type: ignore[attr-defined]
        score_val += float(features.get(col, 0.0)) * weight
    prob = 1 / (1 + math.exp(-score_val))
    return {"symbol": symbol, "probability": float(prob)}


@app.get("/learning/metrics")
async def learning_metrics() -> Dict[str, Any]:
    return {"last_train_ts": state.last_train_ts, "model_ready": state.model is not None}
