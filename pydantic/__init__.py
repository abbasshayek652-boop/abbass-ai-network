"""Lightweight fallback implementations for a subset of Pydantic APIs.

This module exists solely so the project can run its minimal unit tests in
offline environments where installing the real ``pydantic`` package is not
possible.  It intentionally implements only the very small surface area that
the codebase relies upon (``BaseModel`` and ``Field``) and should not be
considered a drop-in replacement for production use.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Type, Union, get_args, get_origin

__all__ = ["BaseModel", "Field", "ValidationError", "field_validator"]


_MISSING: object = object()


class ValidationError(ValueError):
    """Minimal validation error used to mimic pydantic failures."""


@dataclass
class _FieldInfo:
    default: Any = _MISSING
    default_factory: Any = _MISSING


def Field(default: Any = _MISSING, *, default_factory: Any = _MISSING) -> _FieldInfo:
    """Return a lightweight descriptor carrying default metadata."""

    return _FieldInfo(default=default, default_factory=default_factory)


class BaseModel:
    """Very small subset of ``pydantic.BaseModel`` features.

    The implementation focuses on deterministic default handling and basic type
    coercion for simple primitives.  It purposefully omits advanced validation
    features; anything beyond the needs of the current codebase should use the
    real Pydantic package.
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:  # pragma: no cover - thin wrapper
        super().__init_subclass__(**kwargs)
        cls.__annotations__ = _collect_annotations(cls)
        cls.__fields__ = _collect_fields(cls)

    def __init__(self, **data: Any) -> None:
        remaining = dict(data)
        for name, meta in self.__fields__.items():
            if name in remaining:
                value = remaining.pop(name)
            else:
                value = _resolve_default(meta)
            value = _coerce_value(self.__annotations__.get(name), value, field_name=name)
            setattr(self, name, value)

        for key, value in remaining.items():
            setattr(self, key, value)

    def model_dump(self) -> Dict[str, Any]:
        """Return instance data as a plain dictionary."""

        return {name: getattr(self, name) for name in self.__fields__.keys()}


def _collect_annotations(cls: Type[BaseModel]) -> Dict[str, Any]:
    annotations: Dict[str, Any] = {}
    for base in reversed(cls.__mro__):
        base_annotations = getattr(base, "__dict__", {}).get("__annotations__", {})
        for name, annotation in base_annotations.items():
            if _is_internal_field(name):
                continue
            annotations[name] = annotation
    return annotations


def _collect_fields(cls: Type[BaseModel]) -> Dict[str, _FieldInfo]:
    annotations = getattr(cls, "__annotations__", {})
    fields: Dict[str, _FieldInfo] = {}
    for base in reversed(cls.__mro__[1:]):
        base_fields = getattr(base, "__fields__", None)
        if base_fields:
            fields.update(base_fields)

    for name in annotations:
        raw_default = cls.__dict__.get(name, getattr(cls, name, _MISSING))
        if isinstance(raw_default, _FieldInfo):
            fields[name] = raw_default
            if name in cls.__dict__:
                delattr(cls, name)
        else:
            if name in fields and raw_default is _MISSING:
                continue
            fields[name] = _FieldInfo(default=raw_default)
    return fields


def _is_internal_field(name: str) -> bool:
    return name.startswith("_") or name in {"model_config"}


def _resolve_default(info: _FieldInfo) -> Any:
    if info.default is not _MISSING:
        return info.default
    if info.default_factory is not _MISSING:
        return info.default_factory()
    raise ValidationError("Missing required field")


def _coerce_value(annotation: Any, value: Any, *, field_name: str) -> Any:
    if annotation is None:
        return value
    if annotation is Any:
        return value

    origin = get_origin(annotation)
    if origin is Union:
        for candidate in get_args(annotation):
            if candidate is type(None):
                if value in (None, ""):
                    return None
                continue
            try:
                return _coerce_value(candidate, value, field_name=field_name)
            except (TypeError, ValueError, ValidationError):
                continue
        return value

    try:
        if annotation in (str, int, float):
            return annotation(value)
        if annotation is bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"1", "true", "yes", "on"}:
                    return True
                if lowered in {"0", "false", "no", "off", ""}:
                    return False
            return bool(value)
        if origin in (list, List):
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                return [item.strip() for item in value.split(",") if item.strip()]
            return list(value)
        if origin in (dict, Dict):
            if isinstance(value, dict):
                return value
            raise TypeError
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"Invalid value for field '{field_name}'") from exc

    return value
def field_validator(*_fields: str, mode: str | None = None):  # noqa: D401
    """Shim that returns the decorated function unchanged."""

    def decorator(func):
        return func

    return decorator

