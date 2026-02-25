from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable

import pandas as pd

from strategies.momentum_ema import MomentumEMAStrategy


def _window_ranges(length: int, window: int, step: int) -> Iterable[tuple[int, int]]:
    for start in range(0, length - window, step):
        yield start, start + window


def walk_forward(csv_dir: str, output_dir: str, train: int = 500, validate: int = 200) -> None:
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    params: Dict[str, Dict[str, int]] = {}
    for csv_file in Path(csv_dir).glob("*.csv"):
        df = pd.read_csv(csv_file)
        closes = df["close"].values
        best_score = float("-inf")
        best_params = {"ema_fast": 12, "ema_slow": 26}
        for fast in range(5, 20, 5):
            for slow in range(20, 60, 10):
                strat = MomentumEMAStrategy(ema_fast=fast, ema_slow=slow)
                score = 0.0
                for start, end in _window_ranges(len(closes), train + validate, validate):
                    train_slice = closes[start : start + train]
                    validate_slice = closes[start + train : end]
                    if len(train_slice) < train or len(validate_slice) < validate:
                        continue
                    gain = (validate_slice[-1] - validate_slice[0]) / validate_slice[0]
                    score += gain * (fast / slow)
                if score > best_score:
                    best_score = score
                    best_params = {"ema_fast": fast, "ema_slow": slow}
        params[csv_file.stem] = best_params
    param_file = out_path / "momentum_ema.json"
    param_file.write_text(json.dumps(params, indent=2))

