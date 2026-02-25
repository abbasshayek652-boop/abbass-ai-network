from __future__ import annotations

import time
from typing import Dict, Iterable, List, Optional

from sqlmodel import Session, select

from learning.data_schema import (
    Advice,
    Event,
    FeatureView,
    LearningSnapshot,
    MarketSnapshot,
    ModelRun,
    Policy,
    QCIssue,
    Trade,
    dumps_payload,
)


def _now() -> float:
    return time.time()


def add_event(engine, agent: str, kind: str, payload: Dict[str, object]) -> Event:
    event = Event(agent=agent, kind=kind, payload_json=dumps_payload(payload))
    with Session(engine) as session:
        session.add(event)
        session.commit()
    return event


def add_trade(
    engine,
    *,
    agent: str,
    symbol: str,
    side: str,
    qty: float,
    price: float,
    pnl: float,
    paper: bool,
    policy_id: Optional[str] = None,
) -> Trade:
    trade = Trade(
        ts=_now(),
        agent=agent,
        symbol=symbol,
        side=side,
        qty=qty,
        price=price,
        pnl=pnl,
        paper=paper,
        policy_id=policy_id,
    )
    with Session(engine) as session:
        session.add(trade)
        session.commit()
    return trade


def add_market_snapshot(engine, *, symbol: str, price: float, volume: float, features: Dict[str, object]) -> MarketSnapshot:
    snap = MarketSnapshot(ts=_now(), symbol=symbol, price=price, volume=volume, features_json=dumps_payload(features))
    with Session(engine) as session:
        session.add(snap)
        session.commit()
    return snap


def add_qc_issue(engine, *, agent: str, symbol: str, reason: str) -> QCIssue:
    issue = QCIssue(ts=_now(), agent=agent, symbol=symbol, reason=reason)
    with Session(engine) as session:
        session.add(issue)
        session.commit()
    return issue


def add_feature_view(engine, *, name: str, data_json: str, data_hash: str) -> FeatureView:
    view = FeatureView(name=name, as_of_ts=_now(), data_json=data_json, data_hash=data_hash)
    with Session(engine) as session:
        session.add(view)
        session.commit()
    return view


def list_events_since(engine, ts: float, *, kinds: Optional[Iterable[str]] = None) -> List[Event]:
    with Session(engine) as session:
        events = session.exec(select(Event)).all()
    filtered = [e for e in events if e.ts > ts]
    if kinds:
        allowed = set(kinds)
        filtered = [e for e in filtered if e.kind in allowed]
    return filtered


def list_trades_since(engine, ts: float, *, agent: Optional[str] = None) -> List[Trade]:
    with Session(engine) as session:
        trades = session.exec(select(Trade)).all()
    results = [t for t in trades if t.ts > ts]
    if agent:
        results = [t for t in results if t.agent == agent]
    return results


def latest_model_run(engine, *, model_type: str) -> Optional[ModelRun]:
    with Session(engine) as session:
        runs = session.exec(select(ModelRun)).all()
    runs = [r for r in runs if r.model_type == model_type]
    if not runs:
        return None
    return sorted(runs, key=lambda r: r.completed_ts)[-1]


def latest_policy(engine, *, stage: str) -> Optional[Policy]:
    with Session(engine) as session:
        policies = session.exec(select(Policy)).all()
    policies = [p for p in policies if p.stage == stage]
    if not policies:
        return None
    policies.sort(key=lambda p: (p.version, p.created_ts))
    return policies[-1]


def add_advice(engine, *, agent: str, symbol: str, target: str, payload: Dict[str, object], policy_id: Optional[int]) -> Advice:
    advice = Advice(agent=agent, symbol=symbol, target=target, payload_json=dumps_payload(payload), policy_id=policy_id)
    with Session(engine) as session:
        session.add(advice)
        session.commit()
    return advice


def list_advice(engine, *, agent: str) -> List[Advice]:
    with Session(engine) as session:
        advice = session.exec(select(Advice)).all()
    return [a for a in advice if a.agent == agent]


def compact_old_events(engine, cutoff: float) -> None:
    # In-memory stub does not support deletion; keep placeholder for API parity
    _ = engine
    _ = cutoff


def latest_snapshot(engine) -> Optional[LearningSnapshot]:
    with Session(engine) as session:
        snaps = session.exec(select(LearningSnapshot)).all()
    if not snaps:
        return None
    snaps.sort(key=lambda s: s.created_ts)
    return snaps[-1]
