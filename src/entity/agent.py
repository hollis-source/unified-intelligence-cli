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

    # Week 11: Hierarchical agent scaling metadata
    tier: int = 3  # Default Tier 3 (execution), maintains backward compatibility
    parent_agent: Optional[str] = None  # Role of parent agent (for hierarchy)
    specialization: Optional[str] = None  # Domain specialization (e.g., "python", "frontend")

    def can_handle(self, task: Task) -> bool:
        """
        Check if agent can handle task (fuzzy matching).

        Week 6 Fix: Lower threshold to 0.6 for better real-world matching.
        Previous 0.8 threshold was too strict, causing "no agent found" errors.
        """
        desc_words = task.description.lower().split()
        threshold = 0.6  # Lowered from 0.8 (Week 6 bug fix)
        return any(any(difflib.SequenceMatcher(None, cap.lower(), word).ratio() > threshold for word in desc_words) for cap in self.capabilities)