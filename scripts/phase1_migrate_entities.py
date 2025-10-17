#!/usr/bin/env python3
"""Phase 1: Entity Consolidation - Automated Migration Script

This script migrates all imports from src.entities to src.entity,
consolidating duplicate entity implementations.

Usage:
    python scripts/phase1_migrate_entities.py [--dry-run] [--verbose]

Options:
    --dry-run: Show what would be changed without making changes
    --verbose: Show detailed output

Safety:
    - Creates backup before making changes
    - Validates all imports after migration
    - Provides rollback instructions
"""

import os
import re
import sys
import shutil
import argparse
from pathlib import Path
from typing import List, Tuple, Set
from datetime import datetime


class EntityMigrator:
    """Migrates imports from src.entities to src.entity."""
    
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.root = Path(__file__).parent.parent
        self.src_dir = self.root / "src"
        self.backup_dir = self.root / "backups" / f"entity_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.files_modified: List[Path] = []
        self.errors: List[Tuple[Path, str]] = []
    
    def log(self, message: str, force: bool = False):
        """Log message if verbose or force."""
        if self.verbose or force:
            print(message)
    
    def create_backup(self):
        """Create backup of src/ directory."""
        if self.dry_run:
            self.log("DRY RUN: Would create backup", force=True)
            return
        
        self.log(f"Creating backup: {self.backup_dir}", force=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup src/entities directory
        entities_src = self.src_dir / "entities"
        if entities_src.exists():
            entities_backup = self.backup_dir / "entities"
            shutil.copytree(entities_src, entities_backup)
            self.log(f"✓ Backed up: {entities_src}")
        
        # Backup all files that will be modified
        files_to_backup = self.find_files_with_entities_imports()
        for file_path in files_to_backup:
            relative_path = file_path.relative_to(self.root)
            backup_path = self.backup_dir / relative_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_path)
            self.log(f"✓ Backed up: {relative_path}")
        
        self.log(f"✓ Backup complete: {len(files_to_backup)} files", force=True)
    
    def find_files_with_entities_imports(self) -> List[Path]:
        """Find all Python files importing from src.entities."""
        files = []
        for py_file in self.src_dir.rglob("*.py"):
            try:
                content = py_file.read_text()
                if "from src.entities" in content or "import src.entities" in content:
                    files.append(py_file)
            except Exception as e:
                self.log(f"Warning: Could not read {py_file}: {e}")
        
        return files
    
    def migrate_file(self, file_path: Path) -> bool:
        """Migrate imports in a single file."""
        try:
            content = file_path.read_text()
            original_content = content
            
            # Pattern 1: from src.entities.X import Y
            pattern1 = r'from src\.entities\.([\w.]+) import'
            replacement1 = r'from src.entity.\1 import'
            content = re.sub(pattern1, replacement1, content)
            
            # Pattern 2: import src.entities.X
            pattern2 = r'import src\.entities\.([\w.]+)'
            replacement2 = r'import src.entity.\1'
            content = re.sub(pattern2, replacement2, content)
            
            # Pattern 3: import src.entities
            pattern3 = r'import src\.entities\b'
            replacement3 = r'import src.entity'
            content = re.sub(pattern3, replacement3, content)
            
            if content != original_content:
                if self.dry_run:
                    self.log(f"DRY RUN: Would migrate {file_path.relative_to(self.root)}")
                    return True
                
                file_path.write_text(content)
                self.files_modified.append(file_path)
                self.log(f"✓ Migrated: {file_path.relative_to(self.root)}")
                return True
            
            return False
            
        except Exception as e:
            error_msg = f"Failed to migrate {file_path}: {e}"
            self.errors.append((file_path, str(e)))
            self.log(f"✗ {error_msg}")
            return False
    
    def migrate_all_files(self):
        """Migrate all files with entities imports."""
        files = self.find_files_with_entities_imports()
        self.log(f"\nFound {len(files)} files to migrate:", force=True)
        
        for file_path in files:
            self.log(f"  - {file_path.relative_to(self.root)}")
        
        self.log("\nMigrating imports...", force=True)
        
        migrated_count = 0
        for file_path in files:
            if self.migrate_file(file_path):
                migrated_count += 1
        
        self.log(f"\n✓ Migrated {migrated_count}/{len(files)} files", force=True)
    
    def validate_imports(self) -> bool:
        """Validate that all imports are correct after migration."""
        if self.dry_run:
            self.log("\nDRY RUN: Would validate imports", force=True)
            return True
        
        self.log("\nValidating imports...", force=True)
        
        # Check for remaining src.entities imports
        remaining = []
        for py_file in self.src_dir.rglob("*.py"):
            try:
                content = py_file.read_text()
                if "from src.entities" in content or "import src.entities" in content:
                    remaining.append(py_file)
            except Exception:
                pass
        
        if remaining:
            self.log(f"✗ Found {len(remaining)} files still importing from src.entities:", force=True)
            for file_path in remaining:
                self.log(f"  - {file_path.relative_to(self.root)}", force=True)
            return False
        
        self.log("✓ No remaining src.entities imports found", force=True)
        
        # Try to compile all modified files
        self.log("\nValidating Python syntax...", force=True)
        compile_errors = []
        for file_path in self.files_modified:
            try:
                with open(file_path, 'r') as f:
                    compile(f.read(), str(file_path), 'exec')
            except SyntaxError as e:
                compile_errors.append((file_path, str(e)))
        
        if compile_errors:
            self.log(f"✗ Found {len(compile_errors)} files with syntax errors:", force=True)
            for file_path, error in compile_errors:
                self.log(f"  - {file_path.relative_to(self.root)}: {error}", force=True)
            return False
        
        self.log(f"✓ All {len(self.files_modified)} modified files have valid syntax", force=True)
        return True
    
    def print_summary(self):
        """Print migration summary."""
        print("\n" + "="*80)
        print("MIGRATION SUMMARY")
        print("="*80)
        
        if self.dry_run:
            print("\n🔍 DRY RUN MODE - No changes were made")
        
        print(f"\n📊 Statistics:")
        print(f"  - Files modified: {len(self.files_modified)}")
        print(f"  - Errors: {len(self.errors)}")
        
        if self.errors:
            print(f"\n❌ Errors encountered:")
            for file_path, error in self.errors:
                print(f"  - {file_path.relative_to(self.root)}: {error}")
        
        if not self.dry_run and self.files_modified:
            print(f"\n💾 Backup location: {self.backup_dir}")
            print(f"\n📝 Rollback instructions:")
            print(f"  cp -r {self.backup_dir}/src/* {self.src_dir}/")
        
        print("\n" + "="*80)
    
    def run(self) -> bool:
        """Run the complete migration process."""
        try:
            self.log("="*80, force=True)
            self.log("PHASE 1: ENTITY CONSOLIDATION - MIGRATION", force=True)
            self.log("="*80, force=True)
            
            # Step 1: Create backup
            self.log("\nStep 1: Creating backup...", force=True)
            self.create_backup()
            
            # Step 2: Migrate imports
            self.log("\nStep 2: Migrating imports...", force=True)
            self.migrate_all_files()
            
            # Step 3: Validate
            self.log("\nStep 3: Validating migration...", force=True)
            validation_passed = self.validate_imports()
            
            # Step 4: Summary
            self.print_summary()
            
            if not validation_passed:
                print("\n⚠️  Validation failed! Review errors above.")
                if not self.dry_run:
                    print(f"To rollback: cp -r {self.backup_dir}/src/* {self.src_dir}/")
                return False
            
            if self.dry_run:
                print("\n✅ Dry run complete! Run without --dry-run to apply changes.")
            else:
                print("\n✅ Migration complete!")
                print("\nNext steps:")
                print("  1. Run tests: pytest tests/ -v")
                print("  2. Check imports: python -m py_compile src/**/*.py")
                print("  3. If tests pass, remove src/entities/: rm -rf src/entities/")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate imports from src.entities to src.entity"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    
    args = parser.parse_args()
    
    migrator = EntityMigrator(dry_run=args.dry_run, verbose=args.verbose)
    success = migrator.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

