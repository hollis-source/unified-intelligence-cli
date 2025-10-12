"""
Orchestrator Router - Intelligent routing between orchestration modes.

Clean Architecture: Strategy pattern for selecting orchestration approach.
DIP: Depends on abstractions (task patterns), not concrete implementations.
"""

import re
import logging
from typing import List, Tuple
from src.entities import Task


logger = logging.getLogger(__name__)


class OrchestratorRouter:
    """
    Routes tasks to appropriate orchestrator based on complexity.

    Strategy: Analyze task characteristics to determine orchestration mode.
    - Simple tasks → OpenAI Agents SDK (faster, cleaner)
    - Complex multi-agent tasks → Simple mode (TaskCoordinatorUseCase)

    Clean Code: Single responsibility - routing decisions only.
    """

    # Patterns indicating multi-agent workflows
    MULTI_AGENT_PATTERNS = [
        # Research + Implementation (comprehensive)
        r"research.*(then|and).*(implement|code|write|create|build)",
        r"investigate.*(then|and).*(implement|code|write|create|build)",
        r"explore.*(then|and).*(implement|code|write|create|build)",

        # Implementation + Testing
        r"(implement|write|create|code|build).*(then|and).*(test|verify|validate)",
        r"(code|build).*(then|and).*test",

        # Testing + Review
        r"test.*(then|and).*(review|assess|evaluate)",
        r"verify.*(then|and).*review",

        # Review + Fix (loop)
        r"review.*(then|and).*(fix|refactor|improve)",
        r"(assess|evaluate).*(then|and).*(change|modify)",

        # Multi-step workflows (3+ steps)
        r"research.*(implement|code|write|create).*(test|verify)",
        r"investigate.*(implement|code|write|create).*(verify|validate)",
        r"explore.*(build|create).*(test|validate)",

        # Explicit multi-agent keywords
        r"(multiple|several)\s+(agents|steps|phases)",
        r"multi[- ]?(agent|step|phase)",
        r"coordinate.*agents",
    ]

    # Patterns indicating complex analysis (may need researcher)
    RESEARCH_PATTERNS = [
        r"^(research|investigate|explore|analyze|study)",
        r"(compare|contrast|evaluate)\s+\w+\s+(vs|versus|against)",
        r"(pros|advantages)\s+and\s+(cons|disadvantages)",
        r"(best|optimal|recommended)\s+(approach|strategy|solution)",
    ]

    # Patterns indicating review/critique (may need reviewer)
    REVIEW_PATTERNS = [
        r"(review|critique|assess|evaluate)\s+(code|implementation)",
        r"(check|verify)\s+SOLID",
        r"(improve|refactor|optimize)\s+based\s+on",
    ]

    def __init__(self, enable_sdk: bool = True):
        """
        Initialize router.

        Args:
            enable_sdk: Whether SDK mode is available (default True)
        """
        self.enable_sdk = enable_sdk

        # Compile patterns for performance
        self._multi_agent_regex = [re.compile(p, re.IGNORECASE) for p in self.MULTI_AGENT_PATTERNS]
        self._research_regex = [re.compile(p, re.IGNORECASE) for p in self.RESEARCH_PATTERNS]
        self._review_regex = [re.compile(p, re.IGNORECASE) for p in self.REVIEW_PATTERNS]

        logger.info(f"OrchestratorRouter initialized (SDK enabled: {enable_sdk})")

    def route(self, task: Task) -> str:
        """
        Determine orchestration mode for task.

        Args:
            task: Task to route

        Returns:
            "openai-agents" or "simple"
        """
        if not self.enable_sdk:
            logger.debug(f"SDK disabled, using simple mode for task: {task.task_id}")
            return "simple"

        # Analyze task characteristics
        is_multi_agent = self._is_multi_agent_task(task)
        is_research = self._is_research_task(task)
        is_review = self._is_review_task(task)

        # Decision logic
        if is_multi_agent:
            logger.info(
                f"Task {task.task_id} routed to SIMPLE mode: "
                f"multi-agent workflow detected"
            )
            return "simple"

        if is_research and len(task.description.split()) > 20:
            # Complex research tasks may benefit from planner
            logger.info(
                f"Task {task.task_id} routed to SIMPLE mode: "
                f"complex research task"
            )
            return "simple"

        if is_review:
            # Review tasks may need multiple iterations
            logger.info(
                f"Task {task.task_id} routed to SIMPLE mode: "
                f"review task with potential iterations"
            )
            return "simple"

        # Default: use SDK for single-agent tasks
        logger.info(
            f"Task {task.task_id} routed to SDK mode: "
            f"single-agent task"
        )
        return "openai-agents"

    def route_batch(self, tasks: List[Task]) -> List[Tuple[Task, str]]:
        """
        Route multiple tasks.

        Args:
            tasks: List of tasks to route

        Returns:
            List of (task, mode) tuples
        """
        return [(task, self.route(task)) for task in tasks]

    def _is_multi_agent_task(self, task: Task) -> bool:
        """
        Check if task requires multi-agent coordination.

        Args:
            task: Task to analyze

        Returns:
            True if multi-agent patterns detected
        """
        description = task.description

        for regex in self._multi_agent_regex:
            if regex.search(description):
                logger.debug(f"Multi-agent pattern matched: {regex.pattern}")
                return True

        return False

    def _is_research_task(self, task: Task) -> bool:
        """
        Check if task is primarily research-focused.

        Args:
            task: Task to analyze

        Returns:
            True if research patterns detected
        """
        description = task.description

        for regex in self._research_regex:
            if regex.search(description):
                logger.debug(f"Research pattern matched: {regex.pattern}")
                return True

        return False

    def _is_review_task(self, task: Task) -> bool:
        """
        Check if task requires code review.

        Args:
            task: Task to analyze

        Returns:
            True if review patterns detected
        """
        description = task.description

        for regex in self._review_regex:
            if regex.search(description):
                logger.debug(f"Review pattern matched: {regex.pattern}")
                return True

        return False

    def get_routing_stats(self, tasks: List[Task]) -> dict:
        """
        Get routing statistics for batch of tasks.

        Args:
            tasks: Tasks to analyze

        Returns:
            Dict with routing statistics
        """
        routes = self.route_batch(tasks)

        sdk_count = sum(1 for _, mode in routes if mode == "openai-agents")
        simple_count = sum(1 for _, mode in routes if mode == "simple")

        multi_agent_count = sum(1 for task in tasks if self._is_multi_agent_task(task))
        research_count = sum(1 for task in tasks if self._is_research_task(task))
        review_count = sum(1 for task in tasks if self._is_review_task(task))

        return {
            "total_tasks": len(tasks),
            "sdk_mode": sdk_count,
            "simple_mode": simple_count,
            "sdk_percentage": (sdk_count / len(tasks) * 100) if tasks else 0,
            "characteristics": {
                "multi_agent": multi_agent_count,
                "research": research_count,
                "review": review_count,
            }
        }
