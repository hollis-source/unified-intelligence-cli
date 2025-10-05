"""CLI Task Executor - Connects DSL to unified-intelligence-cli.

Clean Architecture: Adapter layer (external system integration).
SOLID: SRP - only executes tasks via CLI, DIP - implements TaskExecutor interface.

Phase 3 Optimization: Replaced subprocess calls with in-process DirectTaskExecutor.
"""

import asyncio
from typing import Any, Dict, Optional, TYPE_CHECKING
from src.dsl.adapters.direct_task_executor import DirectTaskExecutor

if TYPE_CHECKING:
    from src.use_cases.task_coordinator import TaskCoordinatorUseCase


class CLITaskExecutor:
    """
    Executes DSL tasks via unified-intelligence-cli multi-agent system.

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
        llm_provider = None,
        agent_factory = None,
        config: Optional[Dict[str, Any]] = None,
        use_in_process: bool = True,
        direct_executor = None
    ):
        """
        Initialize CLI task executor.

        Args:
            task_coordinator: Existing task coordinator (optional, for future integration)
            task_mapping: Custom task-to-agent mapping (optional, uses defaults)
            llm_provider: LLM provider for in-process execution (Phase 3, legacy)
            agent_factory: Agent factory for in-process execution (Phase 3, legacy)
            config: Configuration dict for DirectTaskExecutor (Phase 3, legacy)
            use_in_process: Use DirectTaskExecutor (True) or subprocess (False, legacy)
            direct_executor: Pre-initialized DirectTaskExecutor (Phase 3 Bugfix, recommended)
        """
        self.task_coordinator = task_coordinator
        self.task_to_agent_map = task_mapping or self.DEFAULT_TASK_MAPPING.copy()
        self.use_in_process = use_in_process

        # Phase 3 Bugfix: Use injected DirectTaskExecutor if provided (recommended)
        if direct_executor:
            self.direct_executor = direct_executor
        # Phase 3 Legacy: Create DirectTaskExecutor internally if not provided
        elif use_in_process and llm_provider and agent_factory:
            from src.dsl.adapters.direct_task_executor import DirectTaskExecutor
            self.direct_executor = DirectTaskExecutor(
                llm_provider=llm_provider,
                agent_factory=agent_factory,
                config=config or {}
            )
        else:
            self.direct_executor = None

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
                return result

            # Check Phase 1 design tasks (active development)
            if hasattr(phase1_tasks, task_name):
                task_func = getattr(phase1_tasks, task_name)
                result = await task_func(input_data)
                return result

            # Check next task analysis (immediate priority determination)
            if hasattr(next_task_tasks, task_name):
                task_func = getattr(next_task_tasks, task_name)
                result = await task_func(input_data)
                return result

            # Check priorities analysis tasks (DSL runtime dogfooding)
            if hasattr(priorities_analysis_tasks, task_name):
                task_func = getattr(priorities_analysis_tasks, task_name)
                result = await task_func(input_data)
                return result

            # Check code review tasks (broadcast composition demo)
            if hasattr(code_review_tasks, task_name):
                task_func = getattr(code_review_tasks, task_name)
                result = await task_func(input_data)
                return result

            # Check GPU integration tasks
            if hasattr(gpu_integration_tasks, task_name):
                task_func = getattr(gpu_integration_tasks, task_name)
                result = await task_func(input_data)
                return result

            # Check git operations tasks
            if hasattr(git_operations_tasks, task_name):
                task_func = getattr(git_operations_tasks, task_name)
                result = await task_func(input_data)
                return result

            # Check refactoring tasks
            if hasattr(refactoring_tasks, task_name):
                task_func = getattr(refactoring_tasks, task_name)
                result = await task_func(input_data)
                return result

            # Check Grok analysis tasks
            if hasattr(grok_analysis_tasks, task_name):
                task_func = getattr(grok_analysis_tasks, task_name)
                result = await task_func(input_data)
                return result

            # Check system analysis tasks
            if hasattr(system_analysis_tasks, task_name):
                task_func = getattr(system_analysis_tasks, task_name)
                result = await task_func(input_data)
                return result

            # Check HF Spaces analysis tasks
            if hasattr(hf_spaces_analysis_tasks, task_name):
                task_func = getattr(hf_spaces_analysis_tasks, task_name)
                result = await task_func(input_data)
                return result

        except (ImportError, AttributeError):
            pass

        # Fallback: Auto-convert unknown task to ULTRATHINK prompt and execute via CLI
        return await self._execute_via_cli_fallback(task_name, input_data)

    async def _execute_via_cli_fallback(
        self,
        task_identifier: str,
        input_data: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Execute unknown task via CLI with auto-generated ULTRATHINK prompt.

        Phase 3 Optimization: Uses DirectTaskExecutor for in-process execution
        instead of subprocess when available, eliminating 1-2s overhead per task.

        Converts task identifier to human-readable prompt:
        - ultrathink_refactor_code_quality_in_src_adapters →
          "ULTRATHINK: Refactor code quality in src adapters"

        Args:
            task_identifier: Task identifier (usually snake_case or underscored)
            input_data: Optional input data/state

        Returns:
            CLI execution result as dict with status, output, etc.
        """
        # Phase 3: Use DirectTaskExecutor for in-process execution (no subprocess)
        if self.direct_executor:
            try:
                result = await self.direct_executor.execute_task(
                    task_identifier=task_identifier,
                    input_data=input_data
                )

                # Convert DirectTaskExecutor result to CLI format
                return {
                    "task": task_identifier,
                    "status": "success" if result.get('status') == 'SUCCESS' else "failed",
                    "output": result.get('output', ''),
                    "raw_output": result.get('output', ''),
                    "auto_generated": True,
                    "prompt": self._identifier_to_prompt(task_identifier),
                    "execution_mode": "in-process",
                    "metadata": result.get('metadata', {})
                }

            except Exception as e:
                raise ValueError(f"In-process execution failed for {task_identifier}: {str(e)}")

        # Legacy: Fall back to subprocess execution if DirectTaskExecutor not available
        prompt = self._identifier_to_prompt(task_identifier)

        # Build CLI command
        cmd = [
            "./bin/ui-cli",
            "--provider", "auto",
            "--routing", "team",
            "--agents", "scaled",
            "--orchestrator", "simple",
            "--verbose",
            "--timeout", "180",
            "--task", prompt
        ]

        # Execute via CLI subprocess
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                output = stdout.decode('utf-8')
                return {
                    "task": task_identifier,
                    "status": "success",
                    "output": output,
                    "raw_output": output,
                    "auto_generated": True,
                    "prompt": prompt,
                    "execution_mode": "subprocess"
                }
            else:
                error = stderr.decode('utf-8')
                raise ValueError(f"CLI execution failed for {task_identifier}: {error}")

        except Exception as e:
            raise ValueError(f"Failed to execute {task_identifier} via CLI: {str(e)}")

    def _identifier_to_prompt(self, identifier: str) -> str:
        """Convert task identifier to ULTRATHINK prompt.

        Examples:
            ultrathink_refactor_code_quality_in_src_adapters →
                ULTRATHINK: Refactor code quality in src adapters

            evaluate_technical_debt →
                ULTRATHINK: Evaluate technical debt

        Args:
            identifier: Task identifier (snake_case or underscored)

        Returns:
            Human-readable ULTRATHINK prompt
        """
        # Strip 'ultrathink_' prefix if present
        text = identifier
        if text.startswith('ultrathink_'):
            text = text[11:]  # len('ultrathink_') = 11

        # Replace underscores with spaces
        text = text.replace('_', ' ')

        # Capitalize first letter of each sentence
        text = text.capitalize()

        # Prepend ULTRATHINK directive
        return f"ULTRATHINK: {text}"

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
