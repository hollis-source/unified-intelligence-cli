"""Pool Task Executor - Dynamic task routing via executor pool.

Replaces CLITaskExecutor with pool-based approach for:
- Extensibility (Open/Closed Principle)
- Dynamic routing (no hardcoded mappings)
- Agent/Team integration

Clean Architecture: Adapter layer (bridges DSL to CLI infrastructure)
SOLID: OCP (extensible without modification), DIP (depends on abstractions)
"""

from typing import Any, Dict, Optional
import asyncio
from src.entities.executor import Executor, ExecutorPool, ExecutionResult, ExecutorStatus
from src.entities import Agent, Task, ExecutionStatus
from src.factories.agent_factory import AgentFactory
from src.adapters.agent.llm_executor import LLMAgentExecutor
from src.interface import ITextGenerator


class AgentExecutor(Executor):
    """Wraps an Agent as an Executor for use in ExecutorPool.

    Adapter Pattern: Adapts Agent + LLMAgentExecutor interface to Executor interface.

    This allows agents to be registered in ExecutorPool and participate in
    dynamic task routing based on capabilities.
    """

    def __init__(self, agent: Agent, llm_executor: LLMAgentExecutor):
        """Initialize with agent and LLM executor.

        Args:
            agent: Agent entity from AgentFactory
            llm_executor: LLM executor for running agent tasks
        """
        super().__init__(
            executor_id=f"agent_{agent.role}",
            name=f"Agent: {agent.role}"
        )
        self.agent = agent
        self.llm_executor = llm_executor
        self.metadata["agent_role"] = agent.role
        self.metadata["capabilities"] = agent.capabilities
        self.metadata["tier"] = agent.tier
        self.metadata["specialization"] = agent.specialization

    def can_execute(self, task: Any) -> bool:
        """Check if agent can handle task based on capabilities.

        Args:
            task: Task description (string) or dict with 'description'

        Returns:
            True if task matches agent capabilities
        """
        # Extract task description
        if isinstance(task, str):
            task_desc = task
        elif isinstance(task, dict):
            task_desc = task.get('description', str(task))
        elif hasattr(task, 'description'):
            task_desc = task.description
        else:
            task_desc = str(task)

        # Check if any capability matches task
        task_lower = task_desc.lower()
        for capability in self.agent.capabilities:
            if capability.lower() in task_lower:
                return True

        return False

    def execute(self, task: Any, **kwargs) -> ExecutionResult:
        """Execute task via agent using LLM executor.

        This is a synchronous wrapper around the async LLMAgentExecutor.execute().
        Uses asyncio.run() to execute the async method.

        Args:
            task: Task to execute
            **kwargs: Additional parameters (input_data, state, etc.)

        Returns:
            ExecutionResult with agent output
        """
        # Update executor status
        self.status = ExecutorStatus.BUSY
        self.execution_count += 1

        try:
            # Extract task description
            if isinstance(task, str):
                task_desc = task
            elif isinstance(task, dict):
                task_desc = task.get('description', str(task))
            else:
                task_desc = str(task)

            # Create Task entity for LLMAgentExecutor
            task_entity = Task(description=task_desc)

            # Execute via LLM (async)
            # Use asyncio.run() to execute async method from sync context
            async def execute_async():
                return await self.llm_executor.execute(
                    agent=self.agent,
                    task=task_entity,
                    context=None
                )

            llm_result = asyncio.run(execute_async())

            # Convert to Executor ExecutionResult format
            self.status = ExecutorStatus.IDLE

            # Extract output from LLM result
            if hasattr(llm_result, 'output'):
                output = llm_result.output
            else:
                output = str(llm_result)

            # Determine success robustly across enum/string implementations
            success_flag = True
            if hasattr(llm_result, 'status'):
                status = llm_result.status
                try:
                    name = getattr(status, 'name', None)
                    if name is not None:
                        success_flag = (name.upper() == 'SUCCESS')
                    else:
                        # Fallback: compare string directly
                        success_flag = str(status).upper().endswith('SUCCESS') or str(status).upper() == 'SUCCESS'
                except Exception:
                    success_flag = True

            return ExecutionResult(
                success=success_flag,
                output=output,
                metadata={
                    "agent": self.agent.role,
                    "capabilities": self.agent.capabilities,
                    "task": task_desc
                }
            )

        except Exception as e:
            self.status = ExecutorStatus.FAILED
            return ExecutionResult(
                success=False,
                error=str(e),
                metadata={"agent": self.agent.role, "task": str(task)}
            )

    def cancel(self, task_id: str) -> bool:
        """Cancel a running task.

        Args:
            task_id: Task ID to cancel

        Returns:
            True if task was cancelled
        """
        # For agent executors, we can't easily cancel LLM execution
        # Just mark as idle and return False (not cancelled)
        if self.status == ExecutorStatus.BUSY:
            self.status = ExecutorStatus.IDLE
            return True
        return False


class PoolTaskExecutor:
    """Task executor using ExecutorPool for dynamic routing.

    Replaces CLITaskExecutor with pool-based approach that:
    - Uses ExecutorPool for capability-based routing
    - Integrates with AgentFactory (no hardcoded mappings)
    - Supports both agent-based and team-based routing
    - Follows Open/Closed Principle (extensible without modification)

    Clean Architecture: Adapter layer (bridges DSL to CLI infrastructure)
    """

    def __init__(
        self,
        agent_factory: AgentFactory,
        llm_provider: ITextGenerator,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize with agent factory and configuration.

        Args:
            agent_factory: Factory for creating agents
            llm_provider: LLM provider for agent execution
            config: Configuration dict (agent_mode, routing_mode, etc.)
        """
        self.pool = ExecutorPool()
        self.agent_factory = agent_factory
        self.llm_provider = llm_provider
        self.config = config or {}

        # Create LLM executor for agents
        self.llm_executor = LLMAgentExecutor(
            llm_provider=llm_provider,
            provider_name=self.config.get('provider', 'mock')
        )

        # Register agent executors based on agent_mode
        self._register_agents()

    def _register_agents(self):
        """Register agent executors from agent factory."""
        agent_mode = self.config.get('agent_mode', 'default')

        # Get agents from factory
        if agent_mode == 'extended':
            agents = self.agent_factory.create_extended_agents()
        elif agent_mode == 'scaled':
            agents = self.agent_factory.create_scaled_agents()
        else:
            agents = self.agent_factory.create_default_agents()

        # Wrap each agent as executor and register
        for agent in agents:
            executor = AgentExecutor(agent, self.llm_executor)
            self.pool.register_executor(executor)

    async def execute_task(
        self,
        task_name: str,
        input_data: Optional[Any] = None
    ) -> Any:
        """Execute task via executor pool.

        Finds capable executor based on task description and routes
        task to that executor.

        Args:
            task_name: Task description
            input_data: Optional input data/state

        Returns:
            Task execution result (output from agent)

        Raises:
            ValueError: If no executor can handle task
        """
        # Get capable executor from pool
        executor = self.pool.get_available_executor(task_name)

        if not executor:
            available_capabilities = self._get_all_capabilities()
            raise ValueError(
                f"No executor available for task: {task_name}\n"
                f"Available capabilities: {', '.join(available_capabilities)}"
            )

        # Execute task
        result = executor.execute(task_name, input_data=input_data)

        if not result.success:
            raise ValueError(f"Task execution failed: {result.error}")

        return result.output

    def _get_all_capabilities(self) -> list:
        """Get all capabilities across all registered executors.

        Returns:
            List of unique capabilities
        """
        capabilities = set()
        for executor in self.pool.executors.values():
            if "capabilities" in executor.metadata:
                capabilities.update(executor.metadata["capabilities"])
        return sorted(capabilities)

    def get_executor_stats(self) -> Dict[str, Any]:
        """Get statistics about registered executors.

        Returns:
            Dictionary with executor pool statistics
        """
        stats = {
            "total_executors": len(self.pool.executors),
            "executors_by_status": {},
            "executors_by_tier": {},
            "total_executions": 0
        }

        for executor in self.pool.executors.values():
            # Count by status
            status = executor.get_status().name
            stats["executors_by_status"][status] = stats["executors_by_status"].get(status, 0) + 1

            # Count by tier (if available)
            if "tier" in executor.metadata:
                tier = executor.metadata["tier"]
                stats["executors_by_tier"][f"tier_{tier}"] = stats["executors_by_tier"].get(f"tier_{tier}", 0) + 1

            # Sum executions
            stats["total_executions"] += executor.execution_count

        return stats
