from __future__ import annotations

import asyncio
from typing import List

from oms.orders import OrderIntent


async def execute_twap(
    router,
    executor,
    intent: OrderIntent,
    *,
    total_notional: float,
    price: float,
    seconds: int,
    max_slices: int = 3,
    slippage_bps: int = 0,
) -> List[dict]:
    slices = max(1, min(max_slices, int(max(seconds // 5, 1))))
    qty_per_slice = intent.qty / slices
    responses: List[dict] = []
    for idx in range(slices):
        child = OrderIntent(
            symbol=intent.symbol,
            side=intent.side,
            type=intent.type,
            qty=qty_per_slice,
            client_id=f"{intent.client_id}-twap-{idx}",
        )
        success, payload, venue = await router.execute(
            child,
            executor,
            slippage_bps=slippage_bps,
        )
        payload["venue"] = venue
        responses.append(payload)
        if idx < slices - 1:
            await asyncio.sleep(max(seconds / max(slices - 1, 1), 0))
    return responses


def apply_slippage(price: float, side: str, slippage_bps: int) -> float:
    if slippage_bps <= 0:
        return price
    slip = price * (slippage_bps / 10_000)
    if side == "buy":
        return price + slip
    return price - slip

