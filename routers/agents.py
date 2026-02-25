from __future__ import annotations

import pathlib
from collections import deque
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import ValidationError

from ai.registry import Registry, hydrate_agents
from gateway_pkg.auth import AuthContext, get_admin, get_operator, get_viewer
from routers.control import Command, start_agent as control_start, stop_agent as control_stop


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

def _agent_specs(request: Request) -> dict[str, object]:
    registry = getattr(request.app.state, "registry", None)
    specs = {}
    if registry is None:
        return specs
    for spec in registry.agents:
        if hasattr(spec, "key"):
            specs[spec.key] = spec
        elif isinstance(spec, dict) and "key" in spec:
            specs[spec["key"]] = spec
    return specs


def _agent_summary(request: Request) -> list[dict[str, Any]]:
    agents = getattr(request.app.state, "agents", None) or {}
    specs = _agent_specs(request)
    keys = set(specs.keys()) | set(agents.keys())
    summary: list[dict[str, Any]] = []
    for key in sorted(keys):
        spec = specs.get(key)
        instance = agents.get(key)
        enabled = True
        if spec is not None:
            enabled = spec.get("enabled", True) if isinstance(spec, dict) else getattr(spec, "enabled", True)
        summary.append(
            {
                "key": key,
                "enabled": enabled,
                "running": bool(getattr(instance, "running", False)) if instance else False,
                "description": getattr(instance, "description", "") if instance else "",
            }
        )
    return summary


@router.get("/agents")
async def list_agents(request: Request, _: AuthContext = Depends(get_viewer)) -> dict[str, Any]:
    return {"agents": _agent_summary(request)}


@router.get("/agents/{agent_key}")
async def agent_detail(agent_key: str, request: Request, _: AuthContext = Depends(get_viewer)) -> dict[str, Any]:
    agents = getattr(request.app.state, "agents", None) or {}
    specs = _agent_specs(request)
    if agent_key not in agents and agent_key not in specs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown agent")
    spec = specs.get(agent_key)
    instance = agents.get(agent_key)
    detail = {
        "key": agent_key,
        "enabled": (spec.get("enabled", True) if isinstance(spec, dict) else getattr(spec, "enabled", True)) if spec else True,
        "running": bool(getattr(instance, "running", False)) if instance else False,
        "description": getattr(instance, "description", "") if instance else "",
        "module": (spec.get("module") if isinstance(spec, dict) else getattr(spec, "module", None)) if spec else None,
        "class_name": (spec.get("class_name") if isinstance(spec, dict) else getattr(spec, "class_name", None)) if spec else None,
        "config": (spec.get("config") if isinstance(spec, dict) else getattr(spec, "config", None)) if spec else None,
    }
    return {"agent": detail}


@router.post("/agents/{agent_key}/start")
async def agent_start(agent_key: str, request: Request, ctx: AuthContext = Depends(get_operator)) -> dict[str, Any]:
    return await control_start(Command(agent_key=agent_key), request, ctx)


@router.post("/agents/{agent_key}/stop")
async def agent_stop(agent_key: str, request: Request, ctx: AuthContext = Depends(get_operator)) -> dict[str, Any]:
    return await control_stop(Command(agent_key=agent_key), request, ctx)


@router.get("/agents/{agent_key}/status")
async def agent_status(agent_key: str, request: Request, _: AuthContext = Depends(get_viewer)) -> dict[str, Any]:
    agents = getattr(request.app.state, "agents", None) or {}
    if agent_key not in agents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown agent")
    payload = await agents[agent_key].status()
    return {"agent_key": agent_key, "status": payload}


@router.get("/agents/{agent_key}/logs")
async def agent_logs_tail(
    agent_key: str,
    request: Request,
    tail: int = 200,
    _: AuthContext = Depends(get_viewer),
) -> dict[str, Any]:
    agents = getattr(request.app.state, "agents", None) or {}
    if agent_key not in agents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown agent")
    tail = max(1, min(2000, int(tail)))
    content = _read_logs(agent_key, limit=tail)
    if not content:
        return {
            "agent_key": agent_key,
            "lines": [],
            "todo": "No log file found. Configure per-agent logging output.",
        }
    return {"agent_key": agent_key, "lines": content.splitlines()}


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

