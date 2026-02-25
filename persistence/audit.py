from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Optional

from sqlmodel import Field, Session, SQLModel, create_engine
from sqlmodel.engine import Engine


class AuditRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: float = Field(default_factory=lambda: time.time())
    user_id: str
    role: str
    action: str
    agent_key: str | None
    ip: str | None
    correlation_id: str
    ok: bool
    details_json: str | None


@dataclass(slots=True)
class AuditEvent:
    user_id: str
    role: str
    action: str
    agent_key: str | None
    ip: str | None
    correlation_id: str
    ok: bool
    details: dict[str, object] | None = None
    ts: float = field(default_factory=lambda: time.time())


_ENGINE: Engine | None = None


def configure_engine(engine: Engine) -> None:
    global _ENGINE
    _ENGINE = engine
    SQLModel.metadata.create_all(engine)


def _get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_engine(
            "sqlite:///mother_audit.db",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        SQLModel.metadata.create_all(_ENGINE)
    return _ENGINE


def write_audit(event: AuditEvent) -> None:
    payload = AuditRecord(
        ts=event.ts,
        user_id=event.user_id,
        role=event.role,
        action=event.action,
        agent_key=event.agent_key,
        ip=event.ip,
        correlation_id=event.correlation_id,
        ok=event.ok,
        details_json=json.dumps(event.details or {}),
    )
    engine = _get_engine()
    with Session(engine) as session:
        session.add(payload)
        session.commit()
