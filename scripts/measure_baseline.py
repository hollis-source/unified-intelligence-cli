#!/usr/bin/env python3
"""
Baseline Metrics Collection for Project Builder Prompts.

Analyzes existing project artifacts to establish baseline performance
before DSPy optimization.

Sprint 0, US-0.2: Baseline metrics collection
"""

import ast
import json
import sys
from pathlib import Path
from typing import Dict, List, Any


def analyze_artifact(code: str, artifact_name: str) -> Dict[str, Any]:
    """
    Analyze code artifact for quality metrics.

    Args:
        code: Code content to analyze
        artifact_name: Name of artifact file

    Returns:
        Dictionary with quality metrics
    """
    metrics = {
        'artifact_name': artifact_name,
        'syntax_correct': False,
        'has_todos': False,
        'has_thinking': False,
        'thinking_lines': 0,
        'code_lines': 0,
        'total_lines': 0
    }

    # Syntax check (try to parse as Python)
    try:
        # Strip markdown fences if present
        code_clean = code
        if '```python' in code:
            # Extract code from fences
            import re
            match = re.search(r'```python\s*\n(.*?)```', code, re.DOTALL)
            if match:
                code_clean = match.group(1)

        ast.parse(code_clean)
        metrics['syntax_correct'] = True
    except SyntaxError:
        pass  # Might be design/docs, not code
    except Exception:
        pass  # Other parsing errors

    # Completeness check (look for TODOs, placeholders)
    incomplete_patterns = [
        '# TODO',
        '# Similar',
        '# ...',
        'pass  # implement',
        'NotImplementedError',
        '# Add similar',
        '# Same as'
    ]

    for pattern in incomplete_patterns:
        if pattern.lower() in code.lower():
            metrics['has_todos'] = True
            break

    # Verbosity check (look for thinking/explanation)
    thinking_patterns = [
        'Okay,',
        'Let me ',
        'I need to ',
        'First,',
        'The user wants',
        'Wait,',
        'Alternatively',
        'But '
    ]

    lines = code.split('\n')
    metrics['total_lines'] = len(lines)

    for line in lines[:20]:  # Check first 20 lines
        line_stripped = line.strip()

        # Check if line is thinking
        is_thinking = False
        for pattern in thinking_patterns:
            if line_stripped.startswith(pattern):
                metrics['thinking_lines'] += 1
                metrics['has_thinking'] = True
                is_thinking = True
                break

        # Count code lines (non-empty, non-comment, non-thinking)
        if line_stripped and not is_thinking:
            if not line_stripped.startswith('#') or '```' in line_stripped:
                metrics['code_lines'] += 1

    return metrics


def collect_baseline(projects_dir: str = 'projects') -> Dict[str, Any]:
    """
    Collect baseline metrics from test projects.

    Args:
        projects_dir: Path to projects directory

    Returns:
        Aggregated baseline metrics
    """
    projects_path = Path(projects_dir)

    # Find projects with artifacts
    test_projects = [
        'test-artifacts-final',
        'test-improved-prompts',
        'test-api-final',
        'test-final-improved',
        'test-rest-api'
    ]

    results = []

    for project_name in test_projects:
        project_path = projects_path / project_name
        if not project_path.exists():
            print(f"Warning: {project_name} not found, skipping")
            continue

        # Analyze all artifact files
        artifacts = list(project_path.glob('*'))
        print(f"\nAnalyzing {project_name}: {len(artifacts)} artifacts")

        for artifact_file in artifacts:
            if not artifact_file.is_file():
                continue

            try:
                code = artifact_file.read_text()
                metrics = analyze_artifact(code, artifact_file.name)
                metrics['project'] = project_name
                results.append(metrics)

                status = '✓' if metrics['syntax_correct'] else '✗'
                todos = 'T' if metrics['has_todos'] else ' '
                thinking = 'V' if metrics['has_thinking'] else ' '
                print(f"  [{status}][{todos}][{thinking}] {artifact_file.name[:40]:<40} "
                      f"({metrics['code_lines']} code / {metrics['thinking_lines']} thinking lines)")

            except Exception as e:
                print(f"  Error analyzing {artifact_file.name}: {e}")

    if not results:
        print("\nNo artifacts found! Run some project builder tests first.")
        return {
            'total_artifacts': 0,
            'syntax_correctness': 0.0,
            'completeness': 0.0,
            'conciseness': 0.0,
            'details': []
        }

    # Aggregate metrics
    total = len(results)
    syntax_correct = sum(r['syntax_correct'] for r in results)
    complete = sum(not r['has_todos'] for r in results)
    concise = sum(not r['has_thinking'] for r in results)

    baseline = {
        'total_artifacts': total,
        'syntax_correctness': (syntax_correct / total * 100) if total > 0 else 0,
        'completeness': (complete / total * 100) if total > 0 else 0,
        'conciseness': (concise / total * 100) if total > 0 else 0,
        'avg_code_lines': sum(r['code_lines'] for r in results) / total if total > 0 else 0,
        'avg_thinking_lines': sum(r['thinking_lines'] for r in results) / total if total > 0 else 0,
        'details': results
    }

    return baseline


def main():
    """Main entry point."""
    print("="*80)
    print("Project Builder Baseline Metrics Collection")
    print("Sprint 0, US-0.2")
    print("="*80)

    # Collect baseline
    baseline = collect_baseline()

    if baseline['total_artifacts'] == 0:
        sys.exit(1)

    # Display summary
    print(f"\n{'='*80}")
    print("BASELINE METRICS SUMMARY")
    print(f"{'='*80}")
    print(f"Total Artifacts Analyzed: {baseline['total_artifacts']}")
    print(f"\nQuality Metrics:")
    print(f"  Syntax Correctness: {baseline['syntax_correctness']:.1f}%")
    print(f"  Completeness:       {baseline['completeness']:.1f}%")
    print(f"  Conciseness:        {baseline['conciseness']:.1f}%")
    print(f"\nVerbosity:")
    print(f"  Avg Code Lines:     {baseline['avg_code_lines']:.1f}")
    print(f"  Avg Thinking Lines: {baseline['avg_thinking_lines']:.1f}")
    print(f"{'='*80}")

    # Calculate overall quality score
    # Weighted: Syntax 40%, Completeness 40%, Conciseness 20%
    overall = (
        baseline['syntax_correctness'] * 0.4 +
        baseline['completeness'] * 0.4 +
        baseline['conciseness'] * 0.2
    )
    print(f"\nOVERALL QUALITY SCORE: {overall:.1f}%")
    print(f"{'='*80}")

    # Save detailed results
    output_path = Path('metrics/baseline_manual_prompts.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(baseline, f, indent=2)

    print(f"\nDetailed results saved to: {output_path}")

    # Generate markdown report
    report_path = Path('docs/dspy/baseline_metrics.md')
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, 'w') as f:
        f.write("# Project Builder Baseline Metrics\n\n")
        f.write("**Date:** Sprint 0, US-0.2\n\n")
        f.write("## Summary\n\n")
        f.write(f"- **Total Artifacts:** {baseline['total_artifacts']}\n")
        f.write(f"- **Syntax Correctness:** {baseline['syntax_correctness']:.1f}%\n")
        f.write(f"- **Completeness:** {baseline['completeness']:.1f}%\n")
        f.write(f"- **Conciseness:** {baseline['conciseness']:.1f}%\n")
        f.write(f"- **Overall Score:** {overall:.1f}%\n\n")
        f.write("## Legend\n\n")
        f.write("- ✓: Syntactically correct Python code\n")
        f.write("- ✗: Syntax errors or not Python code\n")
        f.write("- T: Has TODOs/placeholders (incomplete)\n")
        f.write("- V: Has thinking/verbosity (not concise)\n\n")
        f.write("## Methodology\n\n")
        f.write("Analyzed artifacts from 5 test projects:\n")
        f.write("- test-artifacts-final\n")
        f.write("- test-improved-prompts\n")
        f.write("- test-api-final\n")
        f.write("- test-final-improved\n")
        f.write("- test-rest-api\n\n")
        f.write("Quality scoring:\n")
        f.write("- **Syntax Correctness (40%)**: Can code be parsed by Python AST?\n")
        f.write("- **Completeness (40%)**: No TODOs, placeholders, or NotImplementedError?\n")
        f.write("- **Conciseness (20%)**: No thinking/explanation before code?\n")

    print(f"Report generated: {report_path}")


if __name__ == '__main__':
    main()
