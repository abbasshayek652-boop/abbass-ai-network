from data.quality import validate_ohlcv
from risk.portfolio_limits import dynamic_notional_cap
from risk.rules import RiskCaps


def test_qc_rejects_large_gap():
    now = 1_700_000_000
    ohlcv = [
        [now - 120, 100, 100, 100, 100, 1],
        [now - 60, 100, 100, 100, 120, 1],
    ]
    ok, reason = validate_ohlcv("BTC/USDT", ohlcv, max_gap_pct=0.05)
    assert not ok
    assert reason == "gap"


def test_dynamic_notional_cap_never_exceeds_limit():
    caps = RiskCaps()
    cap = dynamic_notional_cap("BTC/USDT", volatility=0.5, caps=caps, per_symbol_target=50.0)
    assert cap <= 15.0

