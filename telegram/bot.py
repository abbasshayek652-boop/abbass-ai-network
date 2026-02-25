from __future__ import annotations

import json
import time
import uuid
from collections import defaultdict, deque
from typing import Any, Callable, Deque

import httpx

from ai.settings import settings
from gateway.metrics import record_telegram_command

MAX_COMMANDS_PER_MIN = 10
_COMMAND_HISTORY: dict[int, Deque[float]] = defaultdict(deque)


def _role_for(user_id: int) -> str:
    if user_id in settings.telegram_admins:
        return "admin"
    if user_id in settings.telegram_operators:
        return "operator"
    return "viewer"


def _rate_limited(user_id: int) -> bool:
    now = time.time()
    history = _COMMAND_HISTORY[user_id]
    while history and now - history[0] > 60:
        history.popleft()
    if len(history) >= MAX_COMMANDS_PER_MIN:
        return True
    history.append(now)
    return False


async def _call_gateway(method: str, path: str, correlation_id: str, data: dict[str, object] | None = None) -> httpx.Response:
    headers = {"X-Correlation-ID": correlation_id}
    if settings.api_key:
        headers["X-API-Key"] = settings.api_key
    async with httpx.AsyncClient(base_url=settings.gateway_url, timeout=10) as client:
        if method.upper() == "GET":
            return await client.get(path, headers=headers)
        return await client.post(path, json=data or {}, headers=headers)


async def _send_status(message: Any, correlation_id: str) -> None:
    response = await _call_gateway("GET", "/status", correlation_id)
    if response.is_success:
        payload = response.json()
        formatted = json.dumps(payload, indent=2)
        await message.answer(f"Status (CID: {correlation_id})\n<pre>{formatted}</pre>", parse_mode="HTML")
    else:
        await message.answer(f"Status unavailable (CID: {correlation_id})")


async def _control(agent_key: str, action: str, message: Any, correlation_id: str) -> None:
    response = await _call_gateway("POST", f"/{action}", correlation_id, {"agent_key": agent_key})
    if response.is_success:
        await message.answer(f"{action.title()} scheduled for {agent_key} (CID: {correlation_id})")
    else:
        detail = response.json().get("detail") if response.headers.get("content-type", "").startswith("application/json") else response.text
        await message.answer(f"Failed to {action} {agent_key} (CID: {correlation_id}): {detail}")


async def _list_agents(
    message: Any, correlation_id: str, markup_builder: Callable[[list[str]], Any] | None = None
) -> None:
    response = await _call_gateway("GET", "/status", correlation_id)
    if not response.is_success:
        await message.answer(f"Unable to load agents (CID: {correlation_id})")
        return
    payload = response.json()
    agents = list(payload.get("agents", {})) if isinstance(payload, dict) else []
    if not agents:
        await message.answer(f"No agents registered (CID: {correlation_id})")
        return
    if markup_builder:
        markup = markup_builder(agents)
    else:
        keyboard = []
        for agent in agents:
            keyboard.append(
                [
                    {"text": f"▶️ Start {agent}", "callback_data": f"start:{agent}"},
                    {"text": f"⏹ Stop {agent}", "callback_data": f"stop:{agent}"},
                ]
            )
        markup = {"inline_keyboard": keyboard}
    await message.answer(f"Agent controls (CID: {correlation_id})", reply_markup=markup)


async def _handle_logs(message: Any, agent_key: str, correlation_id: str) -> None:
    response = await _call_gateway("GET", f"/logs/{agent_key}", correlation_id)
    if response.is_success:
        text = response.text[-3500:]
        await message.answer(f"Logs for {agent_key} (CID: {correlation_id})\n<pre>{text}</pre>", parse_mode="HTML")
    else:
        await message.answer(f"Unable to fetch logs (CID: {correlation_id})")


def _ensure_role(message: Any, minimum_role: str) -> bool:
    user = getattr(getattr(message, "from_user", None), "id", None)
    if user is None:
        return False
    user_role = _role_for(user)
    order = {"viewer": 0, "operator": 1, "admin": 2}
    return order[user_role] >= order[minimum_role]


async def main() -> None:
    if not settings.telegram_token:
        raise RuntimeError("Telegram token not configured")

    from aiogram import Bot, Dispatcher, F  # type: ignore
    from aiogram.filters import Command, CommandStart  # type: ignore
    from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message  # type: ignore

    bot = Bot(settings.telegram_token)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start(message: Message) -> None:
        cid = str(uuid.uuid4())
        if _rate_limited(message.from_user.id):
            await message.answer(f"Too many requests (CID: {cid})")
            return
        record_telegram_command("start", _role_for(message.from_user.id))
        await message.answer(
            "Mother AI bot ready. Use /status or /agents to control agents. "
            f"(CID: {cid})"
        )

    @dp.message(Command("help"))
    async def help_cmd(message: Message) -> None:
        cid = str(uuid.uuid4())
        record_telegram_command("help", _role_for(message.from_user.id))
        await message.answer(
            "Commands:\n/status – current status\n/agents – inline controls\n"
            "/start_agent <key>\n/stop_agent <key>\n/logs <key> (CID: {cid})"
        )

    @dp.message(Command("status"))
    async def status_cmd(message: Message) -> None:
        cid = str(uuid.uuid4())
        if _rate_limited(message.from_user.id):
            await message.answer(f"Rate limit hit (CID: {cid})")
            return
        record_telegram_command("status", _role_for(message.from_user.id))
        await _send_status(message, cid)

    @dp.message(Command("agents"))
    async def agents_cmd(message: Message) -> None:
        cid = str(uuid.uuid4())
        if _rate_limited(message.from_user.id):
            await message.answer(f"Rate limit hit (CID: {cid})")
            return
        record_telegram_command("agents", _role_for(message.from_user.id))
        await _list_agents(
            message,
            cid,
            lambda agents: InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text=f"▶️ Start {agent}", callback_data=f"start:{agent}"),
                        InlineKeyboardButton(text=f"⏹ Stop {agent}", callback_data=f"stop:{agent}"),
                    ]
                    for agent in agents
                ]
            ),
        )

    @dp.message(Command("start_agent"))
    async def start_agent(message: Message) -> None:
        cid = str(uuid.uuid4())
        if not _ensure_role(message, "operator"):
            await message.answer(f"Permission denied (CID: {cid})")
            return
        if _rate_limited(message.from_user.id):
            await message.answer(f"Rate limit hit (CID: {cid})")
            return
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer(f"Usage: /start_agent <key> (CID: {cid})")
            return
        await _control(parts[1], "start", message, cid)

    @dp.message(Command("stop_agent"))
    async def stop_agent(message: Message) -> None:
        cid = str(uuid.uuid4())
        if not _ensure_role(message, "operator"):
            await message.answer(f"Permission denied (CID: {cid})")
            return
        if _rate_limited(message.from_user.id):
            await message.answer(f"Rate limit hit (CID: {cid})")
            return
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer(f"Usage: /stop_agent <key> (CID: {cid})")
            return
        await _control(parts[1], "stop", message, cid)

    @dp.message(Command("logs"))
    async def logs_cmd(message: Message) -> None:
        cid = str(uuid.uuid4())
        if not _ensure_role(message, "operator"):
            await message.answer(f"Permission denied (CID: {cid})")
            return
        if _rate_limited(message.from_user.id):
            await message.answer(f"Rate limit hit (CID: {cid})")
            return
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer(f"Usage: /logs <key> (CID: {cid})")
            return
        await _handle_logs(message, parts[1], cid)

    @dp.callback_query(F.data.startswith("start:"))
    async def start_callback(callback: CallbackQuery) -> None:
        cid = str(uuid.uuid4())
        if not callback.message or not _ensure_role(callback.message, "operator"):
            await callback.answer("Permission denied", show_alert=True)
            return
        record_telegram_command("start_button", _role_for(callback.from_user.id))
        agent = callback.data.split(":", 1)[1]
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Confirm", callback_data=f"confirm:start:{agent}")]]
        )
        await callback.message.answer(f"Confirm start {agent}? (CID: {cid})", reply_markup=markup)
        await callback.answer()

    @dp.callback_query(F.data.startswith("stop:"))
    async def stop_callback(callback: CallbackQuery) -> None:
        cid = str(uuid.uuid4())
        if not callback.message or not _ensure_role(callback.message, "operator"):
            await callback.answer("Permission denied", show_alert=True)
            return
        record_telegram_command("stop_button", _role_for(callback.from_user.id))
        agent = callback.data.split(":", 1)[1]
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Confirm", callback_data=f"confirm:stop:{agent}")]]
        )
        await callback.message.answer(f"Confirm stop {agent}? (CID: {cid})", reply_markup=markup)
        await callback.answer()

    @dp.callback_query(F.data.startswith("confirm:"))
    async def confirm_callback(callback: CallbackQuery) -> None:
        cid = str(uuid.uuid4())
        if _rate_limited(callback.from_user.id):
            await callback.answer("Rate limited", show_alert=True)
            return
        record_telegram_command("confirm", _role_for(callback.from_user.id))
        _, action, agent = callback.data.split(":", 2)
        if callback.message:
            await _control(agent, action, callback.message, cid)
        await callback.answer("Sent")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
