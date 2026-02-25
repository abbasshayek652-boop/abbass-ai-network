from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


AgentStatus = Literal['running', 'idle', 'stopped']


@dataclass
class AgentState:
    id: str
    name: str
    cpu: int
    mem: int
    status: AgentStatus
