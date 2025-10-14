#!/usr/bin/env python3
"""
Phase 3B: Rename all code references from unified-intelligence-cli to autonomous-task-agent-dev-orchestration.

Updates:
- Python imports
- String references in code
- Path references
- CLI command references
- Comments and docstrings
"""

import re
from pathlib import Path
from typing import List, Tuple, Set

# Replacement mappings
REPLACEMENTS = [
    # Package name (hyphenated)
    (r'\bunified-intelligence-cli\b', 'autonomous-task-agent-dev-orchestration'),

    # Package name (underscored for Python imports)
    (r'\bunified_intelligence_cli\b', 'autonomous_task_agent_dev_orchestration'),

    # CLI command
    (r'\bui-cli\b', 'atado'),
    (r'\bui_cli\b', 'atado'),

    # Path references (common patterns)
    (r'/home/ui-cli_jake/unified-intelligence-cli', '/home/ui-cli_jake/autonomous-task-agent-dev-orchestration'),
    (r'~/unified-intelligence-cli', '~/autonomous-task-agent-dev-orchestration'),

    # Repository references
    (r'hollis-source/unified-intelligence-cli', 'hollis-source/autonomous-task-agent-dev-orchestration'),

    # Full name references in descriptions
    (r'Unified Intelligence CLI', 'Autonomous Task-Agent Dev Orchestration (ATADO)'),
    (r'unified intelligence cli', 'autonomous task-agent dev orchestration'),
]

# File patterns to process
INCLUDE_PATTERNS = [
    "*.py",
    "*.yaml",
    "*.yml",
    "*.md",
    "*.txt",
    "*.json",
    "*.sh",
    "*.service",
]

# Directories to skip
SKIP_DIRS = {
    ".git",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    ".remote_sync",
    "backups",
}


def should_process_file(file_path: Path) -> bool:
    """Check if file should be processed."""
    # Skip if in excluded directory
    for part in file_path.parts:
        if part in SKIP_DIRS:
            return False

    # Check if matches include pattern
    for pattern in INCLUDE_PATTERNS:
        if file_path.match(pattern):
            return True

    return False


def find_files_to_update() -> List[Path]:
    """Find all files that need updates."""
    files: Set[Path] = set()

    for pattern in INCLUDE_PATTERNS:
        for file in Path('.').rglob(pattern):
            if should_process_file(file) and file.is_file():
                files.add(file)

    return sorted(files)


def update_file(file_path: Path) -> Tuple[int, List[str]]:
    """Update references in a single file.

    Returns:
        (count of changes, list of changes made)
    """
    try:
        content = file_path.read_text(encoding='utf-8')
    except (UnicodeDecodeError, PermissionError):
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
        file_path.write_text(content, encoding='utf-8')
        return (len(changes), changes)

    return (0, [])


def main():
    """Main execution."""
    print("=" * 80)
    print("Phase 3B: Rename References to autonomous-task-agent-dev-orchestration")
    print("=" * 80)
    print()

    # Find files
    print("Finding files to update...")
    files = find_files_to_update()
    print(f"Found {len(files)} files to check")
    print()

    # Update files
    total_changes = 0
    updated_files = []

    for file in files:
        count, changes = update_file(file)
        if count > 0:
            updated_files.append(file)
            total_changes += count
            print(f"✅ {file}")
            for change in changes[:3]:  # Show first 3 changes
                print(f"   - {change}")
            if len(changes) > 3:
                print(f"   ... and {len(changes) - 3} more")

    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Files updated: {len(updated_files)}")
    print(f"Total changes: {total_changes}")
    print()

    if updated_files:
        print("✅ Phase 3B complete!")
        print()
        print("Next steps:")
        print("1. Test imports: python3 -c 'import src.main'")
        print("2. Test CLI: atado --help (after reinstalling package)")
        print("3. Run tests: pytest tests/ -v")
        print("4. Commit: git commit -am 'Phase 3B: Update all code references'")
    else:
        print("⚠️  No files needed updates")


if __name__ == "__main__":
    main()
