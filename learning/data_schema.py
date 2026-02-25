from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Dict, Optional

from sqlmodel import Field, SQLModel, create_engine

try:  # pragma: no cover - optional dependency
    import orjson
except Exception:  # pragma: no cover - fallback when orjson unavailable
    import json as orjson  # type: ignore


def _dumps(data: Dict[str, object]) -> str:
    payload = orjson.dumps(data)
    if isinstance(payload, bytes):
        return payload.decode()
    return payload


def _hash_payload(data: Dict[str, object]) -> str:
    payload = _dumps(data)
    return hashlib.sha256(payload.encode() if isinstance(payload, str) else payload).hexdigest()


class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: float = Field(default_factory=lambda: time.time())
    agent: str
    kind: str
    payload_json: str = Field(default="{}")


class Trade(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: float
    agent: str
    symbol: str
    side: str
    qty: float
    price: float
    pnl: float = 0.0
    paper: bool = True
    policy_id: Optional[str] = None


class MarketSnapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: float
    symbol: str
    price: float
    volume: float
    features_json: str = Field(default="{}")


class QCIssue(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: float
    agent: str
    symbol: str
    reason: str


class FeatureView(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    as_of_ts: float
    data_json: str
    data_hash: str


class ModelRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    started_ts: float
    completed_ts: float
    model_type: str
    target: str
    metrics_json: str
    params_json: str
    dataset_hash: str


class Policy(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_ts: float = Field(default_factory=lambda: time.time())
    version: int
    stage: str
    payload_json: str
    payload_hash: str
    parent_id: Optional[int] = None
    description: str = ""


class PolicyMetric(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    policy_id: int
    metric_name: str
    metric_value: float


class Advice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: float = Field(default_factory=lambda: time.time())
    agent: str
    symbol: str
    target: str
    payload_json: str
    policy_id: Optional[int] = None


class LearningSnapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_ts: float = Field(default_factory=lambda: time.time())
    payload_json: str


@dataclass
class LearningState:
    last_event_ts: float = 0.0
    last_train_ts: float = 0.0
    last_eval_ts: float = 0.0
    active_policy_version: Optional[int] = None


def ensure_engine(url: str):
    engine = create_engine(url)
    SQLModel.metadata.create_all(engine)
    return engine


def dumps_payload(data: Dict[str, object]) -> str:
    return _dumps(data)


def hash_payload(data: Dict[str, object]) -> str:
    return _hash_payload(data)
