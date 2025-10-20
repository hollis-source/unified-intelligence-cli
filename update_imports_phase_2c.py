#!/usr/bin/env python3
"""
Phase 2C-2: Update imports from plural to singular directory names.

Updates:
- src.entities → src.entity
- src.interfaces → src.interface
- src.core.entities → src.core.entity
- src.core.ports → src.core.port
"""

import re
from pathlib import Path
from typing import List, Tuple

# Import replacements (old → new)
REPLACEMENTS = [
    (r'\bfrom src\.entities\b', 'from src.entity'),
    (r'\bimport src\.entities\b', 'import src.entity'),
    (r'\bfrom src\.interfaces\b', 'from src.interface'),
    (r'\bimport src\.interfaces\b', 'import src.interface'),
    (r'\bfrom src\.core\.entities\b', 'from src.core.entity'),
    (r'\bimport src\.core\.entities\b', 'import src.core.entity'),
    (r'\bfrom src\.core\.ports\b', 'from src.core.port'),
    (r'\bimport src\.core\.ports\b', 'import src.core.port'),
]


def find_files_to_update() -> List[Path]:
    """Find all Python files that need import updates."""
    files = set()

    # Search for files importing from old paths
    patterns = [
        'from src.entities',
        'from src.interfaces',
        'from src.core.entities',
        'from src.core.ports',
    ]

    for pattern in patterns:
        for file in Path('src').rglob('*.py'):
            # Skip the new directories
            if '/entity/' in str(file) or '/interface/' in str(file):
                continue
            if 'src/core/entity' in str(file) or 'src/core/port' in str(file):
                continue

            try:
                content = file.read_text()
                if pattern in content:
                    files.add(file)
            except Exception:
                pass

    return sorted(files)


def update_imports_in_file(file_path: Path) -> Tuple[int, List[str]]:
    """Update imports in a single file.

    Returns:
        (count of replacements, list of changes made)
    """
    content = file_path.read_text()
    original = content
    changes = []

    for pattern, replacement in REPLACEMENTS:
        matches = re.findall(pattern, content)
        if matches:
            content = re.sub(pattern, replacement, content)
            changes.extend([f"{match} → {replacement}" for match in matches])

    if content != original:
        file_path.write_text(content)
        return (len(changes), changes)

    return (0, [])


def main():
    """Main execution."""
    print("=" * 80)
    print("Phase 2C-2: Update Imports to Singular Directory Names")
    print("=" * 80)
    print()

    # Find files
    print("Finding files to update...")
    files = find_files_to_update()
    print(f"Found {len(files)} files to update")
    print()

    # Update files
    total_changes = 0
    updated_files = []

    for file in files:
        count, changes = update_imports_in_file(file)
        if count > 0:
            updated_files.append(file)
            total_changes += count
            print(f"✅ {file}")
            for change in changes:
                print(f"   - {change}")

    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Files updated: {len(updated_files)}")
    print(f"Total import changes: {total_changes}")
    print()

    if len(updated_files) == len(files):
        print("✅ Phase 2C-2 complete!")
    else:
        print(f"⚠️  Expected {len(files)} updates, completed {len(updated_files)}")

    print()
    print("Next steps:")
    print("1. Verify syntax: python3 -m py_compile $(find src -name '*.py')")
    print("2. Run tests: pytest tests/ -v")
    print("3. Commit: git commit -am 'Phase 2C-2: Update imports to singular directory names'")


if __name__ == "__main__":
    main()
