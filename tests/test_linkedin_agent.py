from __future__ import annotations

import datetime as dt
import time
from pathlib import Path
from typing import Any, Dict

import pytest

import requests
from agents.linkedin_agent import oauth, storage
from agents.linkedin_agent.models import ScheduleRequest, TokenBundle
from agents.linkedin_agent.service import service
from config.settings_linkedin import linkedin_settings


@pytest.fixture(autouse=True)
def _temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    original_path = storage._DB_PATH  # type: ignore[attr-defined]
    storage.configure(str(tmp_path / "linkedin.db"))
    monkeypatch.setattr(linkedin_settings, "li_client_id", "client-id")
    monkeypatch.setattr(linkedin_settings, "li_client_secret", "client-secret")
    monkeypatch.setattr(linkedin_settings, "li_redirect_uri", "http://localhost/callback")
    monkeypatch.setattr(linkedin_settings, "li_oauth_authorize", "https://auth.example")
    monkeypatch.setattr(linkedin_settings, "li_oauth_token", "https://token.example")
    monkeypatch.setattr(linkedin_settings, "li_api_userinfo", "https://userinfo.example")
    monkeypatch.setattr(linkedin_settings, "li_api_posts", "https://api.example/posts")
    service._daily_posts = 0
    service._daily_reset = dt.date.today()
    yield
    storage.configure(str(original_path))


def test_login_url_contains_expected_state():
    url = service.login_url("state-123")
    assert "state-123" in url
    assert "client-id" in url
    assert "redirect_uri=http%3A%2F%2Flocalhost%2Fcallback" in url


def test_callback_persists_tokens(monkeypatch: pytest.MonkeyPatch):
    def fake_exchange(code: str) -> TokenBundle:
        bundle = TokenBundle(access_token="token", expires_at=time.time() + 3600)
        storage.save_tokens(bundle)
        return bundle

    def fake_userinfo(token: str) -> Dict[str, Any]:
        return {"sub": "urn:li:person:123"}

    monkeypatch.setattr(oauth, "exchange_code_for_token", fake_exchange)
    monkeypatch.setattr(oauth, "get_userinfo", fake_userinfo)
    response = service.handle_callback("code", "state")
    assert response["owner"] == "urn:li:person:123"
    assert storage.get_tokens() is not None


def test_post_text_builds_payload(monkeypatch: pytest.MonkeyPatch):
    bundle = TokenBundle(access_token="token", expires_at=time.time() + 3600)
    storage.save_tokens(bundle)
    monkeypatch.setattr(oauth, "get_userinfo", lambda token: {"sub": "urn:li:person:abc"})

    captured: Dict[str, Any] = {}

    def fake_post(url: str, json: Dict[str, Any], headers: Dict[str, str]):
        captured.update({"url": url, "json": json, "headers": headers})
        return requests.Response(status_code=201, data={"id": "123"})

    monkeypatch.setattr(requests, "post", fake_post)
    result = service.post_text("Hello LinkedIn", "PUBLIC")
    assert captured["url"] == "https://api.example/posts"
    assert captured["json"]["commentary"] == "Hello LinkedIn"
    assert "Authorization" in captured["headers"]
    assert result["id"] == "123"


def test_scheduler_publishes_due(monkeypatch: pytest.MonkeyPatch):
    bundle = TokenBundle(access_token="token", expires_at=time.time() + 3600)
    storage.save_tokens(bundle)
    monkeypatch.setattr(oauth, "get_userinfo", lambda token: {"sub": "urn:li:person:owner"})

    published: list[str] = []

    def fake_post(url: str, json: Dict[str, Any], headers: Dict[str, str]):
        published.append(json["commentary"])
        return requests.Response(status_code=200, data={"ok": True})

    monkeypatch.setattr(requests, "post", fake_post)
    run_time = dt.datetime.utcnow()
    req = ScheduleRequest(text="Scheduled", run_at=run_time)
    service.schedule_post(req)
    published_ids = service.publish_due(run_time.timestamp() + 1)
    assert published_ids
    assert published == ["Scheduled"]
