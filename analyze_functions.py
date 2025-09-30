#!/usr/bin/env python3
"""Analyze function lengths to find violations of <20 line rule."""

import ast
import sys
from pathlib import Path
from typing import List, Tuple


def analyze_function_length(file_path: Path) -> List[Tuple[str, int, int]]:
    """
    Analyze a Python file for function lengths.

    Returns:
        List of (function_name, start_line, length) tuples for functions >20 lines
    """
    try:
        with open(file_path, 'r') as f:
            tree = ast.parse(f.read(), filename=str(file_path))
    except Exception as e:
        print(f"Error parsing {file_path}: {e}", file=sys.stderr)
        return []

    violations = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Calculate function body length
            if node.body:
                start = node.lineno
                end = max(
                    getattr(stmt, 'end_lineno', stmt.lineno)
                    for stmt in node.body
                )
                length = end - start + 1

                if length > 20:
                    violations.append((node.name, start, length))

    return violations


def main():
    """Scan all Python files in src/ for long functions."""
    src_path = Path("src")

    if not src_path.exists():
        print("Error: src/ directory not found")
        sys.exit(1)

    all_violations = []

    for py_file in sorted(src_path.rglob("*.py")):
        violations = analyze_function_length(py_file)
        if violations:
            all_violations.append((py_file, violations))

    if not all_violations:
        print("✅ No functions exceed 20 lines!")
        return

    print("=" * 80)
    print("FUNCTIONS EXCEEDING 20 LINES (Clean Code Violations)")
    print("=" * 80)
    print()

    total_violations = 0
    for file_path, violations in all_violations:
        print(f"📄 {file_path}")
        for func_name, start_line, length in violations:
            print(f"   Line {start_line:4d}: {func_name:30s} ({length} lines)")
            total_violations += 1
        print()

    print("=" * 80)
    print(f"Total violations: {total_violations}")
    print("=" * 80)


if __name__ == "__main__":
    main()