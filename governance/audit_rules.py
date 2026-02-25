from __future__ import annotations

import json
from typing import Any, Dict

from persistence.db import add_audit, add_kv


def mask_secret(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) <= 4:
        return "****"
    return value[:2] + "***" + value[-2:]


def pre_trade_audit(engine, agent: str, payload: Dict[str, Any]) -> None:
    add_audit(engine, "info", agent, "pre_trade", json.dumps(payload))


def post_trade_audit(engine, agent: str, payload: Dict[str, Any]) -> None:
    add_audit(engine, "info", agent, "post_trade", json.dumps(payload))


def record_governance_state(engine, key: str, payload: Dict[str, Any]) -> None:
    add_kv(engine, key, json.dumps(payload))

