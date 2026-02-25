from __future__ import annotations

import time

from learning.features.offline import build_offline_dataset, dataset_hash, time_series_split
from learning.ingest import add_market_snapshot, add_trade
from learning.data_schema import ensure_engine


def _engine() -> object:
    return ensure_engine(f"sqlite:///test_learning_features_{time.time()}")


def test_time_split_no_overlap() -> None:
    engine = _engine()
    for idx in range(10):
        add_market_snapshot(engine, symbol="BTC/USDT", price=100 + idx, volume=10 + idx, features={})
        add_trade(
            engine,
            agent="crypto",
            symbol="BTC/USDT",
            side="buy" if idx % 2 else "sell",
            qty=0.1,
            price=100 + idx,
            pnl=1.0 if idx % 2 else -0.5,
            paper=True,
        )
    dataset = build_offline_dataset(engine, "BTC/USDT")
    train, test = time_series_split(dataset, train_fraction=0.6)
    assert train[-1]["ts"] <= test[0]["ts"]
    assert len(train) > 0 and len(test) > 0
    assert dataset_hash(dataset) != "empty"
