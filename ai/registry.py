from __future__ import annotations

import importlib
import json
import logging
import pathlib
from typing import Any, Dict, List, Type

from pydantic import BaseModel, Field, ValidationError

from ai.base_agent import Agent

LOGGER = logging.getLogger(__name__)


class AgentSpec(BaseModel):
    key: str
    module: str
    class_name: str
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)


class Registry(BaseModel):
    agents: List[AgentSpec]


def load_registry(path: str = "registry.json") -> Registry:
    """Read and validate the registry definition from disk."""
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    try:
        return Registry(**data)
    except ValidationError as exc:  # pragma: no cover - clarity over coverage
        raise ValueError("Invalid registry configuration") from exc


def _resolve_class(module: str, class_name: str) -> Type[Agent]:
    mod = importlib.import_module(module)
    cls = getattr(mod, class_name)
    if not issubclass(cls, Agent):  # type: ignore[arg-type]
        raise TypeError(f"{class_name} is not an Agent subclass")
    return cls


def hydrate_agents(registry: Registry) -> Dict[str, Agent]:
    """Instantiate all enabled agents from the registry."""
    instances: Dict[str, Agent] = {}
    for spec_data in registry.agents:
        spec = spec_data if isinstance(spec_data, AgentSpec) else AgentSpec(**spec_data)
        if not spec.enabled:
            LOGGER.info("Skipping disabled agent %s", spec.key)
            continue
        cls = _resolve_class(spec.module, spec.class_name)
        LOGGER.info("Hydrating agent %s from %s.%s", spec.key, spec.module, spec.class_name)
        instances[spec.key] = cls(spec.config)
    return instances

