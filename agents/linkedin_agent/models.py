from __future__ import annotations

import datetime as dt
from typing import Literal, Optional

from pydantic import BaseModel, Field


Visibility = Literal["PUBLIC", "CONNECTIONS"]


class TokenBundle(BaseModel):
    """Persisted OAuth tokens for the LinkedIn API."""

    access_token: str
    expires_at: float
    refresh_token: str | None = None
    scope: str | None = None

    def is_expired(self, now: Optional[float] = None) -> bool:
        reference = now if now is not None else dt.datetime.utcnow().timestamp()
        return reference >= self.expires_at


class PostRequest(BaseModel):
    """User-facing payload describing a post."""

    text: str
    visibility: Visibility = "PUBLIC"
    doc_path: str | None = None
    doc_title: str | None = None


class ScheduleRequest(PostRequest):
    """Extension of :class:`PostRequest` including scheduling metadata."""

    run_at: dt.datetime | None = None
    cron: str | None = None
    state: str = Field(default="pending")

    def next_run_ts(self) -> float:
        if self.run_at is None:
            raise ValueError("run_at is required for the lightweight scheduler")
        return self.run_at.timestamp()
