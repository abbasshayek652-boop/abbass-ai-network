from __future__ import annotations

try:  # pragma: no cover - httpx may be unavailable offline
    import httpx
except ModuleNotFoundError:  # pragma: no cover
    httpx = None


async def notify_webhook(url: str, payload: dict) -> None:
    if httpx is None:
        return
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json=payload)
