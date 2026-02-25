from __future__ import annotations

from typing import Dict, Iterable, Optional

from sqlmodel import Session, select

from learning.data_schema import Policy, PolicyMetric, dumps_payload, hash_payload


def _next_version(policies: Iterable[Policy]) -> int:
    versions = [p.version for p in policies]
    return max(versions) + 1 if versions else 1


def create_policy(
    engine,
    *,
    payload: Dict[str, object],
    stage: str,
    description: str = "",
    metrics: Optional[Dict[str, float]] = None,
) -> Policy:
    payload_json = dumps_payload(payload)
    payload_hash = hash_payload(payload)
    with Session(engine) as session:
        existing = session.exec(select(Policy)).all()
        policy = Policy(
            version=_next_version(existing),
            stage=stage,
            payload_json=payload_json,
            payload_hash=payload_hash,
            description=description,
        )
        session.add(policy)
        session.commit()
        if metrics:
            for name, value in metrics.items():
                session.add(PolicyMetric(policy_id=policy.id or 0, metric_name=name, metric_value=value))
            session.commit()
    return policy


def latest_policy(engine, stage: Optional[str] = None) -> Optional[Policy]:
    with Session(engine) as session:
        policies = session.exec(select(Policy)).all()
    if stage:
        policies = [p for p in policies if p.stage == stage]
    if not policies:
        return None
    policies.sort(key=lambda p: (p.version, p.created_ts))
    return policies[-1]


def update_stage(engine, policy_id: int, stage: str) -> Optional[Policy]:
    with Session(engine) as session:
        policies = session.exec(select(Policy)).all()
        for policy in policies:
            if policy.id == policy_id:
                policy.stage = stage
                session.commit()
                return policy
    return None


def list_policies(engine) -> Iterable[Policy]:
    with Session(engine) as session:
        return session.exec(select(Policy)).all()
