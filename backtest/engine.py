from __future__ import annotations

import pandas as pd

from agents.utils.portfolio import Portfolio
from strategies.momentum_ema import MomentumEMAStrategy


async def run_csv(csv_path: str, fee_bps: int = 10):
    df = pd.read_csv(csv_path)
    strategy = MomentumEMAStrategy()
    portfolio = Portfolio(cash_usdt=100.0)
    for idx in range(50, len(df)):
        window = df.iloc[idx - 50 : idx][
            ["time", "open", "high", "low", "close", "volume"]
        ].values.tolist()
        features = await strategy.compute_features(window)
        sig = await strategy.signal(features)
        price = float(df.iloc[idx]["close"])
        if sig["signal"] == "buy" and portfolio.cash_usdt > 1:
            qty = min(15.0, portfolio.cash_usdt) / price
            fee = price * qty * (fee_bps / 10_000)
            portfolio.buy("BTC/USDT", qty, price, fee)
        elif sig["signal"] == "sell" and "BTC/USDT" in portfolio.positions:
            qty = portfolio.positions["BTC/USDT"].qty
            fee = price * qty * (fee_bps / 10_000)
            portfolio.sell("BTC/USDT", qty, price, fee)
    return portfolio.cash_usdt, {
        symbol: (pos.qty, pos.avg_price) for symbol, pos in portfolio.positions.items()
    }
