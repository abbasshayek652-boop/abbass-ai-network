from __future__ import annotations

import asyncio

from ai.supervisor import Supervisor


class TelegramAdapter:
    def __init__(self, sup: Supervisor) -> None:
        self.sup = sup

    async def cmd_start(self, agent_key: str) -> None:
        await self.sup.start(agent_key)

    async def cmd_stop(self, agent_key: str) -> None:
        await self.sup.stop(agent_key)

    async def cmd_status(self) -> dict[str, object]:
        keys = list(self.sup.agents.keys())
        results = await asyncio.gather(*(self.sup.agents[key].status() for key in keys))
        return dict(zip(keys, results))

