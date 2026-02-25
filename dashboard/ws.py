from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from gateway.auth import decode_token

router = APIRouter()

_SNAPSHOT_PROVIDER: Optional[Callable[[], Awaitable[dict[str, object]]]] = None


def configure(snapshot_provider: Callable[[], Awaitable[dict[str, object]]]) -> None:
    global _SNAPSHOT_PROVIDER
    _SNAPSHOT_PROVIDER = snapshot_provider


@router.websocket("/ws/status")
async def ws_status(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        hello = await websocket.receive_json()
    except Exception:  # noqa: BLE001
        await websocket.close(code=4000)
        return
    token = hello.get("token") if isinstance(hello, dict) else None
    if not token:
        await websocket.close(code=4001)
        return
    try:
        decode_token(token)
    except Exception:  # noqa: BLE001
        await websocket.close(code=4003)
        return
    if _SNAPSHOT_PROVIDER is None:
        await websocket.close(code=1011)
        return
    try:
        while True:
            payload = await _SNAPSHOT_PROVIDER()
            await websocket.send_json(payload)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return
