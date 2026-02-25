from __future__ import annotations

import time
import urllib.parse
from typing import Any, Dict

import requests

from config.settings_linkedin import linkedin_settings
from .models import TokenBundle
from . import storage


def build_authorize_url(state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": linkedin_settings.li_client_id,
        "redirect_uri": linkedin_settings.li_redirect_uri,
        "scope": " ".join(linkedin_settings.li_scopes),
        "state": state,
    }
    return f"{linkedin_settings.li_oauth_authorize}?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(code: str) -> TokenBundle:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": linkedin_settings.li_redirect_uri,
        "client_id": linkedin_settings.li_client_id,
        "client_secret": linkedin_settings.li_client_secret,
    }
    response = requests.post(linkedin_settings.li_oauth_token, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    if response.status_code >= 400:
        raise RuntimeError(f"token exchange failed: {response.status_code}")
    payload = response.json()
    expires_in = float(payload.get("expires_in", 0))
    expires_at = time.time() + expires_in if expires_in else time.time() + 3600
    bundle = TokenBundle(
        access_token=payload["access_token"],
        expires_at=expires_at,
        refresh_token=payload.get("refresh_token"),
        scope=payload.get("scope"),
    )
    storage.save_tokens(bundle)
    return bundle


def get_userinfo(access_token: str) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(linkedin_settings.li_api_userinfo, headers=headers)
    if response.status_code >= 400:
        raise RuntimeError(f"userinfo failed: {response.status_code}")
    return response.json()
