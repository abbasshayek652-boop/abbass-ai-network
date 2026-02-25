from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    side: str
    type: str
    qty: float
    client_id: Optional[str] = None
