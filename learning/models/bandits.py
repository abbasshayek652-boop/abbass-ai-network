from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class ArmState:
    wins: float = 0.0
    plays: float = 0.0

    def value(self) -> float:
        return self.wins / self.plays if self.plays else 0.0


@dataclass
class EpsilonGreedyBandit:
    arms: Dict[str, ArmState] = field(default_factory=dict)
    epsilon: float = 0.1

    def register_arm(self, arm: str) -> None:
        self.arms.setdefault(arm, ArmState())

    def choose(self) -> str:
        if not self.arms:
            raise ValueError("no arms registered")
        if random.random() < self.epsilon:
            return random.choice(list(self.arms.keys()))
        return max(self.arms.items(), key=lambda item: item[1].value())[0]

    def update(self, arm: str, reward: float) -> None:
        state = self.arms.setdefault(arm, ArmState())
        state.plays += 1
        state.wins += reward

    def as_dict(self) -> Dict[str, Dict[str, float]]:
        return {arm: {"wins": state.wins, "plays": state.plays} for arm, state in self.arms.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Dict[str, float]], epsilon: float = 0.1) -> "EpsilonGreedyBandit":
        bandit = cls(epsilon=epsilon)
        for arm, payload in data.items():
            bandit.arms[arm] = ArmState(wins=payload.get("wins", 0.0), plays=payload.get("plays", 0.0))
        return bandit
