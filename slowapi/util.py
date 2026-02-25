from __future__ import annotations

from typing import Any


def get_remote_address(request: Any) -> str:
    if request is None:
        return "unknown"
    client = getattr(request, "client", None)
    if client and getattr(client, "host", None):
        return client.host
    return "unknown"
