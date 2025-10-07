#!/usr/bin/env python3
"""
Prompt Comparison Test Harness.

A/B testing framework to compare manual vs DSPy prompts on the same task.

Sprint 0, US-0.3: Test harness for prompt comparison
"""

import click
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


def analyze_project_artifacts(artifacts_path: Path) -> Dict[str, Any]:
    """
    Analyze project artifacts for quality metrics.

    Args:
        artifacts_path: Path to project artifacts directory

    Returns:
        Quality metrics dictionary
    """
    if not artifacts_path.exists():
        return {
            'exists': False,
            'quality_score': 0.0,
            'syntax_correctness': 0.0,
            'completeness': 0.0,
            'conciseness': 0.0,
            'artifact_count': 0
        }

    # Use the same analysis logic as measure_baseline.py
    import ast

    artifacts = list(artifacts_path.glob('*'))
    if not artifacts:
        return {
            'exists': True,
            'quality_score': 0.0,
            'syntax_correctness': 0.0,
            'completeness': 0.0,
            'conciseness': 0.0,
            'artifact_count': 0
        }

    results = []

    for artifact_file in artifacts:
        if not artifact_file.is_file():
            continue

        try:
            code = artifact_file.read_text()

            # Analyze artifact
            metrics = {
                'syntax_correct': False,
                'has_todos': False,
                'has_thinking': False
            }

            # Syntax check
            try:
                # Strip markdown fences
                code_clean = code
                if '```python' in code:
                    import re
                    match = re.search(r'```python\s*\n(.*?)```', code, re.DOTALL)
                    if match:
                        code_clean = match.group(1)

                ast.parse(code_clean)
                metrics['syntax_correct'] = True
            except:
                pass

            # Completeness check
            incomplete_patterns = ['# TODO', '# Similar', 'NotImplementedError', 'pass  # implement']
            metrics['has_todos'] = any(p.lower() in code.lower() for p in incomplete_patterns)

            # Conciseness check
            thinking_patterns = ['Okay,', 'Let me ', 'I need to ', 'First,', 'Wait,']
            metrics['has_thinking'] = any(code.startswith(p) for p in thinking_patterns)

            results.append(metrics)

        except Exception as e:
            print(f"Warning: Error analyzing {artifact_file.name}: {e}", file=sys.stderr)

    if not results:
        return {
            'exists': True,
            'quality_score': 0.0,
            'syntax_correctness': 0.0,
            'completeness': 0.0,
            'conciseness': 0.0,
            'artifact_count': 0
        }

    # Calculate aggregate metrics
    total = len(results)
    syntax_correct = sum(r['syntax_correct'] for r in results) / total * 100
    complete = sum(not r['has_todos'] for r in results) / total * 100
    concise = sum(not r['has_thinking'] for r in results) / total * 100

    # Overall quality score (weighted)
    quality_score = syntax_correct * 0.4 + complete * 0.4 + concise * 0.2

    return {
        'exists': True,
        'quality_score': quality_score,
        'syntax_correctness': syntax_correct,
        'completeness': complete,
        'conciseness': concise,
        'artifact_count': total
    }


def run_project_builder(task_description: str, project_id: str, model: str, prompt_mode: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Run project builder with specified prompt mode.

    Args:
        task_description: Task to execute
        project_id: Project identifier
        model: LLM model to use
        prompt_mode: 'manual' or 'dspy'
        verbose: Enable verbose output

    Returns:
        Execution results dictionary
    """
    # Build command
    cmd = [
        './venv/bin/python3',
        '-m', 'src.project_builder.cli.command',
        task_description,
        '--project-id', project_id,
        '--model', model
    ]

    # Add prompt mode flag (Sprint 1: Now implemented)
    if prompt_mode == 'dspy':
        cmd.extend(['--prompt-mode', 'dspy'])

    if verbose:
        cmd.append('-v')

    print(f"\nRunning with {prompt_mode.upper()} prompts...")
    print(f"Command: {' '.join(cmd)}\n")

    # Execute
    start_time = datetime.now()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        duration = (datetime.now() - start_time).total_seconds()

        # Check if successful
        success = result.returncode == 0 and 'SUCCESS' in result.stdout

        return {
            'success': success,
            'exit_code': result.returncode,
            'duration': duration,
            'stdout': result.stdout if verbose else result.stdout[-500:],  # Last 500 chars
            'stderr': result.stderr if result.stderr else ''
        }

    except subprocess.TimeoutExpired:
        duration = (datetime.now() - start_time).total_seconds()
        return {
            'success': False,
            'exit_code': -1,
            'duration': duration,
            'stdout': '',
            'stderr': 'Timeout after 300 seconds'
        }
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        return {
            'success': False,
            'exit_code': -2,
            'duration': duration,
            'stdout': '',
            'stderr': str(e)
        }


@click.command()
@click.argument('task_description')
@click.option('--project-id', required=True, help='Base project identifier')
@click.option('--model', default='qwen3_hf_inference', help='LLM model to use')
@click.option('--verbose/--no-verbose', default=False, help='Verbose output')
@click.option('--modes', default='manual,dspy', help='Comma-separated prompt modes to test')
def compare_prompts(task_description: str, project_id: str, model: str, verbose: bool, modes: str):
    """
    Compare manual vs DSPy prompts on the same task.

    Example:
        python scripts/compare_prompts.py "Build Python add function" --project-id test-compare
    """
    print("="*80)
    print("PROMPT COMPARISON TEST HARNESS")
    print("Sprint 0, US-0.3")
    print("="*80)
    print(f"\nTask: {task_description}")
    print(f"Model: {model}")
    print(f"Modes: {modes}\n")

    results = {}
    modes_list = [m.strip() for m in modes.split(',')]

    for mode in modes_list:
        print(f"\n{'='*80}")
        print(f"Testing with {mode.upper()} prompts")
        print(f"{'='*80}")

        # Run project builder
        mode_project_id = f"{project_id}-{mode}"
        execution_result = run_project_builder(
            task_description,
            mode_project_id,
            model,
            mode,
            verbose
        )

        # Analyze artifacts
        artifacts_path = Path(f'projects/{mode_project_id}')
        metrics = analyze_project_artifacts(artifacts_path)

        # Store results
        results[mode] = {
            'implemented': True,
            'execution': execution_result,
            'metrics': metrics
        }

        # Display summary
        if execution_result['success']:
            print(f"\n✓ {mode.upper()} execution SUCCEEDED")
            print(f"  Duration: {execution_result['duration']:.1f}s")
            print(f"  Quality Score: {metrics['quality_score']:.1f}%")
            print(f"  Artifacts: {metrics['artifact_count']}")
        else:
            print(f"\n✗ {mode.upper()} execution FAILED")
            print(f"  Exit code: {execution_result['exit_code']}")
            if execution_result['stderr']:
                print(f"  Error: {execution_result['stderr'][:200]}")

    # Generate comparison report
    print(f"\n{'='*80}")
    print("COMPARISON SUMMARY")
    print(f"{'='*80}")

    # Compare implemented modes
    implemented_modes = [m for m in modes_list if results.get(m, {}).get('implemented', False)]

    if len(implemented_modes) >= 2:
        # Full comparison
        for mode in implemented_modes:
            r = results[mode]
            if r['execution']['success']:
                print(f"\n{mode.upper()}:")
                print(f"  Quality Score:    {r['metrics']['quality_score']:.1f}%")
                print(f"  Syntax Correct:   {r['metrics']['syntax_correctness']:.1f}%")
                print(f"  Complete:         {r['metrics']['completeness']:.1f}%")
                print(f"  Concise:          {r['metrics']['conciseness']:.1f}%")
                print(f"  Duration:         {r['execution']['duration']:.1f}s")

        # Calculate improvement
        if all(results[m]['execution']['success'] for m in implemented_modes):
            baseline_mode = implemented_modes[0]
            comparison_mode = implemented_modes[1]

            baseline_score = results[baseline_mode]['metrics']['quality_score']
            comparison_score = results[comparison_mode]['metrics']['quality_score']

            improvement = comparison_score - baseline_score
            improvement_pct = (improvement / baseline_score * 100) if baseline_score > 0 else 0

            print(f"\n{'='*80}")
            print(f"Improvement: {comparison_mode.upper()} vs {baseline_mode.upper()}")
            print(f"  Absolute: {improvement:+.1f}%")
            print(f"  Relative: {improvement_pct:+.1f}%")
            print(f"{'='*80}")

    elif len(implemented_modes) == 1:
        # Only manual mode available
        mode = implemented_modes[0]
        r = results[mode]
        if r['execution']['success']:
            print(f"\n{mode.upper()} (baseline):")
            print(f"  Quality Score: {r['metrics']['quality_score']:.1f}%")
            print(f"  Duration:      {r['execution']['duration']:.1f}s")
            print(f"\nNote: DSPy comparison will be available after Sprint 1")

    # Save comparison results
    output_file = f"metrics/comparison_{project_id}.json"
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    comparison_data = {
        'task': task_description,
        'timestamp': datetime.now().isoformat(),
        'model': model,
        'results': results
    }

    with open(output_path, 'w') as f:
        json.dump(comparison_data, f, indent=2)

    print(f"\nDetailed results saved to: {output_file}")


if __name__ == '__main__':
    compare_prompts()
