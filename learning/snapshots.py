from __future__ import annotations

from typing import Dict, Optional

from sqlmodel import Session, select

from learning.data_schema import LearningSnapshot, dumps_payload


def save_snapshot(engine, payload: Dict[str, object]) -> LearningSnapshot:
    snap = LearningSnapshot(payload_json=dumps_payload(payload))
    with Session(engine) as session:
        session.add(snap)
        session.commit()
    return snap


def load_snapshot(engine) -> Optional[Dict[str, object]]:
    with Session(engine) as session:
        snaps = session.exec(select(LearningSnapshot)).all()
    if not snaps:
        return None
    snaps.sort(key=lambda s: s.created_ts)
    payload = snaps[-1].payload_json
    try:
        import orjson

        return orjson.loads(payload)
    except Exception:
        import json

        return json.loads(payload)
