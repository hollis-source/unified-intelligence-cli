#!/usr/bin/env python3
"""
Prompt Optimization Script using DSPy MIPROv2.

Sprint 2, US-2.3: CLI tool for running prompt optimization.

This script takes training examples and uses DSPy's MIPROv2 optimizer
to find optimal prompts for a given task type.

Usage:
    ./venv/bin/python scripts/optimize_prompts.py \\
      --task-type implementation \\
      --training-data data/training/implementation_examples.jsonl \\
      --num-trials 20 \\
      --output data/optimized_prompts/implementation.json
"""

import click
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adapters.prompt.quality_metrics import QualityMetricEvaluator
from src.adapters.prompt.optimizer import PromptOptimizer
from src.adapters.prompt.dspy_adapter import DSPyPromptAdapter
from src.factories.provider_factory import ProviderFactory


def load_training_data(file_path: str) -> list:
    """
    Load training examples from JSONL file.

    Args:
        file_path: Path to JSONL file

    Returns:
        List of training example dicts
    """
    examples = []

    with open(file_path) as f:
        for line in f:
            if line.strip():
                examples.append(json.loads(line))

    return examples


@click.command()
@click.option('--task-type', required=True,
              type=click.Choice(['implementation', 'design', 'testing', 'documentation']),
              help='Task type to optimize prompts for')
@click.option('--training-data', required=True, type=click.Path(exists=True),
              help='Path to training examples JSONL file')
@click.option('--num-trials', default=20, type=int,
              help='Number of MIPROv2 optimization trials (default: 20)')
@click.option('--output', required=True, type=click.Path(),
              help='Path to save optimized prompts JSON file')
@click.option('--model', default='qwen3_hf_inference',
              help='LLM model to use (default: qwen3_hf_inference)')
@click.option('--verbose', '-v', is_flag=True,
              help='Enable verbose output')
def optimize_prompts(task_type, training_data, num_trials, output, model, verbose):
    """
    Optimize DSPy prompts using MIPROv2.

    Loads training examples, runs MIPROv2 optimization, and saves
    optimized prompts with improvement metrics.

    Example:
        python scripts/optimize_prompts.py \\
          --task-type implementation \\
          --training-data data/training/examples.jsonl \\
          --num-trials 10 \\
          --output data/optimized_prompts/implementation.json
    """
    # Print header
    click.echo("=" * 80)
    click.echo("DSPy PROMPT OPTIMIZATION (MIPROv2)")
    click.echo("=" * 80)
    click.echo()
    click.echo(f"Task Type: {task_type}")
    click.echo(f"Training Data: {training_data}")
    click.echo(f"Num Trials: {num_trials}")
    click.echo(f"Model: {model}")
    click.echo(f"Output: {output}")
    click.echo()

    try:
        # Load training data
        click.echo("[1/5] Loading training data...")
        training_examples = load_training_data(training_data)
        click.echo(f"  Loaded {len(training_examples)} examples")

        if len(training_examples) == 0:
            click.echo("Error: No training examples found", err=True)
            sys.exit(1)

        # Create LLM provider
        click.echo(f"\n[2/5] Initializing LLM provider ({model})...")
        provider_factory = ProviderFactory()
        llm_provider = provider_factory.create_provider(model, {"timeout": 600})
        click.echo("  Provider initialized")

        # Create DSPy adapter
        click.echo("\n[3/5] Creating DSPy adapter...")
        dspy_adapter = DSPyPromptAdapter(llm_provider, use_chain_of_thought=True)
        click.echo("  DSPy adapter created")

        # Create quality metric
        click.echo("\n[4/5] Setting up quality metrics...")
        metric_evaluator = QualityMetricEvaluator()
        metric_fn = metric_evaluator.get_dspy_metric()
        click.echo("  Quality metric ready")

        # Run optimization
        click.echo(f"\n[5/5] Running MIPROv2 optimization ({num_trials} trials)...")
        click.echo("  This may take several minutes...")

        optimizer = PromptOptimizer(
            training_examples=training_examples,
            metric=metric_fn,
            num_trials=num_trials
        )

        results = optimizer.optimize(
            adapter=dspy_adapter,
            task_type=task_type,
            output_path=output
        )

        # Display results
        click.echo()
        click.echo("=" * 80)
        click.echo("OPTIMIZATION RESULTS")
        click.echo("=" * 80)

        if "error" in results:
            click.secho(f"Status: FAILED", fg="red", bold=True)
            click.secho(f"Error: {results['error']}", fg="red")
        else:
            click.secho("Status: SUCCESS", fg="green", bold=True)
            click.echo()
            click.echo(f"Baseline Score:  {results['baseline_score']:.3f}")
            click.echo(f"Optimized Score: {results['optimized_score']:.3f}")

            improvement = results['improvement']
            improvement_pct = results.get('improvement_pct', 0)

            if improvement > 0:
                click.secho(f"Improvement:     +{improvement:.3f} ({improvement_pct:+.1f}%)", fg="green", bold=True)
            elif improvement < 0:
                click.secho(f"Improvement:     {improvement:.3f} ({improvement_pct:.1f}%)", fg="yellow")
            else:
                click.echo(f"Improvement:     {improvement:.3f} (0.0%)")

            click.echo()
            click.echo(f"Optimized prompts saved to: {output}")

        click.echo("=" * 80)

    except FileNotFoundError as e:
        click.echo(f"\nError: File not found: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"\nError: Optimization failed: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    optimize_prompts()
