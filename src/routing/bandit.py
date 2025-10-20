from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class EpsilonGreedyBandit:
    variants: List[str]
    epsilon: float = 0.1
    counts: Dict[str, int] = field(default_factory=dict)
    rewards: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        for v in self.variants:
            self.counts.setdefault(v, 0)
            self.rewards.setdefault(v, 0.0)
        # env override (0..1)
        try:
            env_eps = float(os.getenv("RAG_BANDIT_EPSILON", str(self.epsilon)))
            if 0.0 <= env_eps <= 1.0:
                self.epsilon = env_eps
        except Exception:
            pass

    def select(self) -> str:
        # Explore
        if random.random() < self.epsilon:
            return random.choice(self.variants)
        # Exploit (average reward)
        def avg(v: str) -> float:
            c = self.counts.get(v, 0)
            return (self.rewards.get(v, 0.0) / c) if c > 0 else 0.0
        best = max(self.variants, key=lambda v: (avg(v), -self.counts.get(v, 0)))
        return best

    def update(self, variant: str, reward: float) -> None:
        if variant not in self.variants:
            return
        self.counts[variant] = self.counts.get(variant, 0) + 1
        self.rewards[variant] = self.rewards.get(variant, 0.0) + float(reward or 0.0)

