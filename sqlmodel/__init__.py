from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional


class _FieldSpec:
    def __init__(self, default: Any = None, *, default_factory: Callable[[], Any] | None = None) -> None:
        self.default = default
        self.default_factory = default_factory


def Field(
    default: Any = None,
    *,
    primary_key: bool = False,  # pragma: no cover - unused but kept for signature parity
    default_factory: Callable[[], Any] | None = None,
) -> _FieldSpec:
    return _FieldSpec(default=default, default_factory=default_factory)


class _Metadata:
    def create_all(self, engine: "Engine") -> None:
        _ENGINE_STORAGE.setdefault(engine, {})


class _SQLModelMeta(type):
    def __new__(mcls, name: str, bases: tuple[type, ...], namespace: Dict[str, Any], **kwargs: Any):
        field_specs: Dict[str, _FieldSpec] = {}
        for base in bases:
            field_specs.update(getattr(base, "_field_specs", {}))
        for key, value in list(namespace.items()):
            if isinstance(value, _FieldSpec):
                field_specs[key] = value
                namespace.pop(key)
        namespace["_field_specs"] = field_specs
        return super().__new__(mcls, name, bases, namespace)


class SQLModel(metaclass=_SQLModelMeta):
    metadata = _Metadata()

    def __init__(self, **kwargs: Any) -> None:
        annotations: Dict[str, Any] = {}
        for cls in reversed(self.__class__.mro()):
            annotations.update(getattr(cls, "__annotations__", {}))
        specs: Dict[str, _FieldSpec] = getattr(self, "_field_specs", {})
        for attr in annotations:
            if attr in kwargs:
                value = kwargs.pop(attr)
            elif attr in specs:
                spec = specs[attr]
                if spec.default_factory is not None:
                    value = spec.default_factory()
                else:
                    value = spec.default
            else:
                value = kwargs.pop(attr, None)
            setattr(self, attr, value)
        for key, value in kwargs.items():
            setattr(self, key, value)


class Engine:
    def __init__(self, url: str) -> None:
        self.url = url

    def __hash__(self) -> int:  # pragma: no cover - deterministic hashing
        return hash(id(self))


_ENGINE_STORAGE: Dict[Engine, Dict[type, List[Any]]] = {}
_ENGINE_REGISTRY: Dict[str, Engine] = {}


def create_engine(url: str, echo: bool = False, connect_args: Optional[Dict[str, Any]] = None) -> Engine:
    engine = _ENGINE_REGISTRY.get(url)
    if engine is None:
        engine = Engine(url)
        _ENGINE_REGISTRY[url] = engine
    _ENGINE_STORAGE.setdefault(engine, {})
    return engine


class Session:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def __enter__(self) -> "Session":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - context manager cleanup
        return None

    def add(self, obj: Any) -> None:
        storage = _ENGINE_STORAGE.setdefault(self.engine, {}).setdefault(type(obj), [])
        if getattr(obj, "id", None) is None:
            setattr(obj, "id", len(storage) + 1)
        storage.append(obj)

    def commit(self) -> None:  # pragma: no cover - transaction is a no-op in stub
        return None

    def exec(self, query: "Select") -> "Result":
        data = list(_ENGINE_STORAGE.setdefault(self.engine, {}).get(query.model, []))
        return Result(data)


class Result:
    def __init__(self, data: Iterable[Any]) -> None:
        self._data = list(data)

    def all(self) -> List[Any]:
        return list(self._data)


class Select:
    def __init__(self, model: type) -> None:
        self.model = model


def select(model: type) -> Select:
    return Select(model)
