from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from sqlmodel import Session, select

from learning.data_schema import PolicyMetric
from learning.policy import registry


@dataclass
class PromotionResult:
    ok: bool
    reason: str
    new_stage: Optional[str] = None


def _collect_metrics(engine, policy_id: int) -> Dict[str, float]:
    with Session(engine) as session:
        rows = session.exec(select(PolicyMetric)).all()
    metrics: Dict[str, float] = {}
    for row in rows:
        if row.policy_id == policy_id:
            metrics[row.metric_name] = row.metric_value
    return metrics


def can_promote(metrics: Dict[str, float], thresholds: Dict[str, float]) -> PromotionResult:
    for key, limit in thresholds.items():
        value = metrics.get(key)
        if value is None:
            return PromotionResult(False, f"missing:{key}")
        if key.endswith("_min") and value < limit:
            return PromotionResult(False, f"threshold:{key}")
        if key.endswith("_max") and value > limit:
            return PromotionResult(False, f"threshold:{key}")
        if key.startswith("max_") or key.endswith("_pct"):
            if value > limit:
                return PromotionResult(False, f"threshold:{key}")
        if key.startswith("min_") and value < limit:
            return PromotionResult(False, f"threshold:{key}")
    return PromotionResult(True, "ok")


def promote(engine, policy_id: int, to_stage: str, thresholds: Dict[str, float]) -> PromotionResult:
    policy = registry.latest_policy(engine)
    if not policy or policy.id != policy_id:
        return PromotionResult(False, "policy_not_latest")
    metrics = _collect_metrics(engine, policy_id)
    check = can_promote(metrics, thresholds)
    if not check.ok:
        return check
    updated = registry.update_stage(engine, policy_id, to_stage)
    if updated is None:
        return PromotionResult(False, "update_failed")
    return PromotionResult(True, "promoted", new_stage=to_stage)


def rollback(engine, target_stage: str = "shadow") -> Optional[int]:
    policy = registry.latest_policy(engine)
    if not policy:
        return None
    registry.update_stage(engine, policy.id or 0, target_stage)
    return policy.id
