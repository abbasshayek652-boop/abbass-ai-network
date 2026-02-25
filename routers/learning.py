from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlmodel import Session

from db.models import AgentEvent
from db.session import engine
from gateway.auth import AuthContext, get_operator


router = APIRouter()


class LearningEventRequest(BaseModel):
    agent_key: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


def _log_event(event_type: str, payload: LearningEventRequest) -> int | None:
    event = AgentEvent(agent_key=payload.agent_key, event_type=event_type, payload=payload.payload)
    with Session(engine) as session:
        session.add(event)
        session.commit()
    return event.id


@router.post("/learning/train")
async def learning_train(payload: LearningEventRequest, _: AuthContext = Depends(get_operator)) -> dict[str, Any]:
    event_id = _log_event("learning_train", payload)
    return {"ok": True, "event_id": event_id}


@router.post("/learning/promote")
async def learning_promote(payload: LearningEventRequest, _: AuthContext = Depends(get_operator)) -> dict[str, Any]:
    event_id = _log_event("learning_promote", payload)
    return {"ok": True, "event_id": event_id}
