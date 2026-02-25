from __future__ import annotations

import datetime as dt
from typing import List, Tuple


TimeWindow = Tuple[str, str]


def in_trading_session(now: dt.datetime, windows: List[TimeWindow]) -> bool:
    current = now.strftime("%H:%M")
    for start, end in windows:
        if start <= current <= end:
            return True
    return False
