from __future__ import annotations

import datetime as dt
from typing import Any, Optional

from sqlmodel import Field, SQLModel


class AgentEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: dt.datetime = Field(default_factory=dt.datetime.utcnow)
    agent_key: Optional[str] = None
    event_type: str
    payload: Optional[dict[str, Any]] = None


class Trade(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: dt.datetime = Field(default_factory=dt.datetime.utcnow)
    agent_key: Optional[str] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    qty: Optional[float] = None
    price: Optional[float] = None
    meta: Optional[dict[str, Any]] = None


class StrategyResult(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: dt.datetime = Field(default_factory=dt.datetime.utcnow)
    strategy_name: str
    success: bool = Field(default=False)
    metrics: Optional[dict[str, Any]] = None


class ContentDraft(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: dt.datetime = Field(default_factory=dt.datetime.utcnow)
    agent_key: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    status: str = Field(default="draft")
    meta: Optional[dict[str, Any]] = None
