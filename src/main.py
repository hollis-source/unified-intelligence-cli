"""
Unified Intelligence CLI - Main entry point.
Clean Architecture: Composition root with minimal responsibilities.
"""

import click
import asyncio
import logging
from pathlib import Path
from typing import List, Any, Coroutine
from dotenv import load_dotenv

from src.entities import Task
from src.composition import compose_dependencies
from src.factories import AgentFactory, ProviderFactory, TeamFactory
from src.adapters.cli import ResultFormatter
from src.config import Config

# Load environment variables from .env file
# Security: API keys and secrets should be in .env, not hardcoded
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)
    logging.debug(f"Loaded environment variables from {env_file}")


@click.command()
@click.option("--task", "-t", "task_descriptions", multiple=True, required=True,
              help="Task description (can be specified multiple times)")
@click.option("--provider", type=click.Choice(["mock", "grok", "tongyi", "tongyi-local", "replicate", "qwen3_zerogpu", "auto"]), default="mock",
              help="LLM provider to use (auto: Week 13 intelligent selection, qwen3_zerogpu: ZeroGPU inference, tongyi-local: async local model)")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--debug", is_flag=True, help="Enable debug output (LLM calls, tool details)")
@click.option("--parallel/--sequential", default=True,
              help="Enable/disable parallel execution")
@click.option("--config", type=click.Path(exists=True),
              help="Path to configuration file")
@click.option("--timeout", type=int, default=60,
              help="Timeout in seconds for async operations")
@click.option("--orchestrator", type=click.Choice(["simple", "openai-agents", "hybrid"]), default="hybrid",
              help="Orchestration mode: simple (baseline), openai-agents (SDK), or hybrid (intelligent routing, default)")
@click.option("--collect-data", is_flag=True,
              help="Enable data collection for model training (Week 9)")
@click.option("--data-dir", type=click.Path(), default="data/training",
              help="Directory to store collected training data (default: data/training)")
@click.option("--agents", type=click.Choice(["default", "extended", "scaled"]), default="default",
              help="Agent configuration: default (5 agents), extended (8 agents), scaled (16 agents with Category Theory & DSL teams)")
@click.option("--routing", type=click.Choice(["individual", "team"]), default="individual",
              help="Routing mode: individual (agent-based), team (team-based, recommended for scaled)")
def main(
    task_descriptions: tuple,
    provider: str,
    verbose: bool,
    debug: bool,
    parallel: bool,
    config: str,
    timeout: int,
    orchestrator: str,
    collect_data: bool,
    data_dir: str,
    agents: str,
    routing: str
) -> None:
    """
    Unified Intelligence CLI: Orchestrate agents for tasks.

    Clean Architecture: Main only handles CLI concerns.
    Composition logic is delegated to compose_dependencies.
    """
    # Load configuration
    app_config = load_config(
        config, provider, verbose, debug, parallel, timeout,
        orchestrator, collect_data, data_dir, agents, routing
    )

    # Setup logging based on verbosity
    logger = setup_logging(app_config.verbose, app_config.debug)

    try:
        # Create factory instances (DIP: depend on abstractions)
        agent_factory = AgentFactory()
        team_factory = TeamFactory(agent_factory)
        provider_factory = ProviderFactory()

        # Create agents or teams based on routing mode (Week 12: Team-based routing, Week 13: Category Theory & DSL teams)
        if app_config.routing_mode == "team":
            # Team-based routing (Week 12/13)
            if app_config.agent_mode == "scaled":
                teams = team_factory.create_scaled_teams()
                logger.info(f"Created {len(teams)} teams (scaled mode: 16 agents across 9 teams including Category Theory & DSL)")
            elif app_config.agent_mode == "extended":
                teams = team_factory.create_extended_teams()
                logger.info(f"Created {len(teams)} teams (extended mode: 8 agents across teams)")
            else:
                teams = team_factory.create_default_teams()
                logger.info(f"Created {len(teams)} teams (default mode: 5 single-agent teams)")

            # Extract agents from teams for backward compatibility
            agents = team_factory.get_all_agents_from_teams(teams)
        else:
            # Individual agent routing (Week 11, backward compatible)
            teams = None
            if app_config.agent_mode == "scaled":
                agents = agent_factory.create_scaled_agents()
                logger.info(f"Created {len(agents)} agents (scaled mode: 16 agents including Category Theory & DSL, individual routing)")
            elif app_config.agent_mode == "extended":
                agents = agent_factory.create_extended_agents()
                logger.info(f"Created {len(agents)} agents (extended mode: 8 agents, individual routing)")
            else:
                agents = agent_factory.create_default_agents()
                logger.info(f"Created {len(agents)} agents (default mode)")

        # Create LLM provider via factory
        llm_provider = provider_factory.create_provider(app_config.provider)
        logger.info(f"Using {app_config.provider} LLM provider")
        logger.info(f"Routing mode: {app_config.routing_mode}")

        # Create tasks from descriptions
        tasks = [
            Task(
                description=desc,
                task_id=f"task_{i+1}",
                priority=i+1
            )
            for i, desc in enumerate(task_descriptions)
        ]
        logger.info(f"Created {len(tasks)} tasks")

        # Compose dependencies (Week 7: orchestrator mode, Week 9: data collection, Week 12: team routing)
        coordinator = compose_dependencies(
            llm_provider=llm_provider,
            agents=agents,
            logger=logger if app_config.verbose else None,
            orchestrator_mode=app_config.orchestrator,
            collect_data=app_config.collect_data,
            data_dir=app_config.data_dir,
            provider_name=app_config.provider,
            routing_mode=app_config.routing_mode,
            teams=teams
        )

        # Execute with timeout
        results = asyncio.run(
            execute_with_timeout(
                coordinator.coordinate(
                    tasks=tasks,
                    agents=agents
                ),
                app_config.timeout
            )
        )

        # Display results (Clean Architecture: Use CLI adapter)
        formatter = ResultFormatter(verbose=app_config.verbose)
        formatter.format_results(results)

    except asyncio.TimeoutError:
        formatter = ResultFormatter()
        formatter.format_error(f"Operation timed out after {app_config.timeout} seconds", "Timeout")
        raise click.Abort()
    except ValueError as e:
        formatter = ResultFormatter()
        formatter.format_error(str(e), "Configuration Error")
        raise click.Abort()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        formatter = ResultFormatter(verbose=app_config.verbose)
        if app_config.verbose:
            raise
        else:
            formatter.format_error(str(e))
            raise click.Abort()


def load_config(
    config_file: str,
    provider: str,
    verbose: bool,
    debug: bool,
    parallel: bool,
    timeout: int,
    orchestrator: str = "simple",
    collect_data: bool = False,
    data_dir: str = "data/training",
    agent_mode: str = "default",
    routing_mode: str = "individual"
) -> Config:
    """
    Load configuration from file and merge with CLI arguments.

    CLI arguments override config file settings.

    Args:
        config_file: Path to config file (optional)
        provider: CLI provider argument
        verbose: CLI verbose flag
        debug: CLI debug flag (Week 3)
        parallel: CLI parallel flag
        timeout: CLI timeout value
        orchestrator: CLI orchestrator mode (Week 7)
        collect_data: CLI data collection flag (Week 9)
        data_dir: CLI data directory (Week 9)
        agent_mode: CLI agent mode (Week 11)
        routing_mode: CLI routing mode (Week 12)

    Returns:
        Merged configuration
    """
    if config_file:
        # Load from file and merge with CLI args
        file_config = Config.from_file(config_file)
        return file_config.merge_cli_args(
            provider=provider,
            verbose=verbose,
            debug=debug,
            parallel=parallel,
            timeout=timeout,
            orchestrator=orchestrator,
            collect_data=collect_data,
            data_dir=data_dir,
            agent_mode=agent_mode,
            routing_mode=routing_mode
        )
    else:
        # Use CLI args only
        return Config(
            provider=provider,
            verbose=verbose,
            debug=debug,
            parallel=parallel,
            timeout=timeout,
            orchestrator=orchestrator,
            collect_data=collect_data,
            data_dir=data_dir,
            agent_mode=agent_mode,
            routing_mode=routing_mode
        )


def setup_logging(verbose: bool, debug: bool) -> logging.Logger:
    """
    Configure logging based on verbosity.

    Week 3: Three-level logging (WARNING/INFO/DEBUG).
    Clean Code: Extract method for clarity.
    """
    if debug:
        level = logging.DEBUG
        log_format = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    elif verbose:
        level = logging.INFO
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    else:
        level = logging.WARNING
        log_format = "%(levelname)s - %(message)s"

    # Week 4: force=True ensures reconfiguration works
    logging.basicConfig(level=level, format=log_format, force=True)
    return logging.getLogger(__name__)


async def execute_with_timeout(coro: Coroutine[Any, Any, Any], timeout: int) -> Any:
    """
    Execute coroutine with timeout.

    Production: Prevent hanging operations.
    """
    return await asyncio.wait_for(coro, timeout=timeout)


if __name__ == "__main__":
    main()