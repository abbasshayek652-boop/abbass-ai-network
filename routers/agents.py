from __future__ import annotations

import pathlib
from collections import deque
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import ValidationError

from ai.registry import Registry, hydrate_agents
from gateway.auth import AuthContext, get_admin, get_viewer


router = APIRouter()


def _log_path(agent_key: str) -> pathlib.Path:
    return pathlib.Path("logs") / f"{agent_key}.log"


def _read_logs(agent_key: str, limit: int = 2000) -> str:
    path = _log_path(agent_key)
    if not path.exists():
        return ""
    lines: deque[str] = deque(maxlen=limit)
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            lines.append(line.rstrip())
    return "\n".join(lines)


@router.get("/logs/{agent_key}")
async def agent_logs(agent_key: str, request: Request, _: AuthContext = Depends(get_viewer)) -> Response:
    agents = getattr(request.app.state, "agents", None) or {}
    if agent_key not in agents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown agent")
    content = _read_logs(agent_key)
    return Response(content=content, media_type="text/plain")


@router.post("/registry/validate")
async def registry_validate(request: Request, _: AuthContext = Depends(get_admin)) -> dict[str, Any]:
    payload = await request.json()
    try:
        Registry(**payload)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/registry/dryrun")
async def registry_dryrun(request: Request, _: AuthContext = Depends(get_admin)) -> dict[str, Any]:
    payload = await request.json()
    registry = Registry(**payload)
    instances = hydrate_agents(registry)
    summary = {key: instance.__class__.__name__ for key, instance in instances.items()}
    return {"ok": True, "agents": summary}
