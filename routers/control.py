from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

from ai.settings import settings
from db.models import AgentEvent
from db.session import engine
from gateway_pkg.auth import AuthContext, get_operator
from gateway_pkg.guards import circuit_breaker, idempotency_cache, limiter
from gateway_pkg.metrics import record_agent_action, record_gateway_error, set_agent_state
from persistence.audit import AuditEvent, write_audit
from sqlmodel import Session


router = APIRouter()


class Command(BaseModel):
    agent_key: str


class N8nWebhook(BaseModel):
    action: str
    agent_key: str
    meta: dict[str, Any] = {}


def _audit(
    request: Request,
    ctx: AuthContext,
    action: str,
    agent_key: str | None,
    ok: bool,
    details: dict[str, Any],
) -> None:
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
    request.app.state.last_audit_ts = event.ts


def _log_agent_event(event_type: str, agent_key: str | None, payload: dict[str, Any]) -> None:
    event = AgentEvent(agent_key=agent_key, event_type=event_type, payload=payload)
    with Session(engine) as session:
        session.add(event)
        session.commit()


@router.post("/start")
@limiter.limit("5/minute")
async def start_agent(cmd: Command, request: Request, ctx: AuthContext = Depends(get_operator)) -> dict[str, Any]:
    supervisor = getattr(request.app.state, "supervisor", None)
    agents = getattr(request.app.state, "agents", None) or {}
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


@router.post("/stop")
@limiter.limit("5/minute")
async def stop_agent(cmd: Command, request: Request, ctx: AuthContext = Depends(get_operator)) -> dict[str, Any]:
    supervisor = getattr(request.app.state, "supervisor", None)
    agents = getattr(request.app.state, "agents", None) or {}
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


@router.post("/webhooks/n8n")
async def n8n_webhook(
    payload: N8nWebhook,
    request: Request,
    x_webhook_token: str | None = Header(default=None),
) -> dict[str, Any]:
    expected = settings.webhook_token
    if not expected or not x_webhook_token or x_webhook_token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook token")
    _log_agent_event("n8n_webhook", payload.agent_key, {"action": payload.action, "meta": payload.meta})
    if payload.action == "start":
        ctx = AuthContext(user_id="webhook", role="admin")
        result = await start_agent(Command(agent_key=payload.agent_key), request, ctx)
        return {"ok": True, "result": result}
    if payload.action == "stop":
        ctx = AuthContext(user_id="webhook", role="admin")
        result = await stop_agent(Command(agent_key=payload.agent_key), request, ctx)
        return {"ok": True, "result": result}
    if payload.action == "status":
        agents = getattr(request.app.state, "agents", None) or {}
        if payload.agent_key not in agents:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown agent")
        status_payload = await agents[payload.agent_key].status()
        return {"ok": True, "status": status_payload}
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown action")

