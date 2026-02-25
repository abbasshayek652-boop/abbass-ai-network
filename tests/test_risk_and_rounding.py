from __future__ import annotations

from agents.utils.market_rules import conform_qty
from risk.cooldowns import Cooldown, CooldownState
from risk.rules import RiskCaps, check_pre_trade


def test_conform_qty_rounds_down():
    markets = {"BTC/USDT": {"stepSize": 0.01}}
    assert conform_qty("BTC/USDT", 0.123, markets) == 0.12


def test_pre_trade_enforces_notional_cap():
    caps = RiskCaps(max_notional_per_trade=15.0)
    ok, reason = check_pre_trade("BTC/USDT", price=100.0, qty=0.2, caps=caps, exposures={}, total_exposure=0.0)
    assert not ok
    assert reason == "cap:notional"


def test_duplicate_cooldown_blocks_reorders():
    cd = Cooldown(duplicate_secs=5)
    state = CooldownState()
    assert state.too_soon("BTC/USDT", "buy", cd) is False
    assert state.too_soon("BTC/USDT", "buy", cd) is True
