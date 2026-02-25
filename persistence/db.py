from __future__ import annotations

import time
from typing import Optional

from sqlmodel import Field, Session, SQLModel, create_engine


class AuditEvent(SQLModel, table=True):
    level: str
    agent: str
    event: str
    details: str
    ts: float = Field(default_factory=lambda: time.time())
    id: Optional[int] = Field(default=None, primary_key=True)


class Trade(SQLModel, table=True):
    ts: float
    symbol: str
    side: str
    qty: float
    price: float
    fee: float
    order_id: str
    paper: bool
    id: Optional[int] = Field(default=None, primary_key=True)


class AuditKV(SQLModel, table=True):
    key: str
    payload_json: str
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: float = Field(default_factory=lambda: time.time())


def init_db(url: str = "sqlite:///mother_trades.db"):
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, echo=False, connect_args=connect_args)
    SQLModel.metadata.create_all(engine)
    return engine


def add_audit(engine, level: str, agent: str, event: str, details: str) -> None:
    with Session(engine) as session:
        session.add(
            AuditEvent(level=level, agent=agent, event=event, details=details)
        )
        session.commit()


def add_trade(engine, **kwargs) -> None:
    with Session(engine) as session:
        session.add(Trade(**kwargs))
        session.commit()


def add_kv(engine, key: str, payload_json: str) -> None:
    with Session(engine) as session:
        session.add(AuditKV(key=key, payload_json=payload_json))
        session.commit()
