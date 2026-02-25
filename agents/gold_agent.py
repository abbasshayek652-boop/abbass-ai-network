from __future__ import annotations

from typing import Any, Dict

from agents.crypto_agent import CryptoTradingAgent


class GoldTradingAgent(CryptoTradingAgent):
    """Tokenised gold trading agent leveraging the crypto stack."""

    name = "gold"
    description = "Trades tokenised gold pairs with strict risk controls."

    _DEFAULT_ALLOWED = ["PAXG/USDT"]
    _DEFAULT_EXCHANGES = ["binance", "okx", "bitget"]

    def __init__(self, config: Dict[str, Any]) -> None:
        merged: Dict[str, Any] = dict(config)
        merged.setdefault("allowed_pairs", list(self._DEFAULT_ALLOWED))
        merged.setdefault("router_exchanges", list(self._DEFAULT_EXCHANGES))
        merged.setdefault("tick_seconds", 20)
        merged.setdefault("timeframe", "1m")
        merged.setdefault("strategy", "momentum_ema")
        if "mode" not in merged:
            merged["mode"] = "shadow" if bool(merged.get("paper", True)) else "canary"
        super().__init__(merged)
