from __future__ import annotations

import time
from typing import Dict, Optional

from persistence.audit import AuditEvent, write_audit


def log_model_run(user: str, role: str, dataset_hash: str, params: Dict[str, object], metrics: Dict[str, float]) -> None:
    write_audit(
        AuditEvent(
            user_id=user,
            role=role,
            action="learning.model_run",
            agent_key="learning",
            ip=None,
            correlation_id=f"learning-{int(time.time()*1000)}",
            ok=True,
            details={"dataset_hash": dataset_hash, "params": params, "metrics": metrics},
        )
    )


def log_policy_decision(user: str, role: str, policy_id: int, stage: str, ok: bool, reason: Optional[str] = None) -> None:
    write_audit(
        AuditEvent(
            user_id=user,
            role=role,
            action="learning.policy",
            agent_key="learning",
            ip=None,
            correlation_id=f"policy-{policy_id}",
            ok=ok,
            details={"policy_id": policy_id, "stage": stage, "reason": reason},
        )
    )
