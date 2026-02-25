"""Single entrypoint for running or smoke-testing Mother AI."""
from __future__ import annotations

import argparse
import json
import os
from typing import Any


def _smoke_test() -> int:
    """Run a lightweight import/startup smoke test without launching a server."""
    from ai.registry import hydrate_agents, load_registry
    from gateway import app

    registry = load_registry()
    agents = hydrate_agents(registry)
    payload: dict[str, Any] = {
        "ok": True,
        "app": getattr(app, "title", "Mother AI Gateway"),
        "agents_loaded": sorted(agents.keys()),
    }
    print(json.dumps(payload))
    return 0


def _run_server() -> None:
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("mother_ai.gateway:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Mother AI gateway")
    parser.add_argument("--smoke-test", action="store_true", help="Validate app imports and registry loading")
    args = parser.parse_args()

    if args.smoke_test:
        raise SystemExit(_smoke_test())
    _run_server()
