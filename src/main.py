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
from src.factories import AgentFactory, ProviderFactory
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
@click.option("--provider", type=click.Choice(["mock", "grok"]), default="mock",
              help="LLM provider to use")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--parallel/--sequential", default=True,
              help="Enable/disable parallel execution")
@click.option("--config", type=click.Path(exists=True),
              help="Path to configuration file")
@click.option("--timeout", type=int, default=60,
              help="Timeout in seconds for async operations")
def main(
    task_descriptions: tuple,
    provider: str,
    verbose: bool,
    parallel: bool,
    config: str,
    timeout: int
) -> None:
    """
    Unified Intelligence CLI: Orchestrate agents for tasks.

    Clean Architecture: Main only handles CLI concerns.
    Composition logic is delegated to compose_dependencies.
    """
    # Load configuration
    app_config = load_config(config, provider, verbose, parallel, timeout)

    # Setup logging based on verbosity
    logger = setup_logging(app_config.verbose)

    try:
        # Create factory instances (DIP: depend on abstractions)
        agent_factory = AgentFactory()
        provider_factory = ProviderFactory()

        # Create agents via factory
        agents = agent_factory.create_default_agents()
        logger.info(f"Created {len(agents)} agents")

        # Create LLM provider via factory
        llm_provider = provider_factory.create_provider(app_config.provider)
        logger.info(f"Using {app_config.provider} LLM provider")

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

        # Compose dependencies
        coordinator = compose_dependencies(
            llm_provider=llm_provider,
            agents=agents,
            logger=logger if app_config.verbose else None
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
    parallel: bool,
    timeout: int
) -> Config:
    """
    Load configuration from file and merge with CLI arguments.

    CLI arguments override config file settings.

    Args:
        config_file: Path to config file (optional)
        provider: CLI provider argument
        verbose: CLI verbose flag
        parallel: CLI parallel flag
        timeout: CLI timeout value

    Returns:
        Merged configuration
    """
    if config_file:
        # Load from file and merge with CLI args
        file_config = Config.from_file(config_file)
        return file_config.merge_cli_args(
            provider=provider,
            verbose=verbose,
            parallel=parallel,
            timeout=timeout
        )
    else:
        # Use CLI args only
        return Config(
            provider=provider,
            verbose=verbose,
            parallel=parallel,
            timeout=timeout
        )


def setup_logging(verbose: bool) -> logging.Logger:
    """
    Configure logging based on verbosity.

    Clean Code: Extract method for clarity.
    """
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger(__name__)


async def execute_with_timeout(coro: Coroutine[Any, Any, Any], timeout: int) -> Any:
    """
    Execute coroutine with timeout.

    Production: Prevent hanging operations.
    """
    return await asyncio.wait_for(coro, timeout=timeout)


if __name__ == "__main__":
    main()