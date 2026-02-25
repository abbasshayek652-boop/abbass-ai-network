from __future__ import annotations

import logging
import pathlib

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from agents.linkedin_agent.router import router as linkedin_router
from agents.linkedin_agent.scheduler import start_scheduler as start_linkedin_scheduler
from ai.registry import hydrate_agents, load_registry
from ai.settings import settings
from ai.supervisor import Supervisor
from ai.utils.logging import setup_logging
from dashboard import ws as dashboard_ws
from db.session import init_db
from gateway.auth import Role, issue_jwt
from gateway.guards import limiter
from gateway.metrics import metrics_app, record_gateway_error, set_agent_state
from gateway.middleware import CorrelationIdMiddleware
from routers import (
    agents_router,
    console_router,
    control_router,
    core_router,
    learning_router,
    planner_router,
    wallet_router,
)
from routers.core import status_payload
from services.scheduler import build_scheduler
from telegram.notify import notify_alert

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
app.include_router(core_router)
app.include_router(control_router)
app.include_router(agents_router)
app.include_router(learning_router)
app.include_router(wallet_router)
app.include_router(planner_router)
app.include_router(console_router)


class LoginRequest(BaseModel):
    email: str
    role: Role


class LoginResponse(BaseModel):
    token: str


@app.on_event("startup")
async def on_startup() -> None:
    app.state.ready = False
    init_db()
    registry = load_registry()
    agents = hydrate_agents(registry)
    supervisor = Supervisor(agents)
    app.state.registry = registry
    app.state.agents = agents
    app.state.supervisor = supervisor
    app.state.last_audit_ts = None
    dashboard_ws.configure(lambda: status_payload(app))
    for key, agent in agents.items():
        set_agent_state(key, agent.running)
    scheduler = build_scheduler(lambda: status_payload(app), notify_alert)
    scheduler.start()
    app.state.scheduler = scheduler
    start_linkedin_scheduler(app)
    app.state.ready = True
    LOGGER.info("Gateway ready with %s agents", len(agents))


@app.on_event("shutdown")
async def on_shutdown() -> None:
    LOGGER.info("Gateway shutdown requested")
    supervisor = getattr(app.state, "supervisor", None)
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


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse("dashboard/index.html")
