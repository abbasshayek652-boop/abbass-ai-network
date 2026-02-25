from __future__ import annotations

import abc
from typing import Any, Dict


class Agent(abc.ABC):
    """Abstract contract implemented by all agents managed by Mother AI."""

    name: str
    description: str = ""
    running: bool = False

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

    @abc.abstractmethod
    async def start(self) -> None:
        """Start the agent and allocate resources."""

    @abc.abstractmethod
    async def stop(self) -> None:
        """Stop the agent and release resources."""

    @abc.abstractmethod
    async def status(self) -> Dict[str, Any]:
        """Return the current status payload for dashboards or APIs."""

    async def on_tick(self) -> None:
        """Periodic hook invoked by the supervisor while the agent is running."""

