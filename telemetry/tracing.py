from __future__ import annotations

import contextlib
from contextlib import asynccontextmanager
from typing import AsyncIterator, Iterator

try:  # pragma: no cover - optional dependency
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
except Exception:  # pragma: no cover - fallback to no-op tracer
    trace = None  # type: ignore


class _NoopSpan:
    def __init__(self, name: str) -> None:
        self.name = name

    def __enter__(self) -> "_NoopSpan":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        return None

    async def __aenter__(self) -> "_NoopSpan":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        return None


class Tracing:
    """Simple OpenTelemetry integration with graceful degradation."""

    def __init__(self, service_name: str, otlp_endpoint: str | None = None) -> None:
        self._service_name = service_name
        self._otlp_endpoint = otlp_endpoint
        self._tracer = None
        if trace is not None:
            resource = Resource.create({"service.name": service_name})
            provider = TracerProvider(resource=resource)
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
            if otlp_endpoint:
                provider.add_span_processor(
                    BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
                )
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(service_name)

    @contextlib.contextmanager
    def span(self, name: str) -> Iterator[object]:
        if self._tracer is None:
            yield _NoopSpan(name)
            return
        with self._tracer.start_as_current_span(name):  # type: ignore[attr-defined]
            yield

    @asynccontextmanager
    async def span_async(self, name: str) -> AsyncIterator[object]:
        if self._tracer is None:
            yield _NoopSpan(name)
            return
        with self._tracer.start_as_current_span(name):  # type: ignore[attr-defined]
            yield


def build_tracer(service_name: str, endpoint: str | None) -> Tracing:
    return Tracing(service_name, endpoint)

