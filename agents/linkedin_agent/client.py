from __future__ import annotations

import pathlib
from typing import Any, Dict

import requests

from config.settings_linkedin import linkedin_settings
from .models import PostRequest


class LinkedInClient:
    """Thin wrapper around the LinkedIn REST endpoints."""

    def __init__(self, access_token: str) -> None:
        self._access_token = access_token

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def create_text_post(self, author_urn: str, text: str, visibility: str = "PUBLIC") -> Dict[str, Any]:
        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "visibility": visibility,
            "commentary": text,
            "distribution": {"feedDistribution": "MAIN_FEED"},
            "content": {"media": []},
        }
        response = requests.post(linkedin_settings.li_api_posts, json=payload, headers=self._headers())
        if response.status_code >= 400:
            raise RuntimeError(f"create post failed: {response.status_code}")
        return response.json() or {"status": "ok"}

    def init_document_upload(self, file_path: pathlib.Path, title: str) -> Dict[str, Any]:
        raise NotImplementedError(
            "LinkedIn document upload is not available in the offline harness."
        )

    def upload_document_to_url(self, upload_url: str, file_path: pathlib.Path) -> None:
        with file_path.open("rb") as handle:
            data = handle.read()
        response = requests.put(upload_url, data=data, headers={"Content-Type": "application/pdf"})
        if response.status_code >= 400:
            raise RuntimeError(f"document upload failed: {response.status_code}")

    def create_document_post(self, author_urn: str, request: PostRequest) -> Dict[str, Any]:
        doc_path = pathlib.Path(request.doc_path or "")
        if not doc_path.exists():
            raise FileNotFoundError(doc_path)
        if doc_path.stat().st_size > 100 * 1024 * 1024:
            raise ValueError("document exceeds 100MB limit")
        try:
            asset = self.init_document_upload(doc_path, request.doc_title or doc_path.name)
        except NotImplementedError as exc:
            note = f"[document fallback] {exc}. Posting text only."
            return self.create_text_post(author_urn, f"{request.text}\n\n{note}", request.visibility)
        upload_url = asset.get("uploadUrl")
        asset_urn = asset.get("asset")
        if not upload_url or not asset_urn:
            raise RuntimeError("invalid asset response from LinkedIn")
        self.upload_document_to_url(upload_url, doc_path)
        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "visibility": request.visibility,
            "commentary": request.text,
            "distribution": {"feedDistribution": "MAIN_FEED"},
            "content": {
                "media": [
                    {
                        "status": "READY",
                        "description": request.doc_title or doc_path.name,
                        "title": request.doc_title or doc_path.stem,
                        "media": asset_urn,
                    }
                ]
            },
        }
        response = requests.post(linkedin_settings.li_api_posts, json=payload, headers=self._headers())
        if response.status_code >= 400:
            raise RuntimeError(f"create document post failed: {response.status_code}")
        return response.json() or {"status": "ok"}
