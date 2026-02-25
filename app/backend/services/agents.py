from __future__ import annotations

import asyncio
import random
from collections.abc import Iterable
from typing import Dict

from models import AgentState, AgentStatus


class AgentRegistry:
    """In-memory agent registry with async-safe mutations."""

    def __init__(self, agents: Iterable[AgentState]):
        self._agents: Dict[str, AgentState] = {agent.id: agent for agent in agents}
        self._lock = asyncio.Lock()

    async def list_agents(self) -> list[AgentState]:
        async with self._lock:
            return [AgentState(**agent.__dict__) for agent in self._agents.values()]

    async def get(self, agent_id: str) -> AgentState | None:
        async with self._lock:
            agent = self._agents.get(agent_id)
            return AgentState(**agent.__dict__) if agent else None

    async def set_status(self, agent_id: str, status: AgentStatus) -> AgentState:
        async with self._lock:
            agent = self._agents[agent_id]
            agent.status = status
            self._agents[agent_id] = agent
            return AgentState(**agent.__dict__)

    async def update_metrics(self, agent_id: str, *, cpu: int, mem: int) -> None:
        async with self._lock:
            agent = self._agents.get(agent_id)
            if agent:
                agent.cpu = cpu
                agent.mem = mem
                self._agents[agent_id] = agent

    async def jitter_metrics(self) -> None:
        async with self._lock:
            for agent in self._agents.values():
                if agent.status == 'running':
                    agent.cpu = min(100, max(5, agent.cpu + random.randint(-5, 8)))
                    agent.mem = min(100, max(5, agent.mem + random.randint(-3, 5)))
                else:
                    agent.cpu = max(0, agent.cpu - random.randint(0, 3))
                    agent.mem = max(0, agent.mem - random.randint(0, 4))


__all__ = ['AgentRegistry']
