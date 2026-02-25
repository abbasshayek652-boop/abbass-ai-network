from __future__ import annotations

from prometheus_client import generate_latest

import gateway


def test_metrics_and_health() -> None:
    assert gateway.app.state.ready is True
    metrics_blob = generate_latest()
    text = metrics_blob.decode()
    assert "agent_state" in text
    assert "gateway_errors_total" in text
