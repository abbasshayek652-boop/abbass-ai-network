from __future__ import annotations

from prometheus_client import Counter, Gauge


ticks_total = Counter("crypto_ticks_total", "Total ticks processed", ["agent"])
orders_total = Counter(
    "crypto_orders_total",
    "Orders placed",
    ["agent", "symbol", "side", "mode"],
)
exposure_usdt = Gauge(
    "crypto_exposure_usdt", "Current exposure in USDT", ["agent", "symbol"]
)
cash_usdt = Gauge("crypto_cash_usdt", "Current cash USDT", ["agent"])
last_score = Gauge("crypto_last_score", "Last score per symbol", ["agent", "symbol"])
data_qc_fail_total = Counter(
    "crypto_data_qc_fail_total",
    "Number of data quality failures per symbol",
    ["agent", "symbol"],
)
router_failover_total = Counter(
    "crypto_router_failover_total",
    "Number of times routing required failover",
    ["agent", "from_exchange", "to_exchange"],
)
canary_live_ratio = Gauge(
    "crypto_canary_live_ratio",
    "Fraction of trade routed to live venue during canary",
    ["agent", "symbol"],
)
snapshot_writes_total = Counter(
    "crypto_snapshot_writes_total",
    "Snapshots persisted to storage",
    ["agent"],
)
