from __future__ import annotations

from learning.data_schema import ensure_engine
from learning.policy.registry import create_policy, latest_policy, list_policies, update_stage
from learning.policy.rollout import can_promote


def test_policy_versioning_and_stage() -> None:
    engine = ensure_engine("sqlite:///test_policy_registry")
    first = create_policy(engine, payload={"risk_caps": {"max_notional_per_trade": 15}}, stage="shadow")
    second = create_policy(engine, payload={"risk_caps": {"max_notional_per_trade": 10}}, stage="shadow")
    assert second.version == first.version + 1
    update_stage(engine, second.id or 0, "canary")
    latest = latest_policy(engine)
    assert latest.stage == "canary"
    assert len(list(list_policies(engine))) == 2


def test_can_promote_thresholds() -> None:
    result = can_promote({"sharpe_min": 1.0, "max_dd_pct": 0.05}, {"sharpe_min": 0.8, "max_dd_pct": 0.1})
    assert result.ok
    blocked = can_promote({"sharpe_min": 0.5, "max_dd_pct": 0.2}, {"sharpe_min": 0.8, "max_dd_pct": 0.1})
    assert not blocked.ok
