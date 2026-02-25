from __future__ import annotations

from ai.registry import AgentSpec, Registry


def test_registry_validation() -> None:
    registry = Registry(
        agents=[AgentSpec(key="learning", module="ai.learning_engine", class_name="LearningAgent")]
    )
    assert registry.agents[0].key == "learning"

