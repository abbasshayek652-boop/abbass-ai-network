"""Minimal offline fallback for :mod:`pydantic_settings`.

This implementation is intentionally small and supports only the features the
project requires: a ``BaseSettings`` class that reads environment variables and
an ``SettingsConfigDict`` helper mirroring Pydantic's signature.  It keeps the
same import surface so the main code can continue to target the official
library without modification.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from pydantic import BaseModel

__all__ = ["BaseSettings", "SettingsConfigDict"]


class SettingsConfigDict(dict):
    """Dictionary-style container for settings configuration options."""


class BaseSettings(BaseModel):
    model_config: SettingsConfigDict = SettingsConfigDict()

    def __init__(self, **values: Any) -> None:
        config = getattr(self, "model_config", SettingsConfigDict())
        env_prefix = config.get("env_prefix", "")
        env_file = config.get("env_file")
        case_sensitive = bool(config.get("case_sensitive", False))

        env_values = _load_env_file(env_file, case_sensitive)
        environ = _normalise_map(dict(os.environ), case_sensitive)

        data: Dict[str, Any] = dict(values)
        for field in self.__fields__:
            if field in data:
                continue
            key = f"{env_prefix}{field}"
            lookup = key if case_sensitive else key.upper()
            if lookup in environ:
                data[field] = environ[lookup]
            elif lookup in env_values:
                data[field] = env_values[lookup]

        super().__init__(**data)


def _load_env_file(env_file: str | None, case_sensitive: bool) -> Dict[str, str]:
    if not env_file:
        return {}
    path = Path(env_file)
    if not path.exists():
        return {}

    content = path.read_text(encoding="utf-8")
    pairs: Dict[str, str] = {}
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not case_sensitive:
            key = key.upper()
        pairs[key] = value
    return pairs


def _normalise_map(data: Dict[str, str], case_sensitive: bool) -> Dict[str, str]:
    if case_sensitive:
        return data
    return {key.upper(): value for key, value in data.items()}
