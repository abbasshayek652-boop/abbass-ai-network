from __future__ import annotations

import asyncio
import datetime as dt
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, select

from db.models import AgentEvent
from db.session import engine
from gateway_pkg.auth import AuthContext, get_viewer
from gateway_pkg.guards import circuit_breaker


router = APIRouter()


async def status_payload(app) -> dict[str, Any]:
    agents = getattr(app.state, "agents", {}) or {}
    keys = list(agents.keys())
    statuses = await asyncio.gather(*(agents[key].status() for key in keys)) if keys else []
    running = {key: agents[key].running for key in keys}
    return {
        "loaded_agents": keys,
        "running": running,
        "agents": {key: status for key, status in zip(keys, statuses)},
        "circuit_breaker": circuit_breaker.state(),
        "last_audit_ts": getattr(app.state, "last_audit_ts", None),
    }


def _db_ready() -> bool:
    try:
        with Session(engine) as session:
            session.exec(select(AgentEvent))
        return True
    except Exception:  # noqa: BLE001
        return False


@router.get("/healthz")
async def healthz() -> dict[str, object]:
    return {
        "ok": True,
        "service": "mother_ai",
        "timestamp": f"{dt.datetime.utcnow().isoformat()}Z",
    }


@router.get("/readyz")
async def readyz(request: Request) -> dict[str, object]:
    db_ok = _db_ready()
    registry_ok = getattr(request.app.state, "registry", None) is not None
    agents_ok = getattr(request.app.state, "agents", None) is not None
    app_ready = bool(getattr(request.app.state, "ready", False))
    ready = all([db_ok, registry_ok, agents_ok, app_ready])
    return {
        "ready": ready,
        "db": db_ok,
        "registry": registry_ok,
        "agents": agents_ok,
    }


@router.get("/status")
async def status_endpoint(request: Request, _: AuthContext = Depends(get_viewer)) -> dict[str, Any]:
    return await status_payload(request.app)

