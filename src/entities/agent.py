# src/entities/agent.py - Pure, no deps
import difflib
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
        desc_words = task.description.lower().split()
        return any(any(difflib.SequenceMatcher(None, cap.lower(), word).ratio() > 0.8 for word in desc_words) for cap in self.capabilities)