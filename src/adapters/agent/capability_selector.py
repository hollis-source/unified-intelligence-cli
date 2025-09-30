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

        Uses fuzzy string matching (difflib.SequenceMatcher) to find similarity
        between task description words and agent capabilities.

        Algorithm:
        1. Tokenize task description into words
        2. For each word, find the best-matching capability using string similarity
        3. Sum all matches that exceed the 0.8 similarity threshold
        4. Return total score (higher = better match)

        Example:
            Task: "Write tests for the API"
            Agent capabilities: ["test", "testing", "qa"]
            - "write" matches nothing (< 0.8 threshold)
            - "tests" matches "testing" (0.889) → count
            - "for" matches nothing
            - "the" matches nothing
            - "api" matches nothing
            Total score: 0.889

        Returns:
            Match score (higher is better, sum of all good matches)
        """
        desc_words = task.description.lower().split()
        total_score = 0.0
        threshold = 0.8  # Minimum similarity ratio to count as match

        # For each word in task description, find best matching capability
        for word in desc_words:
            best_match = 0.0

            # Compare word against all agent capabilities
            for cap in agent.capabilities:
                cap_lower = cap.lower()
                # Calculate string similarity (0.0 to 1.0)
                ratio = difflib.SequenceMatcher(None, cap_lower, word).ratio()
                if ratio > best_match:
                    best_match = ratio

            # Only count strong matches (>= 80% similar)
            if best_match >= threshold:
                total_score += best_match

        return total_score