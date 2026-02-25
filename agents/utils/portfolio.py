from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Position:
    qty: float = 0.0
    avg_price: float = 0.0


@dataclass
class Portfolio:
    cash_usdt: float = 100.0
    positions: dict[str, Position] = field(default_factory=dict)

    def buy(self, symbol: str, qty: float, price: float, fee: float) -> None:
        cost = qty * price + fee
        if cost > self.cash_usdt:
            raise ValueError("insufficient cash")
        self.cash_usdt -= cost
        pos = self.positions.get(symbol, Position())
        new_qty = pos.qty + qty
        pos.avg_price = (
            (pos.avg_price * pos.qty + price * qty) / new_qty if new_qty > 0 else 0.0
        )
        pos.qty = new_qty
        self.positions[symbol] = pos

    def sell(self, symbol: str, qty: float, price: float, fee: float) -> None:
        pos = self.positions.get(symbol, Position())
        if qty > pos.qty + 1e-12:
            raise ValueError("insufficient position")
        self.cash_usdt += qty * price - fee
        pos.qty -= qty
        if pos.qty <= 1e-12:
            self.positions.pop(symbol, None)
        else:
            self.positions[symbol] = pos
