"""
Orchestration Factory - Week 7, Phase 1.4

Factory for creating orchestrators based on mode selection.
Supports multiple orchestration strategies via Factory Method pattern.

Architecture:
- Factory Method: Create orchestrators based on mode
- Strategy: Different orchestration strategies (simple, openai-agents)
- DIP: Returns IAgentCoordinator interface (abstraction)
"""

import logging
from typing import List, Optional

from src.entities import Agent
from src.interfaces import IAgentCoordinator, ITextGenerator, IAgentExecutor, ITaskPlanner
from src.use_cases.task_coordinator import TaskCoordinatorUseCase

# Optional: OpenAI Agents SDK
try:
    from src.adapters.orchestration.openai_agents_sdk_adapter import OpenAIAgentsSDKAdapter
    OPENAI_AGENTS_AVAILABLE = True
except ImportError:
    OPENAI_AGENTS_AVAILABLE = False
    OpenAIAgentsSDKAdapter = None


logger = logging.getLogger(__name__)


class OrchestrationFactory:
    """
    Factory for creating orchestrators.

    Clean Architecture: Factory pattern for dependency creation.
    DIP: Returns IAgentCoordinator interface (callers depend on abstraction).

    Supported modes:
    - "simple": TaskCoordinatorUseCase (current, default)
    - "openai-agents": OpenAIAgentsSDKAdapter (Week 7, Phase 1)
    - "hybrid": HybridOrchestrator (Week 10, Phase 2 - intelligent routing)
    """

    @staticmethod
    def create_orchestrator(
        mode: str,
        llm_provider: ITextGenerator,
        task_planner: ITaskPlanner,
        agent_executor: IAgentExecutor,
        agents: List[Agent],
        logger_instance: Optional[logging.Logger] = None
    ) -> IAgentCoordinator:
        """
        Create orchestrator based on mode.

        Factory Method: Creates appropriate concrete class for mode.
        DIP: Returns IAgentCoordinator interface.

        Args:
            mode: Orchestration mode ("simple", "openai-agents", or "hybrid")
            llm_provider: LLM provider (Tongyi, Mock, etc.)
            task_planner: Task planning strategy
            agent_executor: Agent execution strategy
            agents: Available agents
            logger_instance: Optional logger

        Returns:
            IAgentCoordinator implementation

        Raises:
            ValueError: If mode is unsupported
        """
        mode = mode.lower()

        logger.info(f"Creating orchestrator: mode={mode}")

        if mode == "simple":
            return OrchestrationFactory._create_simple_orchestrator(
                task_planner=task_planner,
                agent_executor=agent_executor,
                logger_instance=logger_instance
            )

        elif mode == "openai-agents":
            if not OPENAI_AGENTS_AVAILABLE:
                logger.warning(
                    "OpenAI Agents SDK not available, falling back to simple mode. "
                    "Install with: pip install openai-agents"
                )
                return OrchestrationFactory._create_simple_orchestrator(
                    task_planner=task_planner,
                    agent_executor=agent_executor,
                    logger_instance=logger_instance
                )

            return OrchestrationFactory._create_openai_agents_orchestrator(
                llm_provider=llm_provider,
                agents=agents
            )

        elif mode == "hybrid":
            return OrchestrationFactory._create_hybrid_orchestrator(
                llm_provider=llm_provider,
                task_planner=task_planner,
                agent_executor=agent_executor,
                agents=agents,
                logger_instance=logger_instance
            )

        else:
            raise ValueError(
                f"Unsupported orchestration mode: '{mode}'. "
                f"Supported modes: simple, openai-agents, hybrid"
            )

    @staticmethod
    def _create_simple_orchestrator(
        task_planner: ITaskPlanner,
        agent_executor: IAgentExecutor,
        logger_instance: Optional[logging.Logger]
    ) -> IAgentCoordinator:
        """
        Create simple orchestrator (current system).

        Args:
            task_planner: Task planning strategy
            agent_executor: Agent execution strategy
            logger_instance: Optional logger

        Returns:
            TaskCoordinatorUseCase instance
        """
        logger.info("Creating simple orchestrator (TaskCoordinatorUseCase)")

        return TaskCoordinatorUseCase(
            task_planner=task_planner,
            agent_executor=agent_executor,
            max_retries=3,
            logger=logger_instance
        )

    @staticmethod
    def _create_openai_agents_orchestrator(
        llm_provider: ITextGenerator,
        agents: List[Agent]
    ) -> IAgentCoordinator:
        """
        Create OpenAI Agents SDK orchestrator.

        Args:
            llm_provider: LLM provider (used for Phase 1 fallback)
            agents: Available agents

        Returns:
            OpenAIAgentsSDKAdapter instance
        """
        logger.info("Creating OpenAI Agents SDK orchestrator")

        return OpenAIAgentsSDKAdapter(
            llm_provider=llm_provider,
            agents=agents,
            max_turns=10
        )

    @staticmethod
    def _create_hybrid_orchestrator(
        llm_provider: ITextGenerator,
        task_planner: ITaskPlanner,
        agent_executor: IAgentExecutor,
        agents: List[Agent],
        logger_instance: Optional[logging.Logger]
    ) -> IAgentCoordinator:
        """
        Create hybrid orchestrator with intelligent routing.

        Week 10, Phase 2: Routes tasks between SDK and simple mode.

        Args:
            llm_provider: LLM provider
            task_planner: Task planning strategy
            agent_executor: Agent execution strategy
            agents: Available agents
            logger_instance: Optional logger

        Returns:
            HybridOrchestrator instance
        """
        logger.info("Creating hybrid orchestrator (intelligent routing)")

        from src.adapters.orchestration.hybrid_orchestrator import HybridOrchestrator

        # Check if SDK is available for hybrid mode
        enable_sdk = OPENAI_AGENTS_AVAILABLE

        if not enable_sdk:
            logger.warning(
                "SDK not available, hybrid mode will use simple mode only. "
                "Install with: pip install openai-agents"
            )

        return HybridOrchestrator(
            llm_provider=llm_provider,
            task_planner=task_planner,
            agent_executor=agent_executor,
            agents=agents,
            logger_instance=logger_instance,
            enable_sdk=enable_sdk
        )

    @staticmethod
    def get_supported_modes() -> List[str]:
        """
        Get list of supported orchestration modes.

        Returns:
            List of mode names
        """
        modes = ["simple", "hybrid"]  # hybrid always available

        if OPENAI_AGENTS_AVAILABLE:
            modes.append("openai-agents")

        return modes

    @staticmethod
    def is_mode_available(mode: str) -> bool:
        """
        Check if orchestration mode is available.

        Args:
            mode: Mode name

        Returns:
            True if mode is available
        """
        mode = mode.lower()

        if mode == "simple":
            return True
        elif mode == "hybrid":
            return True  # Always available (falls back to simple if SDK unavailable)
        elif mode == "openai-agents":
            return OPENAI_AGENTS_AVAILABLE
        else:
            return False