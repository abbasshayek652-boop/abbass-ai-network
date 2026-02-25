from __future__ import annotations

import datetime as dt
import secrets
from typing import Any, Dict, List

from config.settings_linkedin import linkedin_settings
from . import oauth, storage
from .client import LinkedInClient
from .models import PostRequest, ScheduleRequest, TokenBundle


class LinkedInService:
    """High level façade coordinating OAuth, posting, and scheduling."""

    def __init__(self) -> None:
        self._daily_reset = dt.date.today()
        self._daily_posts = 0

    def login_url(self, state: str | None = None) -> str:
        token = state or secrets.token_urlsafe(16)
        return oauth.build_authorize_url(token)

    def handle_callback(self, code: str, state: str | None = None) -> Dict[str, Any]:
        bundle = oauth.exchange_code_for_token(code)
        info = oauth.get_userinfo(bundle.access_token)
        owner = info.get("sub")
        if not owner:
            raise RuntimeError("LinkedIn userinfo missing subject")
        return {"ok": True, "owner": owner}

    def _load_tokens(self) -> TokenBundle:
        bundle = storage.get_tokens()
        if bundle is None:
            raise RuntimeError("LinkedIn tokens not initialised; authenticate first")
        if bundle.is_expired():
            raise RuntimeError("LinkedIn token expired; refresh required")
        return bundle

    def _client(self) -> LinkedInClient:
        bundle = self._load_tokens()
        return LinkedInClient(bundle.access_token)

    def _owner_urn(self, bundle: TokenBundle | None = None) -> str:
        tokens = bundle or self._load_tokens()
        info = oauth.get_userinfo(tokens.access_token)
        owner = info.get("sub")
        if not owner:
            raise RuntimeError("Unable to determine LinkedIn owner URN")
        return owner

    def _reset_daily_if_needed(self) -> None:
        today = dt.date.today()
        if today != self._daily_reset:
            self._daily_reset = today
            self._daily_posts = 0

    def _assert_quota(self) -> None:
        self._reset_daily_if_needed()
        if self._daily_posts >= linkedin_settings.li_daily_post_limit:
            raise RuntimeError("Daily LinkedIn post limit reached")

    def post_text(self, text: str, visibility: str = "PUBLIC") -> Dict[str, Any]:
        self._assert_quota()
        bundle = self._load_tokens()
        owner = self._owner_urn(bundle)
        client = LinkedInClient(bundle.access_token)
        response = client.create_text_post(owner, text, visibility)
        self._daily_posts += 1
        return response

    def post_document(self, request: PostRequest) -> Dict[str, Any]:
        self._assert_quota()
        bundle = self._load_tokens()
        owner = self._owner_urn(bundle)
        client = LinkedInClient(bundle.access_token)
        response = client.create_document_post(owner, request)
        self._daily_posts += 1
        return response

    def schedule_post(self, request: ScheduleRequest) -> int:
        if request.run_at is None:
            raise ValueError("run_at is required for scheduling")
        return storage.upsert_scheduled_post(request)

    def list_scheduled(self) -> List[Dict[str, Any]]:
        return storage.list_scheduled()

    def publish_due(self, now: float | None = None) -> List[int]:
        published: List[int] = []
        for post_id, request in storage.due_posts(now):
            try:
                if request.doc_path:
                    self.post_document(request)
                else:
                    self.post_text(request.text, request.visibility)
                storage.mark_done(post_id, "completed")
                published.append(post_id)
            except Exception as exc:  # noqa: BLE001
                storage.mark_done(post_id, f"failed:{exc}")
        return published

    def health(self) -> Dict[str, Any]:
        bundle = storage.get_tokens()
        return {
            "status": "ok",
            "has_token": bundle is not None and not (bundle.is_expired() if bundle else True),
        }


service = LinkedInService()
