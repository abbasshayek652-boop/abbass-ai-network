from __future__ import annotations

from typing import Dict

from learning.features.online import OnlineFeatureStore
from learning.ingest import list_events_since


def refresh_online_features(engine, store: OnlineFeatureStore, since_ts: float) -> Dict[str, float]:
    events = list_events_since(engine, since_ts, kinds=["market_snapshot"])
    latest_ts = since_ts
    for event in events:
        payload = {}
        try:
            import orjson

            payload = orjson.loads(event.payload_json)
        except Exception:
            import json

            payload = json.loads(event.payload_json)
        symbol = payload.get("symbol")
        if not symbol:
            continue
        features = {k: float(v) for k, v in payload.get("features", {}).items() if isinstance(v, (int, float))}
        store.set(symbol, features)
        latest_ts = max(latest_ts, event.ts)
    return {"latest_ts": latest_ts, "processed": len(events)}
