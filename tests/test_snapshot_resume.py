from persistence.snapshot import load_latest_snapshot, write_snapshot
from sqlmodel import create_engine


def test_snapshot_roundtrip(tmp_path):
    db_path = tmp_path / "snap.db"
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    payload = {"ts": 1.0, "price_cache": {"BTC/USDT": 100.0}}
    write_snapshot(engine, "crypto", payload)
    restored = load_latest_snapshot(engine, "crypto")
    assert restored["price_cache"]["BTC/USDT"] == 100.0

