from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

from sqlmodel import Field, Session, SQLModel, select


class Snapshot(SQLModel, table=True):
    agent: str
    payload: str
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: float = Field(default_factory=lambda: time.time())


def write_snapshot(engine, agent: str, payload: Dict[str, Any]) -> None:
    SQLModel.metadata.create_all(engine)
    data = json.dumps(payload)
    with Session(engine) as session:
        session.add(Snapshot(agent=agent, payload=data))
        session.commit()


def load_latest_snapshot(engine, agent: str) -> Dict[str, Any] | None:
    with Session(engine) as session:
        rows = session.exec(select(Snapshot)).all()
        filtered = [row for row in rows if row.agent == agent]
        if not filtered:
            return None
        filtered.sort(key=lambda item: item.ts, reverse=True)
        return json.loads(filtered[0].payload)

