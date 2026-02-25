from __future__ import annotations

from typing import Tuple

from ai.utils.retry import with_retry


class Executor:
    def __init__(self, adapter, paper: bool, fee_bps: int = 10) -> None:
        self.adapter = adapter
        self.paper = paper
        self.fee = fee_bps / 10_000.0

    async def execute(self, intent, *, adapter=None, slippage_bps: int = 0) -> Tuple[bool, dict]:
        adapter = adapter or self.adapter
        if adapter is None:
            raise RuntimeError("Executor requires an adapter instance")
        if self.paper:
            ticker = await adapter.fetch_ticker(intent.symbol)
            price = float(ticker.get("last") or ticker.get("close"))
            if slippage_bps:
                price = price * (1 + (slippage_bps / 10_000) * (1 if intent.side == "buy" else -1))
            fee = price * intent.qty * self.fee
            return True, {
                "filled": intent.qty,
                "price": price,
                "fee": fee,
                "orderId": f"paper-{intent.side}-{price}",
            }

        async def _live() -> dict:
            return await adapter.create_order(
                intent.symbol, intent.side, intent.type, intent.qty
            )

        result = await with_retry(_live, attempts=3, base_delay=0.5)
        return True, result
