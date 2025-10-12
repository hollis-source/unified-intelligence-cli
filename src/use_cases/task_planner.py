"""Task planner use case - SRP: Focused on planning execution strategy."""

import json
import logging
from typing import List, Optional, Set
from src.entities import Agent, Task, ExecutionContext
from src.interfaces import (
    ITaskPlanner,
    ExecutionPlan,
    ITextGenerator,
    IAgentSelector,
    LLMConfig
)


class TaskPlannerUseCase(ITaskPlanner):
    """
    Planning use case - generates execution plans.

    SRP: Single responsibility - planning (not execution).
    Clean Code: Small methods <20 lines.
    """

    def __init__(
        self,
        llm_provider: ITextGenerator,
        agent_selector: IAgentSelector,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize with injected dependencies."""
        self.llm_provider = llm_provider
        self.agent_selector = agent_selector
        self.logger = logger or logging.getLogger(__name__)

    async def create_plan(
        self,
        tasks: List[Task],
        agents: List[Agent],
        context: Optional[ExecutionContext] = None
    ) -> ExecutionPlan:
        """
        Create execution plan using LLM.

        Clean Code: Orchestration method - delegates to helpers.
        """
        self.logger.info(f"Planning execution for {len(tasks)} tasks")

        try:
            # Use LLM to generate strategy
            llm_response = await self._invoke_llm_planner(tasks, agents)
            plan = self._parse_llm_response(llm_response, tasks, agents)
        except Exception as e:
            self.logger.warning(f"LLM planning failed: {e}, using fallback")
            plan = self._create_fallback_plan(tasks, agents)

        self.logger.info(f"Plan created: {len(plan.parallel_groups)} execution groups")
        return plan

    async def _invoke_llm_planner(
        self,
        tasks: List[Task],
        agents: List[Agent]
    ) -> str:
        """
        Invoke LLM for planning strategy.

        Clean Code: Extract method - single responsibility.
        """
        prompt = self._build_planning_prompt(tasks, agents)
        messages = [{"role": "user", "content": prompt}]
        config = LLMConfig(temperature=0.3, max_tokens=500)

        return self.llm_provider.generate(messages, config)

    def _build_planning_prompt(
        self,
        tasks: List[Task],
        agents: List[Agent]
    ) -> str:
        """
        Build prompt for LLM planner.

        Clean Code: Extract method for clarity.
        """
        task_desc = self._format_task_descriptions(tasks)
        agent_desc = self._format_agent_descriptions(agents)

        return f"""Given these tasks:
{task_desc}

And these available agents:
{agent_desc}

Create an execution plan that:
1. Respects task dependencies
2. Assigns each task to the most suitable agent
3. Identifies tasks that can run in parallel

Return a structured plan with task order and assignments."""

    def _format_task_descriptions(self, tasks: List[Task]) -> str:
        """Format tasks for prompt."""
        return "\n".join([
            f"- {t.task_id or i}: {t.description} (deps: {t.dependencies})"
            for i, t in enumerate(tasks)
        ])

    def _format_agent_descriptions(self, agents: List[Agent]) -> str:
        """Format agents for prompt."""
        return "\n".join([f"- {a.role}: {a.capabilities}" for a in agents])

    def _parse_llm_response(
        self,
        llm_response: str,
        tasks: List[Task],
        agents: List[Agent]
    ) -> ExecutionPlan:
        """
        Parse LLM response into ExecutionPlan.

        Clean Code: Single parsing responsibility.
        Week 11: Enhanced with tier-aware parallel grouping.
        """
        task_ids = [t.task_id or str(i) for i, t in enumerate(tasks)]

        try:
            data = json.loads(llm_response)
            task_order = data.get('task_order', task_ids)
            assignments = data.get('task_assignments', self._assign_tasks_to_agents(tasks, agents))
            # Week 11: Pass assignments and agents for tier-aware grouping
            parallel_groups = data.get('parallel_groups',
                self._compute_parallel_groups(tasks, assignments, agents))
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            task_order = task_ids
            assignments = self._assign_tasks_to_agents(tasks, agents)
            # Week 11: Pass assignments and agents for tier-aware grouping
            parallel_groups = self._compute_parallel_groups(tasks, assignments, agents)

        return ExecutionPlan(
            task_order=task_order,
            task_assignments=assignments,
            parallel_groups=parallel_groups
        )

    def _assign_tasks_to_agents(
        self,
        tasks: List[Task],
        agents: List[Agent]
    ) -> dict[str, str]:
        """
        Assign tasks to agents using selector.

        Clean Code: Delegate to injected selector.
        """
        assignments = {}
        for task in tasks:
            agent = self.agent_selector.select_agent(task, agents)
            if agent:
                task_id = task.task_id or str(tasks.index(task))
                assignments[task_id] = agent.role

        return assignments

    def _compute_parallel_groups(
        self,
        tasks: List[Task],
        task_assignments: Optional[dict[str, str]] = None,
        agents: Optional[List[Agent]] = None
    ) -> List[List[str]]:
        """
        Compute parallel execution groups via topological sort with tier awareness.

        Week 11: Enhanced for hierarchical delegation.
        - Tier 1 (planning) tasks execute first
        - Tier 2 (design) tasks execute second
        - Tier 3 (execution) tasks execute last, in parallel where possible

        Clean Code: Focused algorithm - single responsibility.
        """
        # Backward compatibility: If no tier info, use dependency-based grouping only
        if not task_assignments or not agents:
            return self._compute_parallel_groups_legacy(tasks)

        # Build agent tier map
        agent_tier_map = {a.role: a.tier for a in agents}

        # Group tasks by tier
        tier_groups = {1: [], 2: [], 3: []}
        task_map = {t.task_id or str(i): t for i, t in enumerate(tasks)}

        for task_id, task in task_map.items():
            agent_role = task_assignments.get(task_id)
            if agent_role:
                tier = agent_tier_map.get(agent_role, 3)  # Default to Tier 3
                tier_groups[tier].append(task_id)
            else:
                # No assignment, put in Tier 3 (execution fallback)
                tier_groups[3].append(task_id)

        # Compute parallel groups within each tier, respecting dependencies
        all_groups = []
        completed = set()

        for tier in [1, 2, 3]:  # Process tiers in order
            tier_task_ids = tier_groups[tier]
            if not tier_task_ids:
                continue

            # Compute parallel groups for this tier
            tier_task_map = {tid: task_map[tid] for tid in tier_task_ids}
            tier_completed = set()

            while len(tier_completed) < len(tier_task_ids):
                level = self._find_ready_tasks_in_tier(
                    tier_task_map, tier_completed, completed
                )

                if not level:
                    # Break cycle - add remaining tasks in this tier
                    level = [tid for tid in tier_task_ids if tid not in tier_completed]

                if level:
                    all_groups.append(level)
                    tier_completed.update(level)
                    completed.update(level)

        return all_groups if all_groups else [[t.task_id or str(i) for i, t in enumerate(tasks)]]

    def _compute_parallel_groups_legacy(self, tasks: List[Task]) -> List[List[str]]:
        """
        Legacy parallel group computation (dependency-based only).

        Used for backward compatibility with 5-agent mode.
        """
        task_map = {t.task_id or str(i): t for i, t in enumerate(tasks)}
        completed = set()
        levels = []

        while len(completed) < len(tasks):
            level = self._find_ready_tasks(task_map, completed)

            if not level:
                # Break cycle - add remaining
                level = [tid for tid in task_map if tid not in completed]

            levels.append(level)
            completed.update(level)

        return levels

    def _find_ready_tasks_in_tier(
        self,
        tier_task_map: dict,
        tier_completed: Set[str],
        all_completed: Set[str]
    ) -> List[str]:
        """
        Find tasks in tier with satisfied dependencies (considering all completed tasks).

        Week 11: Enhanced to consider cross-tier dependencies.
        """
        ready = []
        for task_id, task in tier_task_map.items():
            if task_id not in tier_completed:
                # Check if all dependencies (from any tier) are completed
                if all(dep in all_completed for dep in task.dependencies):
                    ready.append(task_id)
        return ready

    def _find_ready_tasks(
        self,
        task_map: dict,
        completed: Set[str]
    ) -> List[str]:
        """
        Find tasks with satisfied dependencies.

        Clean Code: Extract helper for readability.
        """
        ready = []
        for task_id, task in task_map.items():
            if task_id not in completed:
                if all(dep in completed for dep in task.dependencies):
                    ready.append(task_id)
        return ready

    def _create_fallback_plan(
        self,
        tasks: List[Task],
        agents: List[Agent]
    ) -> ExecutionPlan:
        """
        Create simple fallback plan without LLM.

        Clean Code: Reuse parsing logic.
        """
        return self._parse_llm_response("", tasks, agents)