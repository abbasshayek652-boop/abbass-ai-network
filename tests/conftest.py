from __future__ import annotations

import asyncio
import uuid

import pytest

import gateway
from ai.settings import settings
from gateway_pkg.auth import issue_jwt


@pytest.fixture(scope="session", autouse=True)
def configure() -> None:
    settings.jwt_secret = "test-secret"
    settings.api_key = "test-key"
    asyncio.run(gateway.on_startup())
    yield
    asyncio.run(gateway.on_shutdown())


@pytest.fixture
def correlation_id() -> str:
    return str(uuid.uuid4())

