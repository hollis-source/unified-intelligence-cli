# src/entities/agent.py - Pure, no deps
from dataclasses import dataclass
from typing import List

@dataclass
class Task:
    description: str
    priority: int = 1

@dataclass
class Agent:
    role: str  # e.g., "coordinator", "coder"
    capabilities: List[str]  # e.g., ["code_gen", "test"]

    def can_handle(self, task: Task) -> bool:
        return any(cap in task.description.lower() for cap in self.capabilities)