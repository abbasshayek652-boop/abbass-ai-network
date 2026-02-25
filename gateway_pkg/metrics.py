from __future__ import annotations

from prometheus_client import Counter, Gauge, make_asgi_app

agent_state = Gauge("agent_state", "Agent running state", ["agent"])
agent_actions_total = Counter(
    "agent_actions_total", "Agent control actions", ["agent", "action", "who"]
)
gateway_errors_total = Counter(
    "gateway_errors_total", "Gateway errors by endpoint", ["endpoint"]
)
telegram_commands_total = Counter(
    "telegram_commands_total", "Telegram commands executed", ["command", "user_role"]
)


def metrics_app():
    return make_asgi_app()


def set_agent_state(agent: str, running: bool) -> None:
    agent_state.labels(agent=agent).set(1 if running else 0)


def record_agent_action(agent: str, action: str, who: str) -> None:
    agent_actions_total.labels(agent=agent, action=action, who=who).inc()


def record_gateway_error(endpoint: str) -> None:
    gateway_errors_total.labels(endpoint=endpoint).inc()


def record_telegram_command(command: str, role: str) -> None:
    telegram_commands_total.labels(command=command, user_role=role).inc()
