"""
Unified Intelligence CLI - Main entry point.
Clean Architecture: Composition root with minimal responsibilities.
"""

import click
import asyncio
import logging
from typing import List

from src.entities import Task
from src.composition import compose_dependencies
from src.factories import AgentFactory, ProviderFactory


@click.command()
@click.argument("task_description")
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
    task_description: str,
    provider: str,
    verbose: bool,
    parallel: bool,
    config: str,
    timeout: int
):
    """
    Unified Intelligence CLI: Orchestrate agents for tasks.

    Clean Architecture: Main only handles CLI concerns.
    Composition logic is delegated to compose_dependencies.
    """
    # Setup logging based on verbosity
    logger = setup_logging(verbose)

    try:
        # Create agents via factory
        agents = AgentFactory.create_default_agents()
        logger.info(f"Created {len(agents)} agents")

        # Create LLM provider via factory
        llm_provider = ProviderFactory.create_provider(provider)
        logger.info(f"Using {provider} LLM provider")

        # Create task
        task = Task(
            description=task_description,
            task_id="main_task",
            priority=1
        )

        # Compose dependencies
        coordinator = compose_dependencies(
            llm_provider=llm_provider,
            agents=agents,
            logger=logger if verbose else None
        )

        # Execute with timeout
        results = asyncio.run(
            execute_with_timeout(
                coordinator.coordinate(
                    tasks=[task],
                    agents=agents
                ),
                timeout
            )
        )

        # Display results
        display_results(results, verbose)

    except asyncio.TimeoutError:
        click.echo(f"Error: Operation timed out after {timeout} seconds", err=True)
        raise click.Abort()
    except ValueError as e:
        click.echo(f"Configuration error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if verbose:
            raise
        else:
            click.echo(f"Error: {e}", err=True)
            raise click.Abort()


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


async def execute_with_timeout(coro, timeout: int):
    """
    Execute coroutine with timeout.

    Production: Prevent hanging operations.
    """
    return await asyncio.wait_for(coro, timeout=timeout)


def display_results(results: List, verbose: bool) -> None:
    """
    Display execution results.

    Clean Code: Separate display logic.
    """
    for i, result in enumerate(results):
        click.echo(f"\n{'=' * 40}")
        click.echo(f"Result #{i + 1}")
        click.echo(f"{'=' * 40}")

        # Status with color
        if result.status.value == "success":
            click.echo(click.style(f"Status: {result.status.value}", fg="green"))
        else:
            click.echo(click.style(f"Status: {result.status.value}", fg="red"))

        # Output (truncated unless verbose)
        if result.output:
            max_length = None if verbose else 200
            output = result.output[:max_length] if max_length else result.output
            if max_length and len(result.output) > max_length:
                output += "..."
            click.echo(f"Output: {output}")

        # Errors
        if result.errors:
            click.echo(click.style(f"Errors: {', '.join(result.errors)}", fg="red"))

        # Metadata in verbose mode
        if verbose and result.metadata:
            click.echo(f"Metadata: {result.metadata}")


if __name__ == "__main__":
    main()