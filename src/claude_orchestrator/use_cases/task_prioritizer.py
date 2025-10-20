"""TaskPrioritizer - Priority ranking for generated tasks.

Ranks tasks by impact, effort, and urgency using health score deltas and metrics trends.

Clean Architecture: Use Case layer
SOLID: SRP - Single responsibility for task prioritization
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from src.claude_orchestrator.entities.generated_task import GeneratedTask

logger = logging.getLogger(__name__)


@dataclass
class TaskScore:
    """Scoring breakdown for a task."""
    task: GeneratedTask
    impact_score: float  # 0-100
    effort_score: float  # 0-100 (higher = less effort)
    urgency_score: float  # 0-100
    total_score: float  # weighted sum
    rank: int = 0


class TaskPrioritizer:
    """
    Ranks tasks by impact, effort, and urgency.
    
    Scoring formula:
    - Impact (50%): Estimated health score delta or metric improvement
    - Effort (30%): Inverse of estimated minutes (prefer quick wins)
    - Urgency (20%): Based on failing tests, degrading metrics, low coverage
    
    Usage:
        prioritizer = TaskPrioritizer()
        ranked = prioritizer.rank_tasks(tasks, system_context)
        top_task = ranked[0].task
    """
    
    # Weights for scoring
    IMPACT_WEIGHT = 0.50
    EFFORT_WEIGHT = 0.30
    URGENCY_WEIGHT = 0.20
    
    def __init__(self):
        """Initialize task prioritizer."""
        pass
    
    def rank_tasks(
        self,
        tasks: List[GeneratedTask],
        system_context: Optional[Any] = None,
        task_context: Optional[Any] = None,
    ) -> List[TaskScore]:
        """
        Rank tasks by priority score.
        
        Args:
            tasks: List of GeneratedTask objects
            system_context: Optional SystemContext with health score
            task_context: Optional TaskContext with test failures, coverage
            
        Returns:
            List of TaskScore objects sorted by total_score (descending)
        """
        if not tasks:
            return []
        
        scores = []
        for task in tasks:
            impact = self._compute_impact_score(task, system_context)
            effort = self._compute_effort_score(task)
            urgency = self._compute_urgency_score(task, task_context)
            
            total = (
                impact * self.IMPACT_WEIGHT +
                effort * self.EFFORT_WEIGHT +
                urgency * self.URGENCY_WEIGHT
            )
            
            scores.append(TaskScore(
                task=task,
                impact_score=impact,
                effort_score=effort,
                urgency_score=urgency,
                total_score=total,
            ))
        
        # Sort by total score descending
        scores.sort(key=lambda s: s.total_score, reverse=True)
        
        # Assign ranks
        for i, score in enumerate(scores, 1):
            score.rank = i
        
        return scores
    
    def _compute_impact_score(
        self,
        task: GeneratedTask,
        system_context: Optional[Any],
    ) -> float:
        """
        Compute impact score (0-100).
        
        Heuristics:
        - If task mentions coverage and coverage is low → high impact
        - If task mentions failing tests → very high impact
        - If task aligns with top opportunities → high impact
        - Use estimated_score_gain from opportunities if available
        """
        score = 50.0  # baseline
        
        instruction_lower = task.instruction.lower()
        
        # Failing tests = critical impact
        if "failing test" in instruction_lower or "fix test" in instruction_lower:
            score = 95.0
        
        # Coverage improvements
        elif "coverage" in instruction_lower or "test" in instruction_lower:
            score = 75.0
        
        # Performance/metrics
        elif any(kw in instruction_lower for kw in ["performance", "latency", "optimize", "metric"]):
            score = 70.0
        
        # Refactoring/debt
        elif any(kw in instruction_lower for kw in ["refactor", "debt", "cleanup", "churn"]):
            score = 60.0
        
        # Documentation
        elif any(kw in instruction_lower for kw in ["doc", "comment", "readme"]):
            score = 40.0
        
        # Boost if aligns with system_context opportunities
        if system_context and hasattr(system_context, 'ranked_opportunities'):
            for opp in system_context.ranked_opportunities[:5]:
                if opp.category in instruction_lower or opp.description.lower() in instruction_lower:
                    # Use estimated_score_gain if available
                    if hasattr(opp, 'estimated_score_gain'):
                        score = min(100.0, score + opp.estimated_score_gain * 2)
                    else:
                        score = min(100.0, score + 10.0)
                    break
        
        return max(0.0, min(100.0, score))
    
    def _compute_effort_score(self, task: GeneratedTask) -> float:
        """
        Compute effort score (0-100, higher = less effort).
        
        Inverse of estimated_minutes:
        - 30 min → 90 score
        - 60 min → 70 score
        - 120 min → 40 score
        - 240 min → 10 score
        """
        minutes = task.estimated_minutes or 60
        
        # Normalize: 30 min = 100, 240 min = 0
        # score = 100 - (minutes - 30) / (240 - 30) * 100
        if minutes <= 30:
            return 100.0
        elif minutes >= 240:
            return 0.0
        else:
            return 100.0 - ((minutes - 30) / 210.0) * 100.0
    
    def _compute_urgency_score(
        self,
        task: GeneratedTask,
        task_context: Optional[Any],
    ) -> float:
        """
        Compute urgency score (0-100).
        
        Factors:
        - Failing tests → very urgent
        - Low coverage (<70%) → urgent
        - Degrading metrics → urgent
        - Priority P0/P1 → urgent
        """
        score = 50.0  # baseline
        
        # Priority mapping
        priority_map = {
            "P0": 100.0,
            "critical": 100.0,
            "P1": 85.0,
            "high": 85.0,
            "P2": 60.0,
            "medium": 60.0,
            "P3": 30.0,
            "low": 30.0,
        }
        
        priority_str = str(task.priority).strip()
        if priority_str in priority_map:
            score = priority_map[priority_str]
        
        # Boost for failing tests
        if task_context and hasattr(task_context, 'test_failures'):
            if task_context.test_failures and len(task_context.test_failures) > 0:
                if "test" in task.instruction.lower():
                    score = min(100.0, score + 20.0)
        
        # Boost for low coverage
        if task_context and hasattr(task_context, 'coverage_percentage'):
            if task_context.coverage_percentage < 70.0:
                if "coverage" in task.instruction.lower():
                    score = min(100.0, score + 15.0)
        
        return max(0.0, min(100.0, score))
    
    def filter_top_k(
        self,
        scored_tasks: List[TaskScore],
        k: int = 10,
        min_score: float = 40.0,
    ) -> List[TaskScore]:
        """
        Filter to top-K tasks above minimum score.
        
        Args:
            scored_tasks: List of TaskScore objects (should be sorted)
            k: Maximum number of tasks to return
            min_score: Minimum total_score threshold
            
        Returns:
            Filtered list of TaskScore objects
        """
        filtered = [s for s in scored_tasks if s.total_score >= min_score]
        return filtered[:k]
    
    def explain_ranking(self, scored_task: TaskScore) -> str:
        """Generate human-readable explanation of task ranking."""
        lines = [
            f"Rank #{scored_task.rank}: {scored_task.task.id}",
            f"Total Score: {scored_task.total_score:.1f}/100",
            f"  - Impact: {scored_task.impact_score:.1f}/100 (weight: {self.IMPACT_WEIGHT})",
            f"  - Effort: {scored_task.effort_score:.1f}/100 (weight: {self.EFFORT_WEIGHT})",
            f"  - Urgency: {scored_task.urgency_score:.1f}/100 (weight: {self.URGENCY_WEIGHT})",
            f"Estimated time: {scored_task.task.estimated_minutes} minutes",
            f"Priority: {scored_task.task.priority}",
        ]
        return "\n".join(lines)

