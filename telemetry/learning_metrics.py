from __future__ import annotations

from prometheus_client import Counter, Gauge


learning_train_runs_total = Counter("learning_train_runs_total", "Number of training runs", ("stage",))
learning_policy_promotions_total = Counter(
    "learning_policy_promotions_total",
    "Policy promotions by stage",
    ("from_stage", "to_stage"),
)
learning_drift_events_total = Counter(
    "learning_drift_events_total",
    "Drift alerts raised",
    ("symbol", "metric"),
)
learning_advice_total = Counter(
    "learning_advice_total",
    "Advice rows emitted",
    ("symbol", "target"),
)
learning_score_latency_ms = Gauge(
    "learning_score_latency_ms",
    "Latency for scoring pipeline",
    ("symbol",),
)
