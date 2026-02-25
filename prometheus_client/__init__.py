from __future__ import annotations

from typing import Dict, Tuple

_METRICS: list["_Metric"] = []


class _Value:
    def __init__(self, initial: float = 0.0) -> None:
        self._val = initial

    def get(self) -> float:
        return self._val

    def set(self, value: float) -> None:
        self._val = value

    def inc(self, amount: float = 1.0) -> None:
        self._val += amount


class _MetricChild:
    def __init__(self, metric: "_Metric", key: Tuple[str, ...]) -> None:
        self._metric = metric
        self._key = key
        self._value = metric.values.setdefault(key, _Value())

    def set(self, value: float) -> None:
        self._value.set(value)

    def inc(self, amount: float = 1.0) -> None:
        self._value.inc(amount)


class _Metric:
    def __init__(self, name: str, documentation: str, labelnames: Tuple[str, ...], kind: str):
        self.name = name
        self.documentation = documentation
        self.labelnames = labelnames
        self.values: Dict[Tuple[str, ...], _Value] = {}
        self.kind = kind
        _METRICS.append(self)

    def labels(self, *args: str, **kwargs: str) -> _MetricChild:
        if kwargs:
            key = tuple(kwargs.get(name, "") for name in self.labelnames)
        else:
            key = tuple(args)
        return _MetricChild(self, key)


class Counter(_Metric):
    def __init__(self, name: str, documentation: str, labelnames: Tuple[str, ...]):
        super().__init__(name, documentation, labelnames, "counter")


class Gauge(_Metric):
    def __init__(self, name: str, documentation: str, labelnames: Tuple[str, ...]):
        super().__init__(name, documentation, labelnames, "gauge")


def generate_latest() -> bytes:
    lines = []
    for metric in _METRICS:
        lines.append(f"# HELP {metric.name} {metric.documentation}")
        lines.append(f"# TYPE {metric.name} {metric.kind}")
        if not metric.values:
            lines.append(f"{metric.name} 0")
            continue
        for labels, value in metric.values.items():
            if metric.labelnames:
                parts = [f"{name}=\"{label}\"" for name, label in zip(metric.labelnames, labels)]
                label_block = "{" + ",".join(parts) + "}"
            else:
                label_block = ""
            lines.append(f"{metric.name}{label_block} {value.get()}")
    return "\n".join(lines).encode()


def make_asgi_app():
    async def app(scope, receive, send):
        if scope["type"] != "http":
            raise RuntimeError("Unsupported scope")
        body = generate_latest()
        await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"text/plain; version=0.0.4")]})
        await send({"type": "http.response.body", "body": body})

    return app
