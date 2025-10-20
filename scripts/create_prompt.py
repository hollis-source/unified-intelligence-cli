#!/usr/bin/env python3
"""
Interactive Prompt Builder CLI - P2.3

Creates high-quality PromptStrategy objects through guided workflow.

Usage:
    python3 scripts/create_prompt.py [OPTIONS]

Options:
    --format: Output format (yaml, json, python) - default: yaml
    --min-score: Minimum quality score (0-100) - default: 60.0
    --help: Show this help message
"""

import sys
import click
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.cli.prompt_builder import PromptBuilder


@click.command()
@click.option(
    "--format",
    type=click.Choice(["yaml", "json", "python"]),
    default="yaml",
    help="Output format for saved prompt (default: yaml)"
)
@click.option(
    "--min-score",
    type=float,
    default=60.0,
    help="Minimum quality score required for validation (default: 60.0)"
)
def create_prompt(format: str, min_score: float):
    """
    Interactive Prompt Builder - Create high-quality prompts with validation.

    This tool guides you through creating structured prompts following the
    4-Sentence Framework (Persona, Goal, Task, Context) with real-time
    validation and domain-specific suggestions.
    """
    try:
        # Create builder
        builder = PromptBuilder(min_score=min_score)

        # Run interactive workflow
        prompt_strategy = builder.build_interactive()

        if prompt_strategy:
            # Save to file
            file_path = builder.save_prompt(prompt_strategy, output_format=format)

            if file_path:
                click.echo(click.style("\n✓ Success! Prompt created and saved.", fg="green", bold=True))
                sys.exit(0)
            else:
                click.echo(click.style("\n✗ Failed to save prompt.", fg="red"))
                sys.exit(1)
        else:
            click.echo("\nPrompt creation cancelled.")
            sys.exit(0)

    except KeyboardInterrupt:
        click.echo("\n\nInterrupted by user. Exiting...")
        sys.exit(130)
    except Exception as e:
        click.echo(click.style(f"\n✗ Error: {e}", fg="red"))
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    create_prompt()
