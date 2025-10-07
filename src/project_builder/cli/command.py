"""CLI command for project builder.

Provides the `build-project` command for autonomous project execution
from natural language goals.
"""

import click
import asyncio
import logging
from datetime import datetime
from pathlib import Path

from src.project_builder import (
    ProjectOrchestrator,
    ProjectStateManager,
    create_state_repository,
    get_db_info,
    GoalDecomposer,
    HTNDSLTranslator
)
from src.project_builder.execution.coordinator import ExecutionCoordinator
from src.routing.team_router import TeamRouter
from src.routing.adaptive_selector import AdaptiveModelSelector
from src.routing.summary_repository import ModelSummaryRepository
from src.factories.team_factory import TeamFactory
from src.factories.provider_factory import ProviderFactory


logger = logging.getLogger(__name__)


@click.command(name="build-project")
@click.argument("goal", required=False, default="")
@click.option("--project-id", help="Custom project ID (default: auto-generated)")
@click.option("--model", default="grok",
              help="LLM model to use (grok, qwen3_next_80b_thinking, qwen3_hf_inference, qwen3_zerogpu, replicate, tongyi, auto)")
@click.option("--parallel/--sequential", default=True,
              help="Enable/disable parallel task execution (default: parallel)")
@click.option("--prompt-mode", default="manual", type=click.Choice(["manual", "dspy"]),
              help="Prompt generation mode - 'manual' (existing) or 'dspy' (optimized)")
@click.option("--state-db", default="data/project_builder_state.db",
              help="Path to state database (default: data/project_builder_state.db)")
@click.option("--output-dir", default="projects",
              help="Output directory for project artifacts (default: projects)")
@click.option("--verbose", "-v", is_flag=True,
              help="Enable verbose output")
@click.option("--resume", is_flag=True,
              help="Resume existing project by project-id")
def build_project_command(
    goal: str,
    project_id: str,
    model: str,
    parallel: bool,
    prompt_mode: str,
    state_db: str,
    output_dir: str,
    verbose: bool,
    resume: bool
) -> None:
    """Build a project from natural language goal.

    Autonomous project execution using HTN decomposition, DSL workflows,
    and multi-agent teams.

    Examples:
    \\b
        # Build a REST API
        ui-cli build-project "Create a REST API with user authentication"

        # Build with custom project ID
        ui-cli build-project "Create a web dashboard" --project-id dashboard-v1

        # Resume existing project
        ui-cli build-project --resume --project-id rest-api-20251006

        # Sequential execution (no parallelism)
        ui-cli build-project "Create a CLI tool" --sequential
    """
    # Configure logging
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Validate arguments
    if resume:
        if not project_id:
            click.echo("Error: --project-id required when using --resume", err=True)
            raise click.Abort()
    else:
        if not goal:
            click.echo("Error: GOAL required when not using --resume", err=True)
            raise click.Abort()

    # Generate project ID if not provided
    if not project_id:
        project_id = f"project-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Create output directory
    output_path = Path(output_dir) / project_id
    output_path.mkdir(parents=True, exist_ok=True)

    # Print header
    click.echo("=" * 80)
    click.echo("AGENTIC PROJECT BUILDER")
    click.echo("=" * 80)
    click.echo()
    click.echo(f"Mode: {'Resume' if resume else 'New Project'}")
    if not resume:
        click.echo(f"Goal: {goal}")
    click.echo(f"Project ID: {project_id}")
    click.echo(f"Parallel Execution: {parallel}")
    click.echo(f"Prompt Mode: {prompt_mode.upper()}")
    click.echo(f"Output Directory: {output_path}")
    click.echo()

    # Execute project
    try:
        result = asyncio.run(_execute_project(
            goal=goal,
            project_id=project_id,
            model=model,
            parallel=parallel,
            prompt_mode=prompt_mode,
            state_db=state_db,
            output_path=output_path,
            resume=resume
        ))

        # Display results
        _display_results(result)

    except KeyboardInterrupt:
        click.echo("\n\nProject execution interrupted by user.", err=True)
        click.echo(f"State saved. Resume with: ui-cli build-project --resume --project-id {project_id}")
        raise click.Abort()

    except Exception as e:
        click.echo(f"\n\nProject execution failed: {e}", err=True)
        logger.exception("Project execution error")
        raise click.Abort()


async def _execute_project(
    goal: str,
    project_id: str,
    model: str,
    parallel: bool,
    prompt_mode: str,
    state_db: str,
    output_path: Path,
    resume: bool
):
    """Execute project build asynchronously.

    Args:
        goal: Natural language project goal
        project_id: Unique project identifier
        model: LLM model to use
        parallel: Enable parallel execution
        prompt_mode: Prompt generation mode (manual or dspy)
        state_db: Path to state database
        output_path: Output directory path
        resume: Resume existing project

    Returns:
        ProjectResult with execution details
    """
    # Initialize components
    click.echo("[INIT] Initializing components...")

    # State management with environment-based repository selection
    # Uses PB_DB_TYPE env var ("sqlite" or "surrealdb")
    state_repo = create_state_repository(state_db_path=state_db)
    state_manager = ProjectStateManager(state_repo)

    # Display database info
    db_info = get_db_info()
    if db_info['type'] == 'surrealdb':
        click.echo(f"[DB] Using SurrealDB: {db_info['host']}:{db_info['port']}/{db_info['namespace']}/{db_info['database']}")
    else:
        click.echo(f"[DB] Using SQLite: {db_info['path']}")

    if resume:
        # Load existing project
        click.echo(f"[RESUME] Loading project state...")
        state_manager.load_state(project_id)

        # Create orchestrator (no goal decomposer needed for resume)
        orchestrator = ProjectOrchestrator(
            goal_decomposer=None,  # Not used for resume
            htn_dsl_translator=HTNDSLTranslator(enable_parallel=parallel),
            state_manager=state_manager
        )

        # Resume execution
        result = await orchestrator.resume_project(project_id)

    else:
        # New project execution
        # Create LLM provider using factory
        click.echo(f"[INIT] Creating LLM provider: {model}...")
        provider_factory = ProviderFactory()
        llm_provider = provider_factory.create_provider(model, {"timeout": 600})

        # Goal decomposer with selected model
        goal_decomposer = GoalDecomposer(llm_provider)

        # HTN-DSL translator with parallel support
        htn_dsl_translator = HTNDSLTranslator(enable_parallel=parallel)

        # Create execution coordinator with real LLM execution
        click.echo("[INIT] Initializing real LLM execution...")
        team_factory = TeamFactory()
        teams = team_factory.create_scaled_teams()  # Use scaled teams (9 teams)
        team_router = TeamRouter()

        # Create model selector with summary repository
        summary_repo = ModelSummaryRepository()
        model_selector = AdaptiveModelSelector(summary_repo=summary_repo)

        execution_coordinator = ExecutionCoordinator(
            team_router=team_router,
            model_selector=model_selector,
            teams=teams,
            llm_provider=llm_provider,  # Enable real execution
            prompt_mode=prompt_mode  # Sprint 1: DSPy support
        )

        # Project orchestrator with real execution
        orchestrator = ProjectOrchestrator(
            goal_decomposer=goal_decomposer,
            htn_dsl_translator=htn_dsl_translator,
            state_manager=state_manager,
            execution_coordinator=execution_coordinator  # Pass real coordinator
        )

        click.echo(f"[INIT] Components initialized (real execution enabled with {model})\n")

        # Execute project
        result = await orchestrator.execute_project(
            goal=goal,
            project_id=project_id
        )

    # Save artifacts to output directory
    if result.artifacts:
        click.echo(f"\n[ARTIFACTS] Saving to {output_path}...")
        for artifact_name, artifact_data in result.artifacts.items():
            artifact_file = output_path / artifact_name
            artifact_file.write_text(str(artifact_data))
            click.echo(f"  Saved: {artifact_name}")

    return result


def _display_results(result):
    """Display project execution results.

    Args:
        result: ProjectResult instance
    """
    click.echo()
    click.echo("=" * 80)
    click.echo("PROJECT EXECUTION RESULTS")
    click.echo("=" * 80)

    # Status
    status_icon = "✓" if result.success else "✗"
    status_color = "green" if result.success else "red"
    click.secho(f"Status: {status_icon} {'SUCCESS' if result.success else 'FAILED'}", fg=status_color, bold=True)

    # Metrics
    click.echo(f"Execution Time: {result.execution_time:.2f}s")
    click.echo(f"Estimated Cost: ${result.cost:.4f}")
    click.echo(f"Tasks Completed: {len([r for r in result.task_results if r.success])}/{len(result.task_results)}")
    click.echo()

    # Task details
    if result.task_results:
        click.echo("Task Results:")
        for i, task_result in enumerate(result.task_results, 1):
            status = "✓" if task_result.success else "✗"
            color = "green" if task_result.success else "red"
            click.secho(f"  {i}. {status} {task_result.task_id}", fg=color)

            if task_result.metadata.get("description"):
                click.echo(f"     {task_result.metadata['description']}")

            if not task_result.success and task_result.error:
                click.secho(f"     Error: {task_result.error}", fg="red", dim=True)

    # Error message
    if not result.success and result.error:
        click.echo()
        click.secho(f"Error: {result.error}", fg="red", bold=True)

    # Artifacts
    if result.artifacts:
        click.echo()
        click.echo("Artifacts Generated:")
        for artifact_name in result.artifacts.keys():
            click.secho(f"  ✓ {artifact_name}", fg="green")

    click.echo()
    click.echo("=" * 80)


# For standalone testing
if __name__ == "__main__":
    build_project_command()
