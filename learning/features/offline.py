from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from sqlmodel import Session, select

from learning.data_schema import MarketSnapshot, Trade

Dataset = List[Dict[str, float]]


def _rolling(values: List[float], window: int, fn) -> List[float]:
    result: List[float] = []
    for idx in range(len(values)):
        start = max(0, idx - window + 1)
        window_slice = values[start : idx + 1]
        result.append(fn(window_slice))
    return result


def _std(values: List[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / max(1, len(values) - 1)
    return math.sqrt(max(variance, 0.0))


def _mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def build_offline_dataset(engine, symbol: str) -> Dataset:
    with Session(engine) as session:
        snaps = [snap for snap in session.exec(select(MarketSnapshot)).all() if snap.symbol == symbol]
        trades = [trade for trade in session.exec(select(Trade)).all() if trade.symbol == symbol]
    if not snaps:
        return []
    snaps.sort(key=lambda snap: snap.ts)
    pnl_map = {trade.ts: trade.pnl for trade in trades}
    prices = [snap.price for snap in snaps]
    volumes = [snap.volume for snap in snaps]
    returns: List[float] = [0.0]
    for idx in range(1, len(prices)):
        prev = prices[idx - 1]
        curr = prices[idx]
        returns.append((curr - prev) / prev if prev else 0.0)
    forward: List[float] = []
    for idx in range(len(prices)):
        if idx + 1 < len(prices) and prices[idx]:
            forward.append(prices[idx + 1] / prices[idx] - 1.0)
        else:
            forward.append(0.0)
    rolling_vol = _rolling(returns, 5, _std)
    rolling_return = _rolling(returns, 5, _mean)
    dataset: Dataset = []
    for idx, snap in enumerate(snaps):
        row = {
            "ts": float(snap.ts),
            "price": float(prices[idx]),
            "volume": float(volumes[idx]),
            "return": float(returns[idx]),
            "forward_return": float(forward[idx]),
            "label": 1.0 if forward[idx] > 0 else 0.0,
            "rolling_vol": float(min(max(rolling_vol[idx], 0.0), 1.0)),
            "rolling_return": float(rolling_return[idx]),
            "pnl": float(pnl_map.get(snap.ts, 0.0)),
        }
        dataset.append(row)
    return dataset


def time_series_split(dataset: Dataset, train_fraction: float = 0.7) -> Tuple[Dataset, Dataset]:
    if not dataset:
        return [], []
    cutoff = max(1, int(len(dataset) * train_fraction))
    train = dataset[:cutoff]
    test = dataset[cutoff:]
    if not test:
        test = dataset[cutoff - 1 : cutoff]
    return train, test


def dataset_hash(dataset: Dataset) -> str:
    if not dataset:
        return "empty"
    entries = []
    for row in dataset:
        items = tuple(sorted((key, round(value, 8)) for key, value in row.items()))
        entries.append(items)
    return str(hash(tuple(entries)))


def latest_snapshot_pair(engine, symbol: str) -> Tuple[Dataset, Optional[Dataset]]:
    dataset = build_offline_dataset(engine, symbol)
    if not dataset:
        return dataset, None
    train, test = time_series_split(dataset)
    return train, test
