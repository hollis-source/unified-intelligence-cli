#!/usr/bin/env python3
"""
Phase 3C: Update remaining source code and test files.

Focus on src/ and tests/ directories.
"""

import re
from pathlib import Path
from typing import List, Tuple

# Replacement mappings
REPLACEMENTS = [
    # Package name
    (r'\bunified-intelligence-cli\b', 'autonomous-task-agent-dev-orchestration'),
    (r'\bunified_intelligence_cli\b', 'autonomous_task_agent_dev_orchestration'),

    # CLI command
    (r'\bui-cli\b', 'atado'),
    (r'\bui_cli\b', 'atado'),

    # Path references
    (r'/home/ui-cli_jake/unified-intelligence-cli', '/home/ui-cli_jake/autonomous-task-agent-dev-orchestration'),
    (r'~/unified-intelligence-cli', '~/autonomous-task-agent-dev-orchestration'),

    # Repository
    (r'hollis-source/unified-intelligence-cli', 'hollis-source/autonomous-task-agent-dev-orchestration'),
]

# Target directories
TARGET_DIRS = ['src', 'tests']


def find_files() -> List[Path]:
    """Find Python files in target directories."""
    files = []
    for dir_name in TARGET_DIRS:
        dir_path = Path(dir_name)
        if dir_path.exists():
            files.extend(dir_path.rglob('*.py'))
    return sorted(files)


def update_file(file_path: Path) -> Tuple[int, List[str]]:
    """Update references in a file."""
    try:
        content = file_path.read_text(encoding='utf-8')
    except (UnicodeDecodeError, PermissionError) as e:
        print(f"⚠️  Skipping {file_path}: {e}")
        return (0, [])

    original = content
    changes = []

    for pattern, replacement in REPLACEMENTS:
        matches = list(re.finditer(pattern, content))
        if matches:
            content = re.sub(pattern, replacement, content)
            for match in matches:
                changes.append(f"{match.group()} → {replacement}")

    if content != original:
        try:
            file_path.write_text(content, encoding='utf-8')
            return (len(changes), changes)
        except PermissionError as e:
            print(f"⚠️  Cannot write {file_path}: {e}")
            return (0, [])

    return (0, [])


def main():
    """Main execution."""
    print("=" * 80)
    print("Phase 3C: Update Source Code and Tests")
    print("=" * 80)
    print()

    files = find_files()
    print(f"Found {len(files)} Python files in {TARGET_DIRS}")
    print()

    total_changes = 0
    updated_files = []

    for file in files:
        count, changes = update_file(file)
        if count > 0:
            updated_files.append(file)
            total_changes += count
            print(f"✅ {file}")
            for change in changes[:2]:
                print(f"   - {change}")
            if len(changes) > 2:
                print(f"   ... and {len(changes) - 2} more")

    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Files updated: {len(updated_files)}")
    print(f"Total changes: {total_changes}")
    print()

    if updated_files:
        print("✅ Phase 3C complete!")
        print()
        print("Next: Test imports and commit")
    else:
        print("ℹ️  No files needed updates")


if __name__ == "__main__":
    main()
