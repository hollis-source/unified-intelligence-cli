"""Dependency composition module - Clean Architecture composition root."""

import logging
from typing import Optional, List
from src.entity import Agent, AgentTeam, MetricsCollector
from src.use_cases.task_planner import TaskPlannerUseCase
from src.use_cases.task_coordinator import TaskCoordinatorUseCase
from src.adapters.agent.capability_selector import CapabilityBasedSelector
from src.adapters.agent.team_selector import TeamBasedSelector
from src.adapters.agent.llm_executor import LLMAgentExecutor
from src.adapters.agent.llm_cache import CacheConfig
from src.interface import ITextGenerator, IAgentCoordinator
from src.factories.provider_factory import ProviderFactory
from src.factories.agent_factory import AgentFactory
from src.factories.orchestration_factory import OrchestrationFactory
from src.utils.data_collector import DataCollector
from src.routing.domain_classifier import DomainClassifier
from src.routing.team_router import TeamRouter


def compose_dependencies(
    llm_provider: ITextGenerator,
    agents: List[Agent],
    logger: Optional[logging.Logger] = None,
    orchestrator_mode: str = "simple",
    collect_data: bool = False,
    data_dir: str = "data/training",
    provider_name: str = "unknown",
    routing_mode: str = "individual",
    teams: Optional[List[AgentTeam]] = None,
    collect_metrics: bool = False,
    metrics_dir: str = "data/metrics",
    cache_enabled: bool = True,
    cache_ttl_seconds: int = 14400,
    cache_namespace: str = "",
    enable_rag: bool = False
) -> tuple[IAgentCoordinator, Optional[MetricsCollector]]:
    """
    Compose dependencies for the coordinator use case.

    Clean Architecture: Composition root pattern.
    SRP: Single responsibility - dependency wiring.
    DIP: Returns interface, injects abstractions.

    Args:
        llm_provider: LLM provider implementation
        agents: Available agents
        logger: Optional logger
        orchestrator_mode: Orchestration mode ("simple" or "openai-agents")
        collect_data: Enable data collection for training (Week 9)
        data_dir: Directory to store collected data (Week 9)
        provider_name: LLM provider name (Week 9)
        routing_mode: Routing mode ("individual" or "team") (Week 12)
        teams: Available agent teams (required if routing_mode is "team") (Week 12)
        collect_metrics: Enable metrics collection for monitoring (Week 13)
        metrics_dir: Directory to store metrics (Week 13)

    Returns:
        Tuple of (configured IAgentCoordinator, optional MetricsCollector)
    """
    # Week 9: Create data collector if enabled
    data_collector = None
    if collect_data:
        data_collector = DataCollector(data_dir=data_dir, enabled=True)
        if logger:
            logger.info(f"Data collection enabled: {data_dir}")

    # Week 13: Create metrics collector if enabled
    metrics_collector = None
    if collect_metrics:
        metrics_collector = MetricsCollector(storage_path=metrics_dir)
        if logger:
            logger.info(f"Metrics collection enabled: {metrics_dir}")

    # Create adapters
    # Phase 1: Cache configuration
    cache_config = CacheConfig(
        enabled=cache_enabled,
        ttl_seconds=cache_ttl_seconds,
        key_prefix=(cache_namespace or "llm_cache:")
    )

    agent_executor = LLMAgentExecutor(
        llm_provider,
        data_collector=data_collector,
        provider_name=provider_name,
        orchestrator=orchestrator_mode,
        cache_config=cache_config,
        enable_cache=cache_enabled
    )

    # Week 12/13: Create agent selector based on routing mode (with metrics integration)
    # Phase 2: Use RAG-enhanced routing if enabled
    if routing_mode == "team" and teams:
        # Create domain classifier with metrics integration
        domain_classifier = DomainClassifier(metrics_collector=metrics_collector)

        # Use RAG-enhanced router if RAG is enabled and components are available
        if enable_rag:
            try:
                from src.routing.rag_team_router import RAGTeamRouter
                from src.adapters.rag.surrealdb_store import SurrealDBStore
                from src.adapters.rag.embedding_pipeline import EmbeddingPipeline
                from src.adapters.llm.rag_config import RAGConfig

                # Get RAG components (will be created later if not exists)
                rag_config = RAGConfig()

                # Use environment variable or localhost for DB URL
                import os
                db_url = os.getenv("SURREALDB_URL", rag_config.db_url)
                if "project-builder-db" in db_url:
                    db_url = "ws://localhost:8000"

                # Create RAG components for routing
                db_store = SurrealDBStore(
                    url=db_url,
                    namespace=rag_config.db_namespace,
                    database=rag_config.db_database,
                    user=rag_config.db_user,
                    password=rag_config.db_password
                )

                # Connect to DB (async)
                import asyncio
                try:
                    asyncio.get_event_loop().run_until_complete(db_store.connect())
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(db_store.connect())

                # Create embedding pipeline
                embedder = EmbeddingPipeline(
                    provider=rag_config.embedding_provider,
                    model=rag_config.embedding_model
                )

                # Create RAG-enhanced router
                team_router = RAGTeamRouter(
                    domain_classifier=domain_classifier,
                    db_store=db_store,
                    embedding_pipeline=embedder,
                    top_k=rag_config.top_k,
                    similarity_threshold=rag_config.similarity_threshold,
                    use_rag=True
                )

                if logger:
                    logger.info(f"Using RAG-enhanced team routing with {len(teams)} teams")

            except Exception as e:
                if logger:
                    logger.warning(f"Failed to enable RAG routing: {e}. Using base TeamRouter.")
                team_router = TeamRouter(domain_classifier=domain_classifier)
        else:
            # Optional: track baseline routing decisions behind env flag
            import os
            if os.getenv("RAG_BASELINE_TRACK_DECISIONS", "0") in ("1", "true", "TRUE", "yes", "on"):
                try:
                    from src.adapters.llm.rag_config import RAGConfig
                    from src.adapters.rag.surrealdb_store import SurrealDBStore
                    from src.routing.tracking_router import TrackingTeamRouter
                    rag_config = RAGConfig()
                    db_url = os.getenv("SURREALDB_URL", rag_config.db_url)
                    if "project-builder-db" in db_url:
                        db_url = "ws://localhost:8000"
                    db_store = SurrealDBStore(
                        url=db_url,
                        namespace=rag_config.db_namespace,
                        database=rag_config.db_database,
                        user=rag_config.db_user,
                        password=rag_config.db_password
                    )
                    # Lazy connect inside store methods to avoid event loop conflicts
                    team_router = TrackingTeamRouter(domain_classifier=domain_classifier, db_store=db_store)
                    if logger:
                        logger.info("Using TeamRouter with baseline decision tracking (flag enabled)")
                except Exception as e:
                    if logger:
                        logger.warning(f"Baseline tracking flag set but initialization failed: {e}. Using base TeamRouter.")
                    team_router = TeamRouter(domain_classifier=domain_classifier)
            else:
                team_router = TeamRouter(domain_classifier=domain_classifier)

        agent_selector = TeamBasedSelector(teams, team_router=team_router)
        if logger and not enable_rag:
            logger.info(f"Using team-based routing with {len(teams)} teams")
    else:
        agent_selector = CapabilityBasedSelector()
        if logger and routing_mode == "team":
            logger.warning("Team routing requested but no teams provided, using individual routing")

    # Create planner use case (SRP: planning)
    task_planner = TaskPlannerUseCase(
        llm_provider=llm_provider,
        agent_selector=agent_selector,
        logger=logger
    )

    # Create coordinator via factory (Week 7: supports multiple orchestration modes)
    coordinator = OrchestrationFactory.create_orchestrator(
        mode=orchestrator_mode,
        llm_provider=llm_provider,
        task_planner=task_planner,
        agent_executor=agent_executor,
        agents=agents,
        logger_instance=logger
    )

    # RAG Integration: Wrap coordinator with RAGTaskCoordinator if enabled
    if enable_rag:
        try:
            from src.use_cases.rag_task_coordinator import RAGTaskCoordinator
            from src.adapters.rag.surrealdb_store import SurrealDBStore
            from src.adapters.rag.embedding_pipeline import EmbeddingPipeline
            from src.adapters.llm.rag_config import RAGConfig
            import asyncio

            # Create RAG components
            rag_config = RAGConfig()

            # Use environment variable or localhost for DB URL (handles both host and container)
            import os
            db_url = os.getenv("SURREALDB_URL", rag_config.db_url)
            # If using Docker container name, try localhost first (for host execution)
            if "project-builder-db" in db_url:
                db_url = "ws://localhost:8000"

            db_store = SurrealDBStore(
                url=db_url,
                namespace=rag_config.db_namespace,
                database=rag_config.db_database,
                user=rag_config.db_user,
                password=rag_config.db_password
            )

            # NOTE: Do NOT connect here! Connection will be established lazily
            # inside the async context to avoid event loop conflicts.
            # The db_store.connect() will be called automatically on first use.

            embedder = EmbeddingPipeline(
                provider=rag_config.embedding_provider,
                model=rag_config.embedding_model
            )

            # Wrap coordinator with RAG
            coordinator = RAGTaskCoordinator(
                task_planner=task_planner,
                agent_executor=agent_executor,
                db_store=db_store,
                embedding_pipeline=embedder,
                logger=logger
            )

            if logger:
                logger.info(f"RAG enabled: {rag_config}")
        except Exception as e:
            if logger:
                logger.warning(f"Failed to enable RAG: {e}. Continuing without RAG.")

    return coordinator, metrics_collector


def create_coordinator(
    provider_type: str = "mock",
    verbose: bool = False
) -> IAgentCoordinator:
    """
    Convenience function to create coordinator with defaults.

    Uses factory pattern to create dependencies from provider type string.
    Useful for testing and simple use cases.

    Args:
        provider_type: LLM provider type ("mock", "grok", etc.)
        verbose: Enable verbose logging

    Returns:
        Configured IAgentCoordinator
    """
    # Create factories
    agent_factory = AgentFactory()
    provider_factory = ProviderFactory()

    # Create dependencies via factories
    agents = agent_factory.create_default_agents()
    llm_provider = provider_factory.create_provider(provider_type)

    # Setup logging if verbose
    logger = None
    if verbose:
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

    # Compose and return
    return compose_dependencies(
        llm_provider=llm_provider,
        agents=agents,
        logger=logger
    )