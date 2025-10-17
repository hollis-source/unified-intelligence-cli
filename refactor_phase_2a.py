#!/usr/bin/env python3
"""
Phase 2A: Variable Renames

Rename 16 variables (12 single-letter + 4 Hungarian notation) with zero breaking changes.
All renames are local scope only - no API changes.

Strategy:
- Single-letter variables: Rename to descriptive names based on context
- Hungarian notation: Remove type prefixes

Safety:
- All changes are local scope only
- No function signatures changed
- No breaking changes
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple


# Mapping of violations to their proper renames based on context analysis
#
# ANALYSIS NOTES:
# - TypeVar declarations (A, B, C) in morphism.py: These are CORRECT per Python conventions
# - "Hungarian notation" violations: ALL FALSE POSITIVES (strategy_keywords, integration_engineer, etc.)
# - Only REAL violations: single-letter loop variables 'm', 'f', 'a' in metrics.py and agent_team.py
#
# Total ACTUAL violations to fix: 9 (not 16)
VARIABLE_RENAMES = {
    # src/entities/metrics.py - single letter 'm' used for metrics objects in list comprehensions
    ("src/entities/metrics.py", 257, "m"): "metric",
    ("src/entities/metrics.py", 258, "m"): "metric",
    ("src/entities/metrics.py", 259, "m"): "metric",
    ("src/entities/metrics.py", 273, "m"): "routing_metric",
    ("src/entities/metrics.py", 283, "m"): "model_metric",
    ("src/entities/metrics.py", 287, "m"): "model_metric",
    ("src/entities/metrics.py", 295, "m"): "team_metric",

    # src/entities/metrics.py - single letter 'f' for file handle
    ("src/entities/metrics.py", 263, "f"): "file_handle",

    # src/entities/agent_team.py - single letter 'a' for agent
    ("src/entities/agent_team.py", 102, "a"): "agent",
}


def read_file_lines(file_path: Path) -> List[str]:
    """Read file and return lines."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.readlines()


def write_file_lines(file_path: Path, lines: List[str]) -> None:
    """Write lines to file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)


def rename_variable_in_line(line: str, old_name: str, new_name: str) -> str:
    """
    Rename variable in a line, being careful to only rename actual variable usage.
    
    Uses word boundaries to avoid partial matches.
    """
    # Pattern: word boundary + old_name + word boundary
    # This ensures we don't replace parts of other identifiers
    pattern = r'\b' + re.escape(old_name) + r'\b'
    return re.sub(pattern, new_name, line)


def apply_renames(renames: Dict[Tuple[str, int, str], str]) -> Dict[str, int]:
    """
    Apply all variable renames.
    
    Returns:
        Dictionary mapping file paths to number of renames applied
    """
    stats = {}
    
    # Group renames by file
    renames_by_file: Dict[str, List[Tuple[int, str, str]]] = {}
    for (file_path, line_num, old_name), new_name in renames.items():
        if file_path not in renames_by_file:
            renames_by_file[file_path] = []
        renames_by_file[file_path].append((line_num, old_name, new_name))
    
    # Process each file
    for file_path, file_renames in renames_by_file.items():
        path = Path(file_path)
        if not path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue
        
        # Read file
        lines = read_file_lines(path)
        
        # Apply renames (sort by line number to process in order)
        file_renames.sort(key=lambda x: x[0])
        renames_applied = 0
        
        for line_num, old_name, new_name in file_renames:
            if line_num <= 0 or line_num > len(lines):
                print(f"⚠️  Invalid line number {line_num} in {file_path}")
                continue
            
            # Line numbers are 1-based, list indices are 0-based
            idx = line_num - 1
            original_line = lines[idx]
            
            # Apply rename
            new_line = rename_variable_in_line(original_line, old_name, new_name)
            
            if new_line != original_line:
                lines[idx] = new_line
                renames_applied += 1
                print(f"  ✓ {file_path}:{line_num} - '{old_name}' → '{new_name}'")
            else:
                print(f"  ⚠️  {file_path}:{line_num} - '{old_name}' not found in line")
        
        # Write back if changes were made
        if renames_applied > 0:
            write_file_lines(path, lines)
            stats[file_path] = renames_applied
    
    return stats


def main():
    """Main execution."""
    print("=" * 80)
    print("Phase 2A: Variable Renames")
    print("=" * 80)
    print()
    
    print(f"Processing {len(VARIABLE_RENAMES)} variable renames...")
    print()
    
    # Apply renames
    stats = apply_renames(VARIABLE_RENAMES)
    
    # Summary
    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    total_renames = sum(stats.values())
    print(f"Files modified: {len(stats)}")
    print(f"Total renames: {total_renames}")
    print()
    
    for file_path, count in sorted(stats.items()):
        print(f"  {file_path}: {count} renames")
    
    print()
    print("✅ Phase 2A complete!")
    print()
    print("Next steps:")
    print("1. Review changes: git diff")
    print("2. Run tests: pytest tests/ -v")
    print("3. Commit: git add -A && git commit -m 'Phase 2A: Variable renames'")


if __name__ == "__main__":
    main()

