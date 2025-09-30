"""Capability-based agent selector - Simple implementation."""

import difflib
from typing import List, Optional
from src.entities import Agent, Task
from src.interfaces import IAgentSelector


class CapabilityBasedSelector(IAgentSelector):
    """
    Select agents based on capability matching.
    Clean Code: Simple, focused implementation.
    """

    def select_agent(
        self,
        task: Task,
        agents: List[Agent]
    ) -> Optional[Agent]:
        """
        Select agent whose capabilities best match the task.

        SRP: Single responsibility - capability matching.

        Args:
            task: Task to be executed
            agents: Available agents

        Returns:
            Best matching agent or None
        """
        if not agents:
            return None

        # Find agents that can handle the task and calculate match scores
        agent_scores = []
        for agent in agents:
            if agent.can_handle(task):
                score = self._calculate_match_score(agent, task)
                agent_scores.append((agent, score))

        if not agent_scores:
            return None

        # Return agent with highest match score
        # Tie-breaker: if scores are equal, prefer more specialized (fewer capabilities)
        return max(agent_scores, key=lambda x: (x[1], -len(x[0].capabilities)))[0]

    def _calculate_match_score(self, agent: Agent, task: Task) -> float:
        """
        Calculate how well an agent's capabilities match a task.

        Clean Code: Extract method for scoring logic.

        Returns:
            Match score (higher is better, sum of all good matches)
        """
        desc_words = task.description.lower().split()
        total_score = 0.0
        threshold = 0.8

        # For each task word, find best matching capability
        for word in desc_words:
            best_match = 0.0
            for cap in agent.capabilities:
                cap_lower = cap.lower()
                ratio = difflib.SequenceMatcher(None, cap_lower, word).ratio()
                if ratio > best_match:
                    best_match = ratio

            # Only count matches above threshold
            if best_match >= threshold:
                total_score += best_match

        return total_score