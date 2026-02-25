from __future__ import annotations

from typing import Any


class JSONResponse:
    def __init__(self, content: Any, status_code: int = 200) -> None:
        self.content = content
        self.status_code = status_code


class FileResponse:
    def __init__(self, path: str) -> None:
        self.path = path


class RedirectResponse:
    def __init__(self, url: str, status_code: int = 307) -> None:
        self.url = url
        self.status_code = status_code
