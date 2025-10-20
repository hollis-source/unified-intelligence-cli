#!/usr/bin/env python3
"""
Phase 2B: Function Renames - Context-aware refactoring script.

Renames 12 functions to follow verb-noun patterns with backward compatibility.
Based on PHASE_2B_INSTRUCTIONS.md specifications.
"""

import re
from pathlib import Path
from typing import Dict, Tuple

# Rename specifications: (file, old_name, new_name, line_approx, is_inner_function)
RENAMES = [
    # File 1: src/entities/category_theory/morphism.py
    ("src/entities/category_theory/morphism.py", "identity", "create_identity", 93, False),
    ("src/entities/category_theory/morphism.py", "composed_transform", "apply_composed_transform", 77, True),

    # File 2: src/entities/category_theory/workflow_morphism.py
    ("src/entities/category_theory/workflow_morphism.py", "htn_flatten", "flatten_htn", 25, False),
    ("src/entities/category_theory/workflow_morphism.py", "htn_remove_identity", "remove_htn_identity", 86, False),
    ("src/entities/category_theory/workflow_morphism.py", "htn_simplify", "simplify_htn", 143, False),
    ("src/entities/category_theory/workflow_morphism.py", "workflow_optimize", "optimize_workflow", 274, False),

    # File 3: src/entities/graph/graph.py
    ("src/entities/graph/graph.py", "node_count", "count_nodes", 165, False),
    ("src/entities/graph/graph.py", "edge_count", "count_edges", 169, False),
    ("src/entities/graph/graph.py", "dfs", "traverse_dfs", 173, False),
    ("src/entities/graph/graph.py", "bfs", "traverse_bfs", 212, False),
    ("src/entities/graph/graph.py", "topological_sort", "sort_topologically", 290, False),
    ("src/entities/graph/graph.py", "subgraph", "extract_subgraph", 349, False),
]


def read_file(file_path: Path) -> list:
    """Read file and return lines."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.readlines()


def write_file(file_path: Path, lines: list):
    """Write lines to file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)


def rename_function_definition(lines: list, old_name: str, new_name: str, line_hint: int, is_inner: bool) -> Tuple[list, int]:
    """
    Rename function definition and add deprecated alias if not inner function.

    Returns: (modified_lines, functions_renamed_count)
    """
    modified_lines = lines.copy()
    count = 0

    # Find function definition
    pattern = rf'(\s*)def {re.escape(old_name)}\('

    for i, line in enumerate(lines):
        # Look near the hint line (±20 lines)
        if abs(i + 1 - line_hint) > 20:
            continue

        match = re.match(pattern, line)
        if match:
            indent = match.group(1)

            # Rename the function
            modified_lines[i] = re.sub(
                rf'(\s*)def {re.escape(old_name)}\(',
                rf'\1def {new_name}(',
                line
            )
            count += 1
            print(f"  ✓ Renamed function definition: {old_name} → {new_name} (line {i+1})")

            # Add deprecated alias if not inner function
            if not is_inner:
                # Find end of function to add alias after
                alias_lines = create_deprecated_alias(old_name, new_name, indent, lines, i)

                # Find where to insert (after the function body)
                insert_pos = find_function_end(lines, i) + 1

                # Insert alias
                for offset, alias_line in enumerate(alias_lines):
                    modified_lines.insert(insert_pos + offset, alias_line)

                print(f"  ✓ Added deprecated alias: {old_name}() → {new_name}()")

            break

    return modified_lines, count


def create_deprecated_alias(old_name: str, new_name: str, indent: str, lines: list, func_start_line: int) -> list:
    """Create deprecated alias function."""

    # Extract function signature
    signature_line = lines[func_start_line]

    # Check if it's a staticmethod or classmethod
    is_static = any('@staticmethod' in lines[i] for i in range(max(0, func_start_line-5), func_start_line))
    is_classmethod = any('@classmethod' in lines[i] for i in range(max(0, func_start_line-5), func_start_line))

    # Extract parameters
    match = re.search(rf'def {re.escape(new_name)}\((.*?)\)', signature_line)
    if match:
        params = match.group(1).strip()
    else:
        params = ""

    # Extract return type if present
    return_type = ""
    if '->' in signature_line:
        return_type = ' ' + signature_line.split('->')[1].strip()

    alias_lines = [
        '\n',
        f'{indent}# Backward compatibility alias (deprecated)\n',
    ]

    if is_static:
        alias_lines.append(f'{indent}@staticmethod\n')
    elif is_classmethod:
        alias_lines.append(f'{indent}@classmethod\n')

    alias_lines.extend([
        f'{indent}def {old_name}({params}){return_type}\n',
        f'{indent}    """DEPRECATED: Use {new_name}() instead."""\n',
        f'{indent}    import warnings\n',
        f'{indent}    warnings.warn(\n',
        f'{indent}        "{old_name}() is deprecated, use {new_name}() instead",\n',
        f'{indent}        DeprecationWarning,\n',
        f'{indent}        stacklevel=2\n',
        f'{indent}    )\n',
    ])

    # Call the new function
    if is_static or is_classmethod:
        # For static/class methods, need class name - extract from context
        class_name = find_class_name(lines, func_start_line)
        if class_name:
            if params:
                # Extract just parameter names (remove type hints)
                param_names = ', '.join(p.split(':')[0].split('=')[0].strip() for p in params.split(','))
            else:
                param_names = ""
            alias_lines.append(f'{indent}    return {class_name}.{new_name}({param_names})\n')
        else:
            alias_lines.append(f'{indent}    return {new_name}({params})\n')
    else:
        # Instance method
        if params.startswith('self'):
            # Extract parameter names after self
            if ',' in params:
                param_names = ', '.join(p.split(':')[0].split('=')[0].strip() for p in params.split(',')[1:])
            else:
                param_names = ""
            alias_lines.append(f'{indent}    return self.{new_name}({param_names})\n')
        else:
            alias_lines.append(f'{indent}    return {new_name}({params})\n')

    return alias_lines


def find_class_name(lines: list, start_line: int) -> str:
    """Find the class name by searching backwards."""
    for i in range(start_line, -1, -1):
        match = re.match(r'^class\s+(\w+)', lines[i])
        if match:
            return match.group(1)
    return None


def find_function_end(lines: list, start_line: int) -> int:
    """Find the end of a function by tracking indentation."""
    # Get base indentation of function
    base_indent = len(lines[start_line]) - len(lines[start_line].lstrip())

    # Search for next line with same or less indentation (not including docstrings/comments)
    in_docstring = False
    for i in range(start_line + 1, len(lines)):
        line = lines[i]
        stripped = line.strip()

        # Handle docstrings
        if '"""' in line or "'''" in line:
            in_docstring = not in_docstring
            continue

        if in_docstring or not stripped or stripped.startswith('#'):
            continue

        # Check indentation
        current_indent = len(line) - len(line.lstrip())
        if current_indent <= base_indent:
            return i - 1

    return len(lines) - 1


def main():
    """Main execution."""
    print("=" * 80)
    print("Phase 2B: Function Renames (Context-Aware)")
    print("=" * 80)
    print()

    # Group renames by file
    files_to_process = {}
    for file_path, old_name, new_name, line_hint, is_inner in RENAMES:
        if file_path not in files_to_process:
            files_to_process[file_path] = []
        files_to_process[file_path].append((old_name, new_name, line_hint, is_inner))

    total_renamed = 0

    # Process each file
    for file_path, renames in files_to_process.items():
        print(f"📁 Processing: {file_path}")
        print(f"   {len(renames)} functions to rename")
        print()

        path = Path(file_path)
        if not path.exists():
            print(f"  ⚠️  File not found: {file_path}")
            continue

        # Read file
        lines = read_file(path)
        modified_lines = lines

        # Apply all renames for this file
        for old_name, new_name, line_hint, is_inner in renames:
            modified_lines, count = rename_function_definition(
                modified_lines, old_name, new_name, line_hint, is_inner
            )
            total_renamed += count

        # Write back
        if modified_lines != lines:
            write_file(path, modified_lines)
            print(f"  ✅ File updated: {file_path}")
        else:
            print(f"  ⚠️  No changes made to {file_path}")

        print()

    # Summary
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Files processed: {len(files_to_process)}")
    print(f"Functions renamed: {total_renamed}")
    print()

    if total_renamed == len(RENAMES):
        print("✅ Phase 2B complete!")
    else:
        print(f"⚠️  Expected {len(RENAMES)} renames, completed {total_renamed}")

    print()
    print("Next steps:")
    print("1. Review changes: git diff")
    print("2. Run tests: pytest tests/ -v")
    print("3. Commit changes")


if __name__ == "__main__":
    main()
