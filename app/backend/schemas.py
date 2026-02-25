from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel

AgentStatus = Literal['running', 'idle', 'stopped']


class AgentInfo(BaseModel):
    id: str
    name: str
    cpu: int
    mem: int
    status: AgentStatus


class GatewayStatus(BaseModel):
    online: bool
    uptime_s: int


class MetricPoint(BaseModel):
    t: int
    cpu: float
    mem: float
    pnl: float


class CommandRequest(BaseModel):
    text: str


class CommandResponse(BaseModel):
    ok: bool
    message: str


class StatusResponse(BaseModel):
    gateway: GatewayStatus
    agents: List[AgentInfo]
