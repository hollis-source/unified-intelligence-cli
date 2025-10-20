"""CLI Task Executor - Connects DSL to autonomous-task-agent-dev-orchestration.

⚠️ DEPRECATED (Phase 5): This executor is deprecated in favor of PoolTaskExecutor.
Use PoolTaskExecutor for new code. CLITaskExecutor will be removed in Phase 7.

Migration Guide:
    # Old (deprecated):
    from src.dsl.adapters.cli_task_executor import CLITaskExecutor
    executor = CLITaskExecutor()

    # New (recommended):
    from src.dsl.adapters.pool_task_executor import PoolTaskExecutor
    executor = PoolTaskExecutor()

Clean Architecture: Adapter layer (external system integration).
SOLID: SRP - only executes tasks via CLI, DIP - implements TaskExecutor interface.
"""

import asyncio
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.use_cases.task_coordinator import TaskCoordinatorUseCase


class CLITaskExecutor:
    """
    Executes DSL tasks via autonomous-task-agent-dev-orchestration multi-agent system.

    Implements TaskExecutor protocol, bridging DSL interpreter to
    the existing CLI infrastructure. Maps task names to agents and
    executes them through TaskCoordinator.

    Clean Architecture:
    - Adapter layer (external integration)
    - Implements TaskExecutor protocol (DIP)
    - Uses existing TaskCoordinator

    Attributes:
        task_coordinator: Existing CLI task coordinator (optional, for future use)
        task_to_agent_map: Mapping of task names to agent names
    """

    # Default task-to-agent mapping
    DEFAULT_TASK_MAPPING = {
        # Development tasks
        "plan": "master-orchestrator",
        "design": "research-lead",
        "architect": "research-lead",

        # Code tasks
        "build": "python-specialist",
        "code": "python-specialist",
        "implement": "python-specialist",

        # Test tasks
        "test": "unit-test-engineer",
        "unit_test": "unit-test-engineer",
        "test_ui": "unit-test-engineer",
        "test_api": "unit-test-engineer",

        # Frontend tasks
        "frontend": "frontend-lead",
        "build_ui": "frontend-lead",
        "ui": "frontend-lead",

        # Backend tasks
        "backend": "backend-lead",
        "build_api": "backend-lead",
        "api": "backend-lead",

        # Integration tasks
        "integrate": "devops-lead",
        "deploy": "devops-lead",
        "package": "devops-lead",

        # Documentation tasks
        "document": "technical-writer",
        "docs": "technical-writer",

        # Generic task (fallback)
        "task": "python-specialist",
    }

    def __init__(
        self,
        task_coordinator = None,
        task_mapping: Optional[Dict[str, str]] = None,
        router_facade: Optional[object] = None,
        agent_factory: Optional[object] = None,
        lifecycle: Optional[object] = None,
    ):
        """
        Initialize CLI task executor.

        ⚠️ DEPRECATED: Use PoolTaskExecutor instead.

        Args:
            task_coordinator: Existing task coordinator (optional, for future integration)
            task_mapping: Custom task-to-agent mapping (optional, uses defaults)
            router_facade: Optional RouterFacade for production routing decisions
            agent_factory: Optional AgentFactory to provide agent roster to router
            lifecycle: Optional lifecycle callbacks with on_before_task/on_after_task/on_error
        """
        import warnings
        warnings.warn(
            "CLITaskExecutor is deprecated and will be removed in Phase 7. "
            "Use PoolTaskExecutor instead.",
            DeprecationWarning,
            stacklevel=2
        )

        self.task_coordinator = task_coordinator
        self.task_to_agent_map = task_mapping or self.DEFAULT_TASK_MAPPING.copy()
        self.router_facade = router_facade
        self.agent_factory = agent_factory
        self.lifecycle = lifecycle

    def _get_agent_for_task(self, task_name: str) -> str:
        """
        Get agent name for a task.

        Args:
            task_name: Task name from DSL

        Returns:
            Agent name to execute the task
        """
        # Try exact match
        if task_name in self.task_to_agent_map:
            return self.task_to_agent_map[task_name]

        # Try lowercase match
        task_lower = task_name.lower()
        if task_lower in self.task_to_agent_map:
            return self.task_to_agent_map[task_lower]

        # Try partial match (e.g., "build_frontend" -> "frontend")
        for key, agent in self.task_to_agent_map.items():
            if key in task_lower:
                return agent

        # Fallback to generic agent
        return "python-specialist"

    async def execute_task(self, task_name: str, input_data: Any = None) -> Any:
        """
        Execute a task via CLI multi-agent system.

        Args:
            task_name: Name of the task (e.g., "build", "test")
            input_data: Optional input from previous task

        Returns:
            Task execution result

        Example:
            result = await executor.execute_task("build")
        """
        # Lifecycle: before task hook
        if getattr(self, "lifecycle", None) and hasattr(self.lifecycle, "on_before_task"):
            try:
                self.lifecycle.on_before_task(task_name, input_data)
            except Exception:
                pass

        # Try to import and execute real task implementation
        try:
            # Try all task modules
            from src.dsl.tasks import (
                gpu_integration_tasks,
                git_operations_tasks,
                refactoring_tasks,
                grok_analysis_tasks,
                system_analysis_tasks,
                hf_spaces_analysis_tasks,
                code_review_tasks,
                priorities_analysis_tasks,
                next_task_tasks,
                phase1_tasks,
                implementation_tasks
            )

            # Check implementation tasks first (code generation)
            if hasattr(implementation_tasks, task_name):
                task_func = getattr(implementation_tasks, task_name)
                result = await task_func(input_data)
                if getattr(self, "lifecycle", None) and hasattr(self.lifecycle, "on_after_task"):
                    try:
                        self.lifecycle.on_after_task(task_name, result)
                    except Exception:
                        pass
                return result

            # Check Phase 1 design tasks (active development)
            if hasattr(phase1_tasks, task_name):
                task_func = getattr(phase1_tasks, task_name)
                result = await task_func(input_data)
                if getattr(self, "lifecycle", None) and hasattr(self.lifecycle, "on_after_task"):
                    try:
                        self.lifecycle.on_after_task(task_name, result)
                    except Exception:
                        pass
                return result

            # Check next task analysis (immediate priority determination)
            if hasattr(next_task_tasks, task_name):
                task_func = getattr(next_task_tasks, task_name)
                result = await task_func(input_data)
                if getattr(self, "lifecycle", None) and hasattr(self.lifecycle, "on_after_task"):
                    try:
                        self.lifecycle.on_after_task(task_name, result)
                    except Exception:
                        pass
                return result

            # Check priorities analysis tasks (DSL runtime dogfooding)
            if hasattr(priorities_analysis_tasks, task_name):
                task_func = getattr(priorities_analysis_tasks, task_name)
                result = await task_func(input_data)
                if getattr(self, "lifecycle", None) and hasattr(self.lifecycle, "on_after_task"):
                    try:
                        self.lifecycle.on_after_task(task_name, result)
                    except Exception:
                        pass
                return result

            # Check code review tasks (broadcast composition demo)
            if hasattr(code_review_tasks, task_name):
                task_func = getattr(code_review_tasks, task_name)
                result = await task_func(input_data)
                if getattr(self, "lifecycle", None) and hasattr(self.lifecycle, "on_after_task"):
                    try:
                        self.lifecycle.on_after_task(task_name, result)
                    except Exception:
                        pass
                return result

            # Check GPU integration tasks
            if hasattr(gpu_integration_tasks, task_name):
                task_func = getattr(gpu_integration_tasks, task_name)
                result = await task_func(input_data)
                if getattr(self, "lifecycle", None) and hasattr(self.lifecycle, "on_after_task"):
                    try:
                        self.lifecycle.on_after_task(task_name, result)
                    except Exception:
                        pass
                return result

            # Check git operations tasks
            if hasattr(git_operations_tasks, task_name):
                task_func = getattr(git_operations_tasks, task_name)
                result = await task_func(input_data)
                if getattr(self, "lifecycle", None) and hasattr(self.lifecycle, "on_after_task"):
                    try:
                        self.lifecycle.on_after_task(task_name, result)
                    except Exception:
                        pass
                return result

            # Check refactoring tasks
            if hasattr(refactoring_tasks, task_name):
                task_func = getattr(refactoring_tasks, task_name)
                result = await task_func(input_data)
                if getattr(self, "lifecycle", None) and hasattr(self.lifecycle, "on_after_task"):
                    try:
                        self.lifecycle.on_after_task(task_name, result)
                    except Exception:
                        pass
                return result

            # Check Grok analysis tasks
            if hasattr(grok_analysis_tasks, task_name):
                task_func = getattr(grok_analysis_tasks, task_name)
                result = await task_func(input_data)
                if getattr(self, "lifecycle", None) and hasattr(self.lifecycle, "on_after_task"):
                    try:
                        self.lifecycle.on_after_task(task_name, result)
                    except Exception:
                        pass
                return result

            # Check system analysis tasks
            if hasattr(system_analysis_tasks, task_name):
                task_func = getattr(system_analysis_tasks, task_name)
                result = await task_func(input_data)
                if getattr(self, "lifecycle", None) and hasattr(self.lifecycle, "on_after_task"):
                    try:
                        self.lifecycle.on_after_task(task_name, result)
                    except Exception:
                        pass
                return result

            # Check HF Spaces analysis tasks
            if hasattr(hf_spaces_analysis_tasks, task_name):
                task_func = getattr(hf_spaces_analysis_tasks, task_name)
                result = await task_func(input_data)
                if getattr(self, "lifecycle", None) and hasattr(self.lifecycle, "on_after_task"):
                    try:
                        self.lifecycle.on_after_task(task_name, result)
                    except Exception:
                        pass
                return result

        except (ImportError, AttributeError):
            pass

        # Fallback: routed selection (if facade+factory available), else heuristic map
        routing_info: Dict[str, Any] = {}
        agent_name = None

        if getattr(self, "router_facade", None) and getattr(self, "agent_factory", None):
            try:
                # Prefer extended roster for hierarchical routing; fallback to default
                get_agents = getattr(self.agent_factory, "create_extended_agents", None) or getattr(self.agent_factory, "create_default_agents", None)
                agents = get_agents() if callable(get_agents) else []
                task_obj = {"name": task_name, "description": str(input_data) if input_data is not None else task_name}
                decision = self.router_facade.route(task_obj, agents)
                agent_name = getattr(decision.selected_agent, "role", None) or self._get_agent_for_task(task_name)
                routing_info = {
                    "domain": decision.domain,
                    "tier": decision.tier,
                    "mode": decision.mode,
                    "scores": decision.scores,
                    "top_candidates": [getattr(a, "role", str(a)) for a in (decision.top_candidates or [])],
                }
            except Exception:
                agent_name = self._get_agent_for_task(task_name)
        else:
            agent_name = self._get_agent_for_task(task_name)

        description = f"Execute {task_name} with input: {input_data}" if input_data else f"Execute {task_name}"

        result = {
            "task": task_name,
            "agent": agent_name,
            "description": description,
            "status": "success",
            "output": f"Completed {task_name} via {agent_name}",
        }
        if routing_info:
            result["routing"] = routing_info

        # Simulate async execution
        await asyncio.sleep(0.01)

        # Lifecycle: after task hook (fallback path)
        if getattr(self, "lifecycle", None) and hasattr(self.lifecycle, "on_after_task"):
            try:
                self.lifecycle.on_after_task(task_name, result)
            except Exception:
                pass

        return result

    def add_task_mapping(self, task_name: str, agent_name: str) -> None:
        """
        Add custom task-to-agent mapping.

        Args:
            task_name: Task name to map
            agent_name: Agent to execute this task

        Example:
            executor.add_task_mapping("custom_task", "custom-agent")
        """
        self.task_to_agent_map[task_name] = agent_name

    def get_task_mapping(self) -> Dict[str, str]:
        """
        Get current task-to-agent mapping.

        Returns:
            Dictionary of task names to agent names
        """
        return self.task_to_agent_map.copy()
