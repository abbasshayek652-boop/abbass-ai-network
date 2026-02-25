from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Request
from sqlmodel import Session, select

from db.models import AgentEvent
from db.session import engine
from routers.agents import _agent_summary
from routers.core import healthz, readyz

router = APIRouter()


@router.get("/console/agents")
async def console_agents(request: Request) -> dict[str, Any]:
    return {"agents": _agent_summary(request)}


@router.get("/console/health")
async def console_health(request: Request) -> dict[str, Any]:
    health = await healthz()
    ready = await readyz(request)
    started_at = getattr(request.app.state, "started_at", None)
    uptime = time.time() - started_at if started_at else None
    version = getattr(request.app, "version", None) or getattr(request.app.state, "version", None)
    return {
        "health": health,
        "ready": ready,
        "version": version,
        "uptime_seconds": uptime,
    }


@router.get("/console/events")
async def console_events(limit: int = 200) -> dict[str, Any]:
    limit = max(1, min(500, int(limit)))
    with Session(engine) as session:
        rows = session.exec(select(AgentEvent)).all()
    rows.sort(key=lambda row: row.ts, reverse=True)
    payload = [
        {
            "id": row.id,
            "ts": row.ts.isoformat() if hasattr(row.ts, "isoformat") else row.ts,
            "agent_key": row.agent_key,
            "event_type": row.event_type,
            "payload": row.payload,
        }
        for row in rows[:limit]
    ]
    return {"events": payload}
