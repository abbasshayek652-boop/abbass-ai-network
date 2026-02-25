from __future__ import annotations

import asyncio
import contextlib
import os
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from analytics.signal_strength import evaluate
from ai.base_agent import Agent
from ai.settings import settings
from learning.data_schema import LearningState, ensure_engine
from learning.eval.monitor import DriftMonitor
from learning.features.online import OnlineFeatureStore
from learning.ingest import add_advice
from learning.jobs.hourly_refresh import refresh_online_features
from learning.jobs.nightly import run_nightly
from learning.policy import registry
from learning.snapshots import load_snapshot, save_snapshot
from telemetry.learning_metrics import (
    learning_advice_total,
    learning_drift_events_total,
    learning_score_latency_ms,
    learning_train_runs_total,
)


@dataclass
class AdviceRecord:
    score: float
    signal: str
    updated_ts: float


class LearningEngine(Agent):
    name = "learning"
    description = "Aggregates agent telemetry and produces policy advice."

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.running = False
        self.mode = config.get("mode", "shadow")
        db_url = config.get("db_url") or os.getenv("MOTHER_LEARNING_DB", "sqlite:///mother_learning.db")
        redis_url = config.get("redis_url") or settings.redis_url
        self.engine = ensure_engine(db_url)
        self.feature_store = OnlineFeatureStore(redis_url)
        self.state = LearningState()
        self.last_error: Optional[str] = None
        self.last_tick_ts: float = 0.0
        self.last_scores: Dict[str, AdviceRecord] = {}
        self.training_task: Optional[asyncio.Task] = None
        self.symbols: List[str] = config.get("symbols", ["BTC/USDT"])
        self.policy_constraints = config.get(
            "policy_max_caps", {"max_notional_per_trade": 15.0, "max_total_exposure_usdt": 150.0}
        )
        self.promotion_thresholds = config.get(
            "promotion_thresholds", {"sharpe_min": 0.8, "max_dd_pct": 0.1, "qc_rate_max": 0.02}
        )
        self.session_resume = bool(config.get("resume", True))
        self.train_interval = float(config.get("train_interval_seconds", 60.0))
        self.snapshot_interval = int(config.get("snapshot_interval_ticks", 5))
        self.tick_count = 0
        self.drift_monitor = DriftMonitor()
        self._training_lock = asyncio.Lock()

    async def start(self) -> None:
        self.running = True
        if self.session_resume:
            snapshot = load_snapshot(self.engine)
            if snapshot:
                state = snapshot.get("state", {})
                self.state = LearningState(**state)
                scores = snapshot.get("scores", {})
                self.last_scores = {
                    symbol: AdviceRecord(score=payload["score"], signal=payload["signal"], updated_ts=payload["updated_ts"])
                    for symbol, payload in scores.items()
                }
        await self._maybe_schedule_training(force=True)

    async def stop(self) -> None:
        self.running = False
        if self.training_task:
            self.training_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.training_task
        save_snapshot(
            self.engine,
            {
                "state": asdict(self.state),
                "scores": {symbol: asdict(record) for symbol, record in self.last_scores.items()},
                "last_tick_ts": self.last_tick_ts,
            },
        )

    async def status(self) -> Dict[str, Any]:
        latest_policy = registry.latest_policy(self.engine)
        return {
            "running": self.running,
            "mode": self.mode,
            "symbols": self.symbols,
            "last_tick_ts": self.last_tick_ts,
            "last_error": self.last_error,
            "last_train_ts": self.state.last_train_ts,
            "last_eval_ts": self.state.last_eval_ts,
            "active_policy_version": self.state.active_policy_version,
            "last_scores": {symbol: asdict(record) for symbol, record in self.last_scores.items()},
            "policy_stage": latest_policy.stage if latest_policy else None,
        }

    async def on_tick(self) -> None:
        if not self.running:
            return
        start = time.time()
        try:
            refresh = refresh_online_features(self.engine, self.feature_store, self.state.last_event_ts)
            self.state.last_event_ts = refresh["latest_ts"]
            await self._emit_advice()
            await self._maybe_schedule_training()
            self.tick_count += 1
            if self.tick_count % self.snapshot_interval == 0:
                save_snapshot(
                    self.engine,
                    {
                        "state": asdict(self.state),
                        "scores": {symbol: asdict(record) for symbol, record in self.last_scores.items()},
                        "last_tick_ts": self.last_tick_ts,
                    },
                )
            self.last_error = None
        except Exception as exc:  # pragma: no cover - protective guard
            self.last_error = str(exc)
        finally:
            self.last_tick_ts = time.time()
            learning_score_latency_ms.labels("learning").set((time.time() - start) * 1000)

    async def _emit_advice(self) -> None:
        for symbol in self.symbols:
            features = self.feature_store.get(symbol)
            if not features:
                continue
            momentum = float(features.get("rolling_return", 0.0))
            volatility = float(min(1.0, max(0.0, features.get("rolling_vol", 0.0))))
            news = 0.5
            outcome = evaluate(momentum, volatility, news)
            record = AdviceRecord(score=float(outcome["score"]), signal=str(outcome["signal"]), updated_ts=time.time())
            self.last_scores[symbol] = record
            add_advice(
                self.engine,
                agent=self.name,
                symbol=symbol,
                target="policy",
                payload={"score": record.score, "signal": record.signal, "features": features},
                policy_id=self.state.active_policy_version,
            )
            learning_advice_total.labels(symbol, "policy").inc()
            drift = self.drift_monitor.check(symbol, features.values())
            if drift.triggered:
                learning_drift_events_total.labels(symbol, drift.metric).inc()

    async def _maybe_schedule_training(self, force: bool = False) -> None:
        if not force and time.time() - self.state.last_train_ts < self.train_interval:
            return
        if self.training_task and not self.training_task.done():
            return
        async with self._training_lock:
            if self.training_task and not self.training_task.done():
                return
            self.training_task = asyncio.create_task(self._run_training())

    async def _run_training(self) -> None:
        try:
            for symbol in self.symbols:
                run = await run_nightly(self.engine, symbol=symbol, constraints=self.policy_constraints)
                if run.get("created"):
                    policy = registry.latest_policy(self.engine, "shadow")
                    if policy:
                        self.state.active_policy_version = policy.version
            self.state.last_train_ts = time.time()
            learning_train_runs_total.labels(self.mode).inc()
        except Exception as exc:  # pragma: no cover - guard
            self.last_error = str(exc)

