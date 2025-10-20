"""Hybrid Task Executor: Routes Tasks to Optimal Executor

Combines auggie's speed (55-91x faster) for research tasks with HTN agents'
codebase awareness for implementation tasks.

Routing Strategy:
- Research tasks → Auggie (3-10s, $0.01-0.05)
- Implementation tasks → HTN agents (30s-5min, $0.10-0.50)
- Default → Auggie (faster + cheaper)
"""

from typing import Dict, List, Optional
from src.entity.htn.htn_node import HTNNode
from src.entity.htn.execution_result import HTNExecutionResult
from src.interface.agent_executor import IAgentExecutor
from src.adapters.llm.auggie_executor import AuggieCLIExecutor, AuggieConfig


class HybridTaskExecutor(IAgentExecutor):
    """Intelligent task routing between auggie and HTN agents

    Routing logic based on task type keywords:
    - Research: design, strategy, architecture, compare, analyze, plan
    - Implementation: implement, refactor, fix, write code, test, debug

    Usage:
        >>> executor = HybridTaskExecutor()
        >>> research = HTNNode(task_id="r1", description="Design RAG architecture")
        >>> impl = HTNNode(task_id="i1", description="Implement RAG pipeline")
        >>>
        >>> # Automatically routes to auggie (fast)
        >>> r_result = executor.execute(research)
        >>>
        >>> # Automatically routes to HTN agent (codebase aware)
        >>> i_result = executor.execute(impl)
    """

    # Task classification keywords
    RESEARCH_KEYWORDS = [
        "design", "strategy", "architecture", "compare", "comparison",
        "analyze", "analysis", "explain", "recommend", "recommendation",
        "plan", "planning", "evaluate", "assessment", "review",
        "pros and cons", "trade-offs", "benefits", "advantages",
        "disadvantages", "pattern", "approach", "methodology"
    ]

    IMPLEMENTATION_KEYWORDS = [
        "implement", "implementation", "refactor", "refactoring",
        "fix", "debug", "write code", "code generation",
        "test", "testing", "deploy", "deployment",
        "integrate", "integration", "migrate", "migration",
        "optimize", "optimization", "performance tuning"
    ]

    def __init__(
        self,
        auggie_config: Optional[AuggieConfig] = None,
        htn_agent: Optional[IAgentExecutor] = None
    ):
        """Initialize hybrid executor

        Args:
            auggie_config: Configuration for auggie executor
            htn_agent: HTN agent executor (optional, for future implementation)
        """
        self.auggie = AuggieCLIExecutor(auggie_config or AuggieConfig())
        self.htn_agent = htn_agent  # TODO: Implement HTN agent fallback

    def execute(self, node: HTNNode) -> HTNExecutionResult:
        """Route task to optimal executor

        Args:
            node: HTN node to execute

        Returns:
            HTNExecutionResult from chosen executor
        """
        # Determine task type
        is_research = self._is_research_task(node)

        # Route to appropriate executor
        if is_research:
            # Research task → Use auggie (fast + cheap)
            node.metadata["routing_decision"] = "auggie_research"
            return self.auggie.execute(node)
        else:
            # Implementation task
            if self.htn_agent:
                # Use HTN agent if available
                node.metadata["routing_decision"] = "htn_agent_implementation"
                return self.htn_agent.execute(node)
            else:
                # Fallback to auggie (better than nothing)
                node.metadata["routing_decision"] = "auggie_fallback"
                return self.auggie.execute(node)

    def _is_research_task(self, node: HTNNode) -> bool:
        """Determine if task is research (vs implementation)

        Args:
            node: HTN node to classify

        Returns:
            True if research task, False if implementation
        """
        desc_lower = node.description.lower()

        # Check for explicit task type annotation
        if "type:research" in desc_lower:
            return True
        if "type:implementation" in desc_lower:
            return False

        # Count keyword matches
        research_score = sum(
            1 for kw in self.RESEARCH_KEYWORDS
            if kw in desc_lower
        )

        implementation_score = sum(
            1 for kw in self.IMPLEMENTATION_KEYWORDS
            if kw in desc_lower
        )

        # If implementation keywords dominate, classify as implementation
        if implementation_score > research_score:
            return False

        # Default to research (auggie is faster + cheaper)
        return True

    def get_routing_stats(self) -> Dict[str, int]:
        """Get routing statistics (for monitoring)

        Returns:
            Dict with routing counts
        """
        # TODO: Implement routing stats tracking
        return {
            "auggie_research": 0,
            "htn_agent_implementation": 0,
            "auggie_fallback": 0
        }
