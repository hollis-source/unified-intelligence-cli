# src/entities/agent.py - Pure, no deps
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Task:
    description: str
    priority: int = 1
    task_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)

@dataclass
class Agent:
    role: str  # e.g., "coordinator", "coder"
    capabilities: List[str]  # e.g., ["code_gen", "test"]

    def can_handle(self, task: Task) -> bool:
        return any(cap in task.description.lower() for cap in self.capabilities)