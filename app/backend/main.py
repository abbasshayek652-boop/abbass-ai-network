from __future__ import annotations

import asyncio
import contextlib
import os
import random
from typing import Dict, List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from models import AgentState
from schemas import AgentInfo, CommandRequest, CommandResponse, GatewayStatus, MetricPoint, StatusResponse
from services.agents import AgentRegistry
from services.metrics import MetricService

load_dotenv()

app = FastAPI(title=os.getenv('API_TITLE', 'Mother AI Gateway'))
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv('CORS_ORIGINS', '*').split(','),
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

INITIAL_AGENTS = [
    AgentState(id='crypto', name='Crypto Trader', cpu=42, mem=48, status='running'),
    AgentState(id='gold', name='Gold Trader', cpu=35, mem=40, status='running'),
    AgentState(id='content', name='Content Bot', cpu=18, mem=24, status='idle'),
    AgentState(id='linkedin', name='LinkedIn Outreach', cpu=12, mem=20, status='stopped'),
    AgentState(id='learning', name='Learning Engine', cpu=55, mem=60, status='running'),
]

registry = AgentRegistry(INITIAL_AGENTS)
metrics = MetricService()
connections: set[WebSocket] = set()
state: Dict[str, bool] = {'online': True}


async def broadcast(payload: Dict[str, object]) -> None:
    stale: List[WebSocket] = []
    for connection in connections.copy():
        try:
            await connection.send_json(payload)
        except Exception:
            stale.append(connection)
    for connection in stale:
        connections.discard(connection)


async def telemetry_loop() -> None:
    while True:
        metrics.append_point()
        await registry.jitter_metrics()
        agent_list = await registry.list_agents()
        choice = random.choice(agent_list)
        log_line = f"[{random.randint(0,23):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}] {choice.name} heartbeat ok"
        await broadcast({'type': 'log', 'line': log_line})
        await broadcast(
            {
                'type': 'agent',
                'id': choice.id,
                'status': choice.status,
                'cpu': choice.cpu,
                'mem': choice.mem,
            }
        )
        await broadcast({'type': 'gateway', 'online': state['online']})
        await asyncio.sleep(1)


@app.on_event('startup')
async def on_startup() -> None:
    app.state.worker = asyncio.create_task(telemetry_loop())


@app.on_event('shutdown')
async def on_shutdown() -> None:
    task: asyncio.Task = app.state.worker  # type: ignore[attr-defined]
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


def to_schema(agent: AgentState) -> AgentInfo:
    return AgentInfo(**agent.__dict__)


@app.get('/agents', response_model=List[AgentInfo])
async def list_agents() -> List[AgentInfo]:
    agents = await registry.list_agents()
    return [to_schema(agent) for agent in agents]


@app.post('/agents/{agent_id}/start', response_model=AgentInfo)
async def start_agent(agent_id: str) -> AgentInfo:
    agent = await registry.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail='Agent not found')
    updated = await registry.set_status(agent_id, 'running')
    await broadcast({'type': 'agent', 'id': agent_id, 'status': 'running', 'cpu': updated.cpu, 'mem': updated.mem})
    return to_schema(updated)


@app.post('/agents/{agent_id}/stop', response_model=AgentInfo)
async def stop_agent(agent_id: str) -> AgentInfo:
    agent = await registry.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail='Agent not found')
    updated = await registry.set_status(agent_id, 'stopped')
    await broadcast({'type': 'agent', 'id': agent_id, 'status': 'stopped', 'cpu': updated.cpu, 'mem': updated.mem})
    return to_schema(updated)


@app.get('/status/all', response_model=StatusResponse)
async def status_all() -> StatusResponse:
    agents = await registry.list_agents()
    return StatusResponse(gateway=GatewayStatus(online=state['online'], uptime_s=metrics.uptime), agents=[to_schema(a) for a in agents])


@app.get('/metrics', response_model=List[MetricPoint])
async def read_metrics() -> List[MetricPoint]:
    return metrics.current()


@app.post('/gateway/restart')
async def gateway_restart() -> Dict[str, bool]:
    if not state['online']:
        return {'ok': True}

    state['online'] = False
    await broadcast({'type': 'gateway', 'online': False})

    async def _restore() -> None:
        await asyncio.sleep(1.5)
        state['online'] = True
        await broadcast({'type': 'gateway', 'online': True})

    asyncio.create_task(_restore())
    return {'ok': True}


@app.post('/command', response_model=CommandResponse)
async def run_command(request: CommandRequest) -> CommandResponse:
    message = f"received: {request.text}"
    return CommandResponse(ok=True, message=message)


@app.websocket('/ws/status')
async def ws_status(websocket: WebSocket) -> None:
    await websocket.accept()
    connections.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connections.discard(websocket)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('main:app', host='0.0.0.0', port=int(os.getenv('PORT', '8000')), reload=True)
