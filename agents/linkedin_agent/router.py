from __future__ import annotations

import datetime as dt
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from .models import PostRequest, ScheduleRequest
from .service import service
from .scheduler import start_scheduler

router = APIRouter()


def _parse_datetime(value: str) -> dt.datetime:
    try:
        return dt.datetime.fromisoformat(value)
    except ValueError as exc:  # pragma: no cover - invalid input path
        raise HTTPException(status_code=400, detail="Invalid datetime format") from exc


@router.get("/agents/linkedin/login")
def login() -> RedirectResponse:
    url = service.login_url()
    return RedirectResponse(url)


@router.get("/agents/linkedin/callback")
def callback(code: str, state: str | None = None) -> Dict[str, Any]:
    return service.handle_callback(code, state)


@router.post("/agents/linkedin/post/text")
def post_text(payload: Dict[str, Any]) -> Dict[str, Any]:
    text = payload.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    visibility = payload.get("visibility", "PUBLIC")
    return service.post_text(str(text), str(visibility))


@router.post("/agents/linkedin/post/document")
def post_document(payload: Dict[str, Any]) -> Dict[str, Any]:
    model = PostRequest(**payload)
    if not model.doc_path:
        raise HTTPException(status_code=400, detail="doc_path required")
    return service.post_document(model)


@router.post("/agents/linkedin/schedule")
def schedule(payload: Dict[str, Any]) -> Dict[str, Any]:
    if "run_at" in payload and isinstance(payload["run_at"], str):
        payload["run_at"] = _parse_datetime(payload["run_at"])
    request = ScheduleRequest(**payload)
    schedule_id = service.schedule_post(request)
    return {"scheduled_id": schedule_id}


@router.get("/agents/linkedin/schedule")
def list_schedule() -> Dict[str, Any]:
    return {"items": service.list_scheduled()}


@router.get("/agents/linkedin/health")
def health() -> Dict[str, Any]:
    return service.health()


__all__ = ["router", "start_scheduler"]
