"""Clean Agile Refactoring Tasks - Code quality analysis and improvement.

Clean Architecture: Use Cases layer (business logic for refactoring).
SOLID: SRP - each task has one responsibility.

This module implements tasks for analyzing code quality and generating
refactoring recommendations based on Clean Code and SOLID principles.
"""

import asyncio
import subprocess
import re
from typing import Any, Dict, List
from pathlib import Path


async def analyze_function_length(input_data: Any = None) -> Dict[str, Any]:
    """
    Analyze Python functions for excessive length (>20 lines per Clean Code).

    Returns:
        List of functions exceeding recommended length
    """
    src_files = list(Path("src").rglob("*.py"))

    long_functions = []

    for file_path in src_files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                lines = content.split('\n')

            # Simple regex to find function definitions
            in_function = False
            function_start = 0
            function_name = ""
            indent_level = 0

            for i, line in enumerate(lines):
                # Check for function definition
                if re.match(r'^\s*(async\s+)?def\s+(\w+)', line):
                    match = re.match(r'^(\s*)(async\s+)?def\s+(\w+)', line)
                    if match:
                        in_function = True
                        function_start = i + 1
                        function_name = match.group(3)
                        indent_level = len(match.group(1))

                # Check if function ended (dedent or new function)
                elif in_function:
                    if line.strip() and not line.startswith(' ' * (indent_level + 4)):
                        # Function ended
                        function_length = i - function_start
                        if function_length > 20:
                            long_functions.append({
                                "file": str(file_path),
                                "function": function_name,
                                "line": function_start,
                                "length": function_length,
                                "severity": "high" if function_length > 50 else "medium"
                            })
                        in_function = False

        except Exception as e:
            continue  # Skip files with encoding issues

    return {
        "task": "analyze_function_length",
        "status": "success",
        "long_functions_count": len(long_functions),
        "long_functions": long_functions[:10],  # Return top 10 longest
        "recommendation": f"Found {len(long_functions)} functions >20 lines. Refactor to smaller, focused functions."
    }


async def analyze_code_duplication(input_data: Any = None) -> Dict[str, Any]:
    """
    Detect code duplication using simple heuristics.

    Returns:
        Potential code duplication issues
    """
    # This is a simplified analysis - in production would use tools like pylint
    src_files = list(Path("src").rglob("*.py"))

    # Count similar imports as a proxy for duplication
    import_patterns = {}

    for file_path in src_files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            # Find import statements
            imports = re.findall(r'^(from .+ import .+|import .+)$', content, re.MULTILINE)
            for imp in imports:
                if imp not in import_patterns:
                    import_patterns[imp] = []
                import_patterns[imp].append(str(file_path))

        except Exception:
            continue

    # Find patterns used in many files (potential utility candidates)
    common_patterns = {k: v for k, v in import_patterns.items() if len(v) > 5}

    return {
        "task": "analyze_code_duplication",
        "status": "success",
        "common_import_count": len(common_patterns),
        "recommendation": f"Found {len(common_patterns)} import patterns used across multiple files. Consider extracting common utilities."
    }


async def analyze_naming_conventions(input_data: Any = None) -> Dict[str, Any]:
    """
    Analyze code for poor naming (single letters, unclear names).

    Returns:
        Naming convention violations
    """
    src_files = list(Path("src").rglob("*.py"))

    naming_issues = []

    for file_path in src_files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                lines = content.split('\n')

            for i, line in enumerate(lines):
                # Check for single-letter variable names (except common loop vars)
                single_letters = re.findall(r'\b([a-z])\s*=\s*', line)
                for letter in single_letters:
                    if letter not in ['i', 'j', 'k', 'x', 'y', 'z', 'n', 'e', 'f']:
                        naming_issues.append({
                            "file": str(file_path),
                            "line": i + 1,
                            "issue": f"Single-letter variable '{letter}'",
                            "severity": "low"
                        })

                # Check for unclear abbreviations
                unclear_abbrevs = re.findall(r'\b(tmp|temp|var|data|info|mgr|svc)\s*=', line.lower())
                if unclear_abbrevs:
                    naming_issues.append({
                        "file": str(file_path),
                        "line": i + 1,
                        "issue": f"Unclear abbreviation: {unclear_abbrevs[0]}",
                        "severity": "low"
                    })

        except Exception:
            continue

    return {
        "task": "analyze_naming_conventions",
        "status": "success",
        "naming_issues_count": len(naming_issues),
        "naming_issues": naming_issues[:10],  # Top 10
        "recommendation": f"Found {len(naming_issues)} naming convention issues. Use descriptive names."
    }


async def analyze_test_coverage(input_data: Any = None) -> Dict[str, Any]:
    """
    Analyze test coverage using pytest-cov.

    Returns:
        Test coverage metrics
    """
    result = subprocess.run(
        ["venv/bin/pytest", "tests/", "--cov=src", "--cov-report=term-missing", "-q"],
        capture_output=True,
        text=True,
        cwd=Path.cwd()
    )

    output = result.stdout + result.stderr

    # Parse coverage percentage
    coverage_match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', output)
    coverage_pct = int(coverage_match.group(1)) if coverage_match else 0

    return {
        "task": "analyze_test_coverage",
        "status": "success",
        "coverage_percentage": coverage_pct,
        "target_coverage": 90,
        "meets_target": coverage_pct >= 90,
        "recommendation": f"Coverage at {coverage_pct}%. Target: 90%. {'✅ Good!' if coverage_pct >= 90 else '⚠️ Increase test coverage.'}"
    }


async def detect_solid_violations(input_data: Any = None) -> Dict[str, Any]:
    """
    Detect potential SOLID principle violations.

    Returns:
        SOLID violations found
    """
    src_files = list(Path("src").rglob("*.py"))

    violations = []

    for file_path in src_files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            # SRP violation: Classes with too many methods
            class_matches = re.findall(r'class\s+(\w+)', content)
            for class_name in class_matches:
                method_count = len(re.findall(rf'class {class_name}.*?(?=class|\Z)', content, re.DOTALL))
                if method_count > 10:
                    violations.append({
                        "file": str(file_path),
                        "type": "SRP",
                        "issue": f"Class {class_name} may have too many responsibilities",
                        "severity": "medium"
                    })

            # DIP violation: Direct imports of concrete classes
            concrete_imports = re.findall(r'from src\.\w+\.\w+ import \w+Adapter', content)
            if len(concrete_imports) > 3:
                violations.append({
                    "file": str(file_path),
                    "type": "DIP",
                    "issue": "Many direct adapter imports - consider using factory/DI",
                    "severity": "low"
                })

        except Exception:
            continue

    return {
        "task": "detect_solid_violations",
        "status": "success",
        "violations_count": len(violations),
        "violations": violations[:10],
        "recommendation": f"Found {len(violations)} potential SOLID violations."
    }


async def generate_refactoring_plan(input_data: Any = None) -> Dict[str, Any]:
    """
    Generate comprehensive refactoring plan based on analysis results.

    Args:
        input_data: Combined analysis from previous tasks

    Returns:
        Prioritized refactoring plan
    """
    plan = {
        "high_priority": [],
        "medium_priority": [],
        "low_priority": []
    }

    # Extract data from input if available
    if isinstance(input_data, dict):
        # Check for long functions
        if input_data.get('long_functions_count', 0) > 0:
            plan["high_priority"].append({
                "task": "Refactor long functions",
                "count": input_data['long_functions_count'],
                "action": "Break functions >20 lines into smaller, focused functions",
                "principle": "Clean Code - Small Functions"
            })

        # Check for test coverage
        if input_data.get('coverage_percentage', 100) < 90:
            plan["high_priority"].append({
                "task": "Increase test coverage",
                "current": f"{input_data.get('coverage_percentage', 0)}%",
                "target": "90%",
                "action": "Add tests for uncovered code paths",
                "principle": "Clean Agile - TDD"
            })

        # Check for SOLID violations
        if input_data.get('violations_count', 0) > 0:
            plan["medium_priority"].append({
                "task": "Fix SOLID violations",
                "count": input_data['violations_count'],
                "action": "Apply SOLID principles (SRP, DIP, OCP)",
                "principle": "SOLID Principles"
            })

        # Check for naming issues
        if input_data.get('naming_issues_count', 0) > 0:
            plan["low_priority"].append({
                "task": "Improve naming",
                "count": input_data['naming_issues_count'],
                "action": "Use descriptive, intention-revealing names",
                "principle": "Clean Code - Meaningful Names"
            })

    return {
        "task": "generate_refactoring_plan",
        "status": "success",
        "plan": plan,
        "total_tasks": len(plan["high_priority"]) + len(plan["medium_priority"]) + len(plan["low_priority"]),
        "recommendation": "Address high-priority items first, commit after each refactoring"
    }


async def prioritize_refactorings(input_data: Any = None) -> Dict[str, Any]:
    """
    Prioritize refactoring tasks by impact and effort.

    Args:
        input_data: Refactoring plan

    Returns:
        Prioritized list of refactorings
    """
    if not isinstance(input_data, dict) or 'plan' not in input_data:
        return {
            "task": "prioritize_refactorings",
            "status": "success",
            "prioritized_tasks": [],
            "recommendation": "No refactorings needed - code quality is good!"
        }

    plan = input_data['plan']

    prioritized = []

    # High priority first
    for i, item in enumerate(plan.get("high_priority", [])):
        prioritized.append({
            "priority": i + 1,
            "level": "HIGH",
            "task": item['task'],
            "action": item['action'],
            "principle": item['principle'],
            "estimated_time": "2-4 hours"
        })

    # Medium priority
    for i, item in enumerate(plan.get("medium_priority", [])):
        prioritized.append({
            "priority": len(plan.get("high_priority", [])) + i + 1,
            "level": "MEDIUM",
            "task": item['task'],
            "action": item['action'],
            "principle": item['principle'],
            "estimated_time": "1-2 hours"
        })

    # Low priority
    for i, item in enumerate(plan.get("low_priority", [])):
        prioritized.append({
            "priority": len(plan.get("high_priority", [])) + len(plan.get("medium_priority", [])) + i + 1,
            "level": "LOW",
            "task": item['task'],
            "action": item['action'],
            "principle": item['principle'],
            "estimated_time": "30-60 min"
        })

    return {
        "task": "prioritize_refactorings",
        "status": "success",
        "prioritized_tasks": prioritized,
        "total_tasks": len(prioritized),
        "recommendation": f"Work through {len(prioritized)} refactorings in priority order. Commit after each."
    }


async def create_refactoring_report(input_data: Any = None) -> Dict[str, Any]:
    """
    Create comprehensive refactoring report.

    Args:
        input_data: Prioritized refactoring tasks

    Returns:
        Formatted refactoring report
    """
    if not isinstance(input_data, dict):
        return {
            "task": "create_refactoring_report",
            "status": "success",
            "report": "No refactorings needed - codebase follows Clean Code/SOLID principles!"
        }

    tasks = input_data.get('prioritized_tasks', [])

    report_lines = [
        "# Clean Agile Refactoring Report",
        "",
        "## Summary",
        f"Total refactoring tasks: {len(tasks)}",
        "",
        "## Prioritized Tasks",
        ""
    ]

    for task in tasks:
        report_lines.append(f"### {task['priority']}. [{task['level']}] {task['task']}")
        report_lines.append(f"**Action**: {task['action']}")
        report_lines.append(f"**Principle**: {task['principle']}")
        report_lines.append(f"**Estimated Time**: {task['estimated_time']}")
        report_lines.append("")

    report_lines.extend([
        "## Clean Agile Practices",
        "",
        "1. **Small, Frequent Commits**: Commit after each refactoring (200-500 LOC)",
        "2. **Tests First**: Ensure tests pass before AND after each refactoring",
        "3. **Continuous Refactoring**: Refactor as you go, don't batch",
        "4. **Pair Programming**: Review with teammate or AI assistant",
        "",
        "---",
        "Generated via DSL + unified-intelligence-cli"
    ])

    report = "\n".join(report_lines)

    return {
        "task": "create_refactoring_report",
        "status": "success",
        "report": report,
        "file": "docs/REFACTORING_PLAN.md",
        "recommendation": "Save report and work through tasks systematically"
    }
