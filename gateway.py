from __future__ import annotations

import asyncio
import logging
import pathlib
import uuid
from collections import deque
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from ai.registry import Registry, hydrate_agents, load_registry
from ai.settings import settings
from ai.supervisor import Supervisor
from ai.utils.logging import setup_logging
from dashboard import ws as dashboard_ws
from gateway.auth import AuthContext, Role, get_admin, get_operator, get_viewer, issue_jwt
from gateway.guards import circuit_breaker, idempotency_cache, limiter
from gateway.metrics import metrics_app, record_agent_action, record_gateway_error, set_agent_state
from gateway.middleware import CorrelationIdMiddleware
from persistence.audit import AuditEvent, write_audit
from services.scheduler import build_scheduler
from telegram.notify import notify_alert
from agents.linkedin_agent.router import router as linkedin_router
from agents.linkedin_agent.scheduler import start_scheduler as start_linkedin_scheduler

setup_logging(settings.log_level)
LOGGER = logging.getLogger("gateway")

app = FastAPI(title="Mother AI Gateway", version="2.0.0")
app.state.ready = False

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(SlowAPIMiddleware, limiter=limiter)

if settings.dashboard_origin:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.dashboard_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

BASE_DIR = pathlib.Path(__file__).resolve().parent

app.mount("/dashboard", StaticFiles(directory=BASE_DIR / "dashboard", html=True), name="dashboard")
app.mount("/metrics", metrics_app())
app.include_router(dashboard_ws.router)
app.include_router(linkedin_router)

registry: Registry | None = None
agents: dict[str, Any] = {}
supervisor: Supervisor | None = None
_scheduler = None
_last_audit_ts: float | None = None


class Command(BaseModel):
    agent_key: str


class LoginRequest(BaseModel):
    email: str
    role: Role


class LoginResponse(BaseModel):
    token: str


async def _status_payload() -> dict[str, Any]:
    keys = list(agents.keys())
    statuses = await asyncio.gather(*(agents[key].status() for key in keys))
    return {
        "agents": {key: status for key, status in zip(keys, statuses)},
        "circuit_breaker": circuit_breaker.state(),
        "last_audit_ts": _last_audit_ts,
    }


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


@app.on_event("startup")
async def on_startup() -> None:
    global _scheduler, registry, agents, supervisor
    registry = load_registry()
    agents = hydrate_agents(registry)
    supervisor = Supervisor(agents)
    dashboard_ws.configure(_status_payload)
    for key, agent in agents.items():
        set_agent_state(key, agent.running)
    scheduler = build_scheduler(_status_payload, notify_alert)
    scheduler.start()
    _scheduler = scheduler
    start_linkedin_scheduler(app)
    app.state.ready = True
    LOGGER.info("Gateway ready with %s agents", len(agents))


@app.on_event("shutdown")
async def on_shutdown() -> None:
    LOGGER.info("Gateway shutdown requested")
    if supervisor is not None:
        await supervisor.stop_all()
    scheduler = getattr(app.state, "linkedin_scheduler", None)
    if scheduler is not None:
        await scheduler.stop()


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:  # type: ignore[override]
    record_gateway_error(request.url.path)
    return JSONResponse(status_code=status.HTTP_429_TOO_MANY_REQUESTS, content={"detail": "Rate limit exceeded"})


@app.post("/auth/login", response_model=LoginResponse)
async def login(request: Request, payload: LoginRequest, x_api_key: str | None = Header(default=None)) -> LoginResponse:
    if settings.api_key is None or x_api_key is None or x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    token = issue_jwt(payload.email, payload.role)
    LOGGER.info("login", extra={"email": payload.email, "role": payload.role})
    return LoginResponse(token=token)


def _audit(request: Request, ctx: AuthContext, action: str, agent_key: str | None, ok: bool, details: dict[str, Any]) -> None:
    global _last_audit_ts
    ip = request.client.host if request.client else None
    event = AuditEvent(
        user_id=ctx.user_id,
        role=ctx.role,
        action=action,
        agent_key=agent_key,
        ip=ip,
        correlation_id=getattr(request.state, "correlation_id", str(uuid.uuid4())),
        ok=ok,
        details=details,
    )
    write_audit(event)
    _last_audit_ts = event.ts


@app.post("/start")
@limiter.limit("5/minute")
async def start_agent(cmd: Command, request: Request, ctx: AuthContext = Depends(get_operator)) -> dict[str, Any]:
    if supervisor is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supervisor not ready")
    if not circuit_breaker.allow():
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Control circuit open")
    if cmd.agent_key not in agents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown agent")
    if not idempotency_cache.allow(f"start:{cmd.agent_key}"):
        _audit(request, ctx, "start", cmd.agent_key, True, {"duplicate": True})
        return {"ok": True, "duplicate": True}
    ok = False
    try:
        await supervisor.start(cmd.agent_key)
        set_agent_state(cmd.agent_key, True)
        ok = True
        record_agent_action(cmd.agent_key, "start", ctx.role)
        circuit_breaker.record_success()
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        circuit_breaker.record_error(str(exc))
        record_gateway_error("/start")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to start agent") from exc
    finally:
        _audit(request, ctx, "start", cmd.agent_key, ok, {})


@app.post("/stop")
@limiter.limit("5/minute")
async def stop_agent(cmd: Command, request: Request, ctx: AuthContext = Depends(get_operator)) -> dict[str, Any]:
    if supervisor is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supervisor not ready")
    if not circuit_breaker.allow():
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Control circuit open")
    if cmd.agent_key not in agents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown agent")
    if not idempotency_cache.allow(f"stop:{cmd.agent_key}"):
        _audit(request, ctx, "stop", cmd.agent_key, True, {"duplicate": True})
        return {"ok": True, "duplicate": True}
    ok = False
    try:
        await supervisor.stop(cmd.agent_key)
        set_agent_state(cmd.agent_key, False)
        ok = True
        record_agent_action(cmd.agent_key, "stop", ctx.role)
        circuit_breaker.record_success()
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        circuit_breaker.record_error(str(exc))
        record_gateway_error("/stop")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to stop agent") from exc
    finally:
        _audit(request, ctx, "stop", cmd.agent_key, ok, {})


@app.get("/status")
async def status_endpoint(_: AuthContext = Depends(get_viewer)) -> dict[str, Any]:
    return await _status_payload()


@app.get("/logs/{agent_key}")
@limiter.limit("5/minute")
async def agent_logs(agent_key: str, _: AuthContext = Depends(get_viewer)) -> Response:
    if agent_key not in agents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown agent")
    content = _read_logs(agent_key)
    return Response(content=content, media_type="text/plain")


@app.post("/registry/validate")
async def registry_validate(request: Request, _: AuthContext = Depends(get_admin)) -> dict[str, Any]:
    payload = await request.json()
    try:
        Registry(**payload)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"ok": True}


@app.post("/registry/dryrun")
async def registry_dryrun(request: Request, _: AuthContext = Depends(get_admin)) -> dict[str, Any]:
    payload = await request.json()
    registry = Registry(**payload)
    instances = hydrate_agents(registry)
    summary = {key: instance.__class__.__name__ for key, instance in instances.items()}
    return {"ok": True, "agents": summary}


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, bool]:
    return {"ready": bool(app.state.ready)}


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse("dashboard/index.html")
