from __future__ import annotations

import asyncio
import json
from typing import Iterable

from ai.settings import settings


async def notify_alert(kind: str, payload: dict[str, object]) -> None:
    if not settings.telegram_token:
        return
    recipients: Iterable[int] = settings.telegram_admins or []
    if not recipients:
        return
    from aiogram import Bot  # type: ignore

    bot = Bot(settings.telegram_token)
    message = f"[{kind}] {json.dumps(payload)}"
    try:
        await asyncio.gather(*(bot.send_message(chat_id=chat, text=message) for chat in recipients))
    finally:
        await bot.session.close()
