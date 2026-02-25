from __future__ import annotations

import asyncio
import types
import uuid

import gateway
from gateway import Command
from gateway.auth import issue_jwt, require


class DummyRequest:
    def __init__(self, correlation_id: str) -> None:
        self.state = types.SimpleNamespace(correlation_id=correlation_id)
        self.client = types.SimpleNamespace(host="test")


class JsonRequest(DummyRequest):
    def __init__(self, correlation_id: str, payload: dict[str, object]) -> None:
        super().__init__(correlation_id)
        self._payload = payload

    async def json(self) -> dict[str, object]:
        return self._payload


def test_rbac_controls() -> None:
    async def runner() -> None:
        viewer_token = issue_jwt("viewer@example.com", "viewer")
        viewer_request = DummyRequest(str(uuid.uuid4()))
        viewer_dep = require("operator")
        try:
            await viewer_dep(viewer_request, authorization=f"Bearer {viewer_token}", x_api_key=None)
        except Exception as exc:  # noqa: BLE001
            assert getattr(exc, "status_code", None) == 403
        else:
            raise AssertionError("viewer should not pass operator guard")

        operator_token = issue_jwt("operator@example.com", "operator")
        operator_request = DummyRequest(str(uuid.uuid4()))
        operator_ctx = await viewer_dep(
            operator_request,
            authorization=f"Bearer {operator_token}",
            x_api_key=None,
        )
        start_result = await gateway.start_agent(Command(agent_key="learning"), operator_request, operator_ctx)
        assert start_result["ok"] is True
        stop_result = await gateway.stop_agent(Command(agent_key="learning"), operator_request, operator_ctx)
        assert stop_result["ok"] is True

        admin_token = issue_jwt("admin@example.com", "admin")
        admin_request = JsonRequest(str(uuid.uuid4()), {"agents": []})
        admin_dep = require("admin")
        admin_ctx = await admin_dep(admin_request, authorization=f"Bearer {admin_token}", x_api_key=None)
        validate = await gateway.registry_validate(admin_request, admin_ctx)
        assert validate["ok"] is True
        dryrun = await gateway.registry_dryrun(JsonRequest(str(uuid.uuid4()), {"agents": []}), admin_ctx)
        assert dryrun["ok"] is True

    asyncio.run(runner())
