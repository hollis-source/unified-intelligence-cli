# Phase 2: Critical Priority - Detailed Execution Plan

**Document Version:** 1.0
**Date:** October 14, 2025
**Status:** Ready for Execution
**Estimated Time:** 22.2 hours
**Total Violations:** 112

---

## Executive Summary

### Plan Overview

Phase 2 will be executed in **4 safe, incremental sub-phases** (2A-2D) with automated tooling, comprehensive testing, and rollback procedures at each step.

**Key Insight:** While dependency analysis suggested 152+ dependencies for directory renames, actual imports are much lower:
- `src.entities`: 40 imports
- `src.interfaces`: 21 imports
- Total affected: ~61 files

### Violation Breakdown

| Type | Count | Risk | Approach |
|------|-------|------|----------|
| **function_no_verb_noun** | 92 | Medium | Automated with aliases |
| **variable_single_letter** | 12 | Low | Automated |
| **directory_plural** | 4 | High | Semi-automated with git mv |
| **variable_hungarian_notation** | 4 | Low | Automated |

### Sub-Phase Strategy

```
Phase 2A: Variable Renames (Low Risk)          │ 1-2 hours  │ 16 violations
Phase 2B: Function Renames (Medium Risk)       │ 12-15 hours│ 92 violations
Phase 2C: Directory Renames (High Risk)        │ 6-8 hours  │ 4 violations
Phase 2D: Validation & Documentation           │ 2-3 hours  │ Verification
```

---

## Phase 2A: Variable Renames (Low Risk)

### Objective
Rename 16 variables (12 single-letter + 4 Hungarian notation) with zero breaking changes.

### Violations
- **variable_single_letter**: 12 violations
- **variable_hungarian_notation**: 4 violations

### Strategy
Local variable renames are safe because they don't cross file boundaries. Can be fully automated.

### Execution Steps

**Step 1: Generate Refactoring Script (30 minutes)**
```python
# refactor_phase_2a.py
import json
import ast
import re
from pathlib import Path

def rename_variable_in_file(file_path, old_name, new_name, line_number):
    """
    Rename variable in specific file at specific line.
    Uses AST to ensure we only rename the specific variable scope.
    """
    # Read file
    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Simple replacement (for local variables in small scopes)
    # More sophisticated: use rope library for AST-based refactoring
    if line_number and line_number <= len(lines):
        line = lines[line_number - 1]
        lines[line_number - 1] = line.replace(old_name, new_name)

    # Write back
    with open(file_path, 'w') as f:
        f.writelines(lines)

# Load Phase 2 goals
with open('phase_2_goals.json', 'r') as f:
    phase2 = json.load(f)

# Filter variable violations
variable_violations = []
for file_path, violations in phase2['files_to_refactor'].items():
    for v in violations:
        if v['violation_type'] in ['variable_single_letter', 'variable_hungarian_notation']:
            variable_violations.append(v)

print(f"Processing {len(variable_violations)} variable renames...")

for v in variable_violations:
    rename_variable_in_file(
        v['file_path'],
        v['current_name'],
        v['suggested_name'],
        v.get('line_number')
    )
    print(f"  ✓ {v['file_path']}:{v.get('line_number')} - {v['current_name']} → {v['suggested_name']}")
```

**Step 2: Execute Refactoring (10 minutes)**
```bash
# Backup
git add -A
git commit -m "Checkpoint before Phase 2A variable renames"

# Execute
python3 refactor_phase_2a.py

# Review changes
git diff
```

**Step 3: Test (20 minutes)**
```bash
# Run full test suite
pytest tests/ -v

# Check for import errors
python3 -m py_compile src/**/*.py
```

**Step 4: Commit (10 minutes)**
```bash
git add -A
git commit -m "Phase 2A: Rename 16 variables for naming compliance

- Renamed 12 single-letter variables to descriptive names
- Renamed 4 Hungarian notation variables to clean names
- Zero breaking changes (local scope only)
- All tests pass

Refs: phase_2_goals.json (Phase 2A violations)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Rollback Procedure
```bash
# If tests fail
git reset --hard HEAD~1
```

### Success Criteria
- [ ] All 16 variables renamed
- [ ] All tests pass
- [ ] No import errors
- [ ] Git history preserved

---

## Phase 2B: Function Renames (Medium Risk)

### Objective
Rename 92 functions that don't follow verb-noun pattern. Use **backward compatibility aliases** to avoid breaking changes.

### Violations
- **function_no_verb_noun**: 92 violations

### Strategy
1. Create new function with correct name
2. Keep old function as deprecated alias
3. Add deprecation warnings
4. Update internal calls gradually
5. Remove aliases in Phase 3+

### Example Transformation

**Before:**
```python
def metrics():
    """Get metrics."""
    return calculate_metrics()
```

**After (with backward compatibility):**
```python
def get_metrics():
    """Get metrics."""
    return calculate_metrics()

# Backward compatibility alias (deprecated)
def metrics():
    """DEPRECATED: Use get_metrics() instead."""
    import warnings
    warnings.warn(
        "metrics() is deprecated, use get_metrics() instead",
        DeprecationWarning,
        stacklevel=2
    )
    return get_metrics()
```

### Execution Steps

**Step 1: Generate Refactoring Script (2 hours)**
```python
# refactor_phase_2b.py
"""
Phase 2B: Function renames with backward compatibility.

Strategy:
1. Parse each function using AST
2. Create new function with correct name
3. Keep old function as deprecated alias
4. Update internal file calls to use new name
"""

import ast
import json
from pathlib import Path
from typing import List, Tuple

class FunctionRenamer(ast.NodeTransformer):
    """AST transformer to rename functions with aliases."""

    def __init__(self, old_name: str, new_name: str):
        self.old_name = old_name
        self.new_name = new_name
        self.found = False

    def visit_FunctionDef(self, node):
        if node.name == self.old_name:
            self.found = True
            # Create new function with new name
            new_func = ast.copy_location(
                ast.FunctionDef(
                    name=self.new_name,
                    args=node.args,
                    body=node.body,
                    decorator_list=node.decorator_list,
                    returns=node.returns,
                ),
                node
            )

            # Create deprecated alias
            alias_func = self._create_deprecated_alias(node)

            # Return both
            return [new_func, alias_func]

        return node

    def _create_deprecated_alias(self, original_node):
        """Create deprecated alias function."""
        # Build alias function that calls new function
        pass

def rename_functions(violations: List[dict]):
    """Rename functions with backward compatibility."""
    for v in violations:
        file_path = Path(v['file_path'])
        old_name = v['current_name']
        new_name = v['suggested_name']

        # Read source
        with open(file_path, 'r') as f:
            source = f.read()

        # Parse AST
        tree = ast.parse(source)

        # Transform
        renamer = FunctionRenamer(old_name, new_name)
        new_tree = renamer.visit(tree)

        if renamer.found:
            # Generate new source
            new_source = ast.unparse(new_tree)

            # Write back
            with open(file_path, 'w') as f:
                f.write(new_source)

            print(f"  ✓ {file_path}: {old_name} → {new_name} (with alias)")

# Load Phase 2 goals
with open('phase_2_goals.json', 'r') as f:
    phase2 = json.load(f)

# Filter function violations
function_violations = []
for file_path, violations in phase2['files_to_refactor'].items():
    for v in violations:
        if v['violation_type'] == 'function_no_verb_noun':
            function_violations.append(v)

print(f"Processing {len(function_violations)} function renames...")
rename_functions(function_violations)
```

**Step 2: Execute in Batches (10-12 hours)**

Break into 4 batches of ~23 functions each:

```bash
# Batch 1: Core entities (6 files, ~2 hours)
python3 refactor_phase_2b.py --batch 1
git add -A
git commit -m "Phase 2B Batch 1: Rename functions in core entities"
pytest tests/entities/ -v

# Batch 2: Adapters (10 files, ~3 hours)
python3 refactor_phase_2b.py --batch 2
git add -A
git commit -m "Phase 2B Batch 2: Rename functions in adapters"
pytest tests/adapters/ -v

# Batch 3: Use cases (8 files, ~2 hours)
python3 refactor_phase_2b.py --batch 3
git add -A
git commit -m "Phase 2B Batch 3: Rename functions in use cases"
pytest tests/ -v

# Batch 4: Orchestrators & misc (10 files, ~3 hours)
python3 refactor_phase_2b.py --batch 4
git add -A
git commit -m "Phase 2B Batch 4: Rename functions in orchestrators"
pytest tests/ -v
```

**Step 3: Update Internal Calls (2-3 hours)**

Use automated tool to update internal calls to use new names:

```python
# update_internal_calls.py
"""
Update internal calls to use new function names.
Keeps external calls using deprecated aliases.
"""

import ast
import json
from pathlib import Path

def update_calls_in_file(file_path: Path, old_name: str, new_name: str):
    """Update function calls in same file."""
    with open(file_path, 'r') as f:
        source = f.read()

    tree = ast.parse(source)

    # Find all Call nodes with old name
    # Replace with new name
    # (Implementation details...)

    # Write back
    with open(file_path, 'w') as f:
        f.write(new_source)

# Process all files
# ...
```

**Step 4: Full Test Suite (1 hour)**
```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

### Rollback Procedure
```bash
# If batch N fails
git reset --hard HEAD~N

# Or rollback entire Phase 2B
git revert <commit-range>
```

### Success Criteria
- [ ] All 92 functions renamed
- [ ] Backward compatibility aliases in place
- [ ] Internal calls updated
- [ ] All tests pass
- [ ] Deprecation warnings working

---

## Phase 2C: Directory Renames (High Risk)

### Objective
Rename 4 directories from plural to singular:
- `src/entities` → `src/entity`
- `src/interfaces` → `src/interface`
- `src/core/entities` → `src/core/entity`
- `src/core/ports` → `src/core/port`

### Violations
- **directory_plural**: 4 violations

### Impact Analysis
- `src/entities`: 40 imports
- `src/interfaces`: 21 imports
- `src/core/entities`: ~5 imports
- `src/core/ports`: ~8 imports
- **Total affected files**: ~74

### Strategy

**Two-Phase Approach:**

1. **Phase 2C-1: Add Compatibility Shims** (Safe, non-breaking)
   - Create alias modules at old locations
   - Import and re-export from new locations
   - Keep for 6+ months

2. **Phase 2C-2: Directory Rename** (Breaking, but shimmed)
   - Use `git mv` to preserve history
   - Update all imports
   - Shims catch any missed imports

### Execution Steps

**Phase 2C-1: Compatibility Shims (2 hours)**

```bash
# Step 1: Create new directories
mkdir -p src/entity
mkdir -p src/interface
mkdir -p src/core/entity
mkdir -p src/core/port

# Step 2: Copy files (don't move yet)
cp -r src/entities/* src/entity/
cp -r src/interfaces/* src/interface/
cp -r src/core/entities/* src/core/entity/
cp -r src/core/ports/* src/core/port/

# Step 3: Update imports in new directories
python3 update_imports_in_dirs.py src/entity src/interface src/core/entity src/core/port

# Step 4: Create compatibility shims in old directories
python3 create_shims.py

# Test that both old and new imports work
pytest tests/ -v
```

**create_shims.py:**
```python
"""
Create compatibility shims for directory renames.

Example shim (src/entities/__init__.py):

# DEPRECATED: This module has moved to src.entity
# This compatibility shim will be removed in v2.0

import warnings
warnings.warn(
    "src.entities is deprecated, use src.entity instead",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from new location
from src.entity import *  # noqa
```

from pathlib import Path

shims = {
    'src/entities/__init__.py': 'src.entity',
    'src/interfaces/__init__.py': 'src.interface',
    'src/core/entities/__init__.py': 'src.core.entity',
    'src/core/ports/__init__.py': 'src.core.port',
}

for shim_path, new_module in shims.items():
    path = Path(shim_path)

    # Read existing __init__.py
    if path.exists():
        with open(path, 'r') as f:
            original = f.read()

        # Backup
        path.with_suffix('.py.bak').write_text(original)

    # Write shim
    shim_code = f'''"""
DEPRECATED: This module has moved to {new_module}
This compatibility shim will be removed in v2.0
"""

import warnings
warnings.warn(
    "{path.parent.as_posix()} is deprecated, use {new_module} instead",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from new location
from {new_module} import *  # noqa
'''

    path.write_text(shim_code)
    print(f"Created shim: {shim_path} → {new_module}")
```

**Commit Phase 2C-1:**
```bash
git add -A
git commit -m "Phase 2C-1: Add compatibility shims for directory renames

- Created src/entity, src/interface, src/core/entity, src/core/port
- Added compatibility shims at old locations
- Both old and new imports work
- Deprecation warnings guide users to new locations

Non-breaking change - old imports still work.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com)"
```

**Phase 2C-2: Update All Imports (4-6 hours)**

```bash
# Step 1: Find all imports
grep -r "from src.entities" src/ tests/ scripts/ --include="*.py" > imports_to_fix.txt
grep -r "from src.interfaces" src/ tests/ scripts/ --include="*.py" >> imports_to_fix.txt
grep -r "import src.entities" src/ tests/ scripts/ --include="*.py" >> imports_to_fix.txt
grep -r "import src.interfaces" src/ tests/ scripts/ --include="*.py" >> imports_to_fix.txt

# Count
wc -l imports_to_fix.txt

# Step 2: Automated replacement
python3 update_all_imports.py

# Step 3: Manual review
git diff
```

**update_all_imports.py:**
```python
"""Update all imports to use new directory names."""

import re
from pathlib import Path

# Mapping of old → new
replacements = {
    'from src.entities': 'from src.entity',
    'from src.interfaces': 'from src.interface',
    'from src.core.entities': 'from src.core.entity',
    'from src.core.ports': 'from src.core.port',
    'import src.entities': 'import src.entity',
    'import src.interfaces': 'import src.interface',
}

def update_imports_in_file(file_path: Path):
    """Update imports in a single file."""
    with open(file_path, 'r') as f:
        content = f.read()

    original = content

    for old, new in replacements.items():
        content = content.replace(old, new)

    if content != original:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    return False

# Process all Python files
python_files = list(Path('src').rglob('*.py'))
python_files.extend(Path('tests').rglob('*.py'))
python_files.extend(Path('scripts').rglob('*.py'))

updated = 0
for file_path in python_files:
    if update_imports_in_file(file_path):
        updated += 1
        print(f"  ✓ {file_path}")

print(f"\nUpdated {updated} files")
```

**Step 4: Test Everything (1 hour)**
```bash
# Run full test suite
pytest tests/ -v --cov=src

# Check for import errors
python3 -m py_compile src/**/*.py
python3 -m py_compile tests/**/*.py

# Verify both old and new imports still work (shims)
python3 -c "from src.entities import *; print('Old import works')"
python3 -c "from src.entity import *; print('New import works')"
```

**Step 5: Commit**
```bash
git add -A
git commit -m "Phase 2C-2: Update all imports to use new directory names

Updated imports in ~74 files:
- src.entities → src.entity (40 files)
- src.interfaces → src.interface (21 files)
- src.core.entities → src.core.entity (5 files)
- src.core.ports → src.core.port (8 files)

Compatibility shims still in place - old imports work with warnings.
All tests pass.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Rollback Procedure

**If Phase 2C-1 fails:**
```bash
git reset --hard HEAD~1
```

**If Phase 2C-2 fails:**
```bash
# Revert import updates
git reset --hard HEAD~1

# Shims are still in place, so old code works
```

### Success Criteria
- [ ] New directories created with correct names
- [ ] All imports updated
- [ ] Compatibility shims in place
- [ ] Both old and new imports work
- [ ] All tests pass
- [ ] Deprecation warnings guide users

---

## Phase 2D: Validation & Documentation (2-3 hours)

### Objective
Final validation, documentation, and cleanup.

### Steps

**1. Run Full Validation (1 hour)**
```bash
# All tests
pytest tests/ -v --cov=src --cov-report=html

# Type checking (if using mypy)
mypy src/

# Linting
flake8 src/ tests/

# Import validation
python3 -m py_compile src/**/*.py
python3 -m py_compile tests/**/*.py
```

**2. Update Documentation (1 hour)**

Update affected docs:
- README.md (if it references old directory names)
- ARCHITECTURE.md
- Import examples in docstrings
- Migration guide

**3. Create Phase 2 Summary (30 minutes)**

```markdown
# Phase 2: Critical Priority - COMPLETION SUMMARY

**Date:** 2025-10-14
**Status:** ✅ COMPLETE
**Violations Resolved:** 112
**Time Invested:** ~22 hours

## Accomplishments

### Phase 2A: Variable Renames ✅
- Renamed 16 variables (12 single-letter + 4 Hungarian)
- Zero breaking changes
- All tests pass

### Phase 2B: Function Renames ✅
- Renamed 92 functions to verb-noun pattern
- Backward compatibility aliases in place
- Internal calls updated
- Deprecation warnings active

### Phase 2C: Directory Renames ✅
- Renamed 4 directories to singular form
- Updated ~74 import statements
- Compatibility shims in place
- Both old and new imports work

### Phase 2D: Validation ✅
- All tests pass (100% coverage maintained)
- No import errors
- Documentation updated
- Migration guide created

## Breaking Changes

**None** - All changes are backward compatible via:
- Function aliases (will be removed in Phase 5+)
- Directory shims (will be removed in v2.0)

## Next Steps

Ready for Phase 3: High Priority violations (241 violations, ~76 hours)
```

**4. Commit Phase 2 Summary (10 minutes)**
```bash
git add -A
git commit -m "Phase 2: Critical Priority complete - 112 violations resolved

Summary:
- Phase 2A: 16 variable renames ✅
- Phase 2B: 92 function renames (with aliases) ✅
- Phase 2C: 4 directory renames (with shims) ✅
- Phase 2D: Validation & documentation ✅

Breaking changes: NONE (backward compatibility maintained)
All tests pass.
Ready for Phase 3.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com)"
```

---

## Tooling Requirements

### Python Packages
```bash
pip install rope  # Automated refactoring
pip install ast-grep  # AST-based search/replace
pip install pytest pytest-cov  # Testing
pip install mypy flake8  # Validation
```

### Scripts to Create
1. `refactor_phase_2a.py` - Variable renames
2. `refactor_phase_2b.py` - Function renames with aliases
3. `create_shims.py` - Compatibility shims for directories
4. `update_all_imports.py` - Update import statements
5. `validate_phase_2.py` - Final validation

---

## Testing Strategy

### Test After Each Sub-Phase
- **Phase 2A**: `pytest tests/ -v`
- **Phase 2B Batch N**: `pytest tests/<affected-area>/ -v`
- **Phase 2C-1**: `pytest tests/ -v` + manual import tests
- **Phase 2C-2**: Full test suite + coverage
- **Phase 2D**: All validation tools

### Test Coverage Requirements
- Maintain ≥85% coverage (current baseline)
- All refactored files must have tests
- No decrease in coverage

### Smoke Tests
After each sub-phase, run smoke tests:
```bash
python3 -c "from src.main import main; print('Import OK')"
python3 src/main.py --help
python3 autonomous_dev_tool.py --help
```

---

## Rollback Procedures

### Per Sub-Phase Rollback
Each sub-phase is a separate commit, allowing granular rollback:

```bash
# Rollback Phase 2A only
git revert <2A-commit-hash>

# Rollback Phase 2B Batch 2
git revert <batch-2-commit-hash>

# Rollback entire Phase 2
git revert <first-commit>..<last-commit>
```

### Full Phase 2 Rollback
If Phase 2 must be completely abandoned:

```bash
# Create rollback branch
git checkout -b rollback-phase-2

# Revert all Phase 2 commits
git revert --no-commit <first-phase-2-commit>..HEAD
git commit -m "Rollback Phase 2: Critical priority refactoring"

# Merge back to main
git checkout main
git merge rollback-phase-2
```

### Emergency Rollback
If production is broken:

```bash
# Hard reset (lose uncommitted changes)
git reset --hard <before-phase-2-commit>

# Force push (if already pushed)
git push --force origin <branch-name>
```

---

## Timeline

### Optimistic (22 hours)
- Phase 2A: 1 hour
- Phase 2B: 12 hours
- Phase 2C: 6 hours
- Phase 2D: 3 hours

### Realistic (28 hours)
- Phase 2A: 2 hours (including script creation)
- Phase 2B: 15 hours (including testing between batches)
- Phase 2C: 8 hours (including manual review)
- Phase 2D: 3 hours

### Pessimistic (35 hours)
- Phase 2A: 3 hours (issues with variable scopes)
- Phase 2B: 20 hours (complex function dependencies)
- Phase 2C: 10 hours (import issues, test failures)
- Phase 2D: 2 hours

**Recommended:** Plan for 3-4 days (8 hours/day) = 24-32 hours

---

## Risk Mitigation

### Risk 1: Import Errors After Directory Rename
**Mitigation:**
- Compatibility shims at old locations
- Both old and new imports work
- Gradual migration over 6+ months

**Fallback:**
- Keep shims indefinitely
- Never remove old directories

### Risk 2: Tests Fail After Function Rename
**Mitigation:**
- Execute in batches (4 batches × ~23 functions)
- Test after each batch
- Rollback only failed batch

**Fallback:**
- Keep backward compatibility aliases forever
- Update tests to use new names gradually

### Risk 3: AST Parsing Fails
**Mitigation:**
- Manual fallback for complex cases
- Use rope library (more robust)
- Test on sample files first

**Fallback:**
- Manual refactoring for problem files
- Document exceptions in Phase 2 summary

### Risk 4: Merge Conflicts
**Mitigation:**
- Communicate Phase 2 execution window
- Lock branch during execution
- Coordinate with team

**Fallback:**
- Pause Phase 2 mid-execution
- Merge main into branch
- Resume after conflicts resolved

---

## Success Criteria

### Phase 2 Complete When:
- [ ] All 112 violations resolved
- [ ] All tests pass (no regressions)
- [ ] Test coverage maintained ≥85%
- [ ] No import errors
- [ ] Backward compatibility maintained
- [ ] Documentation updated
- [ ] Phase 2 summary created
- [ ] All commits pushed

### Quality Gates:
- [ ] `pytest tests/ -v` → 100% pass
- [ ] `python3 -m py_compile src/**/*.py` → No errors
- [ ] `pytest --cov=src --cov-report=term` → ≥85% coverage
- [ ] Manual import tests → Both old and new work
- [ ] Deprecation warnings → Visible for old functions

---

## Execution Checklist

### Pre-Execution
- [ ] Read this plan thoroughly
- [ ] Install required tools (`rope`, `pytest`, etc.)
- [ ] Create feature branch: `refactor/naming-ruleset-phase-2`
- [ ] Backup database/configs (if applicable)
- [ ] Notify team of execution window

### Phase 2A Execution
- [ ] Create `refactor_phase_2a.py`
- [ ] Test on 1-2 sample files
- [ ] Execute full Phase 2A
- [ ] Run tests: `pytest tests/ -v`
- [ ] Commit: "Phase 2A complete"

### Phase 2B Execution
- [ ] Create `refactor_phase_2b.py`
- [ ] Test on 1-2 sample files
- [ ] Execute Batch 1 + test
- [ ] Execute Batch 2 + test
- [ ] Execute Batch 3 + test
- [ ] Execute Batch 4 + test
- [ ] Update internal calls
- [ ] Run full test suite
- [ ] Commit: "Phase 2B complete"

### Phase 2C Execution
- [ ] Create `create_shims.py`
- [ ] Execute Phase 2C-1 (shims)
- [ ] Test: both old and new imports work
- [ ] Commit: "Phase 2C-1 complete"
- [ ] Create `update_all_imports.py`
- [ ] Execute Phase 2C-2 (update imports)
- [ ] Manual review: `git diff`
- [ ] Test: full test suite
- [ ] Commit: "Phase 2C-2 complete"

### Phase 2D Execution
- [ ] Run full validation suite
- [ ] Update documentation
- [ ] Create Phase 2 summary
- [ ] Commit: "Phase 2 complete"
- [ ] Create PR (if using PRs)

---

## Autonomous Execution Option

### Can Phase 2 Be Fully Automated?

**Yes, with oversight.** Here's the recommended approach:

**Option A: Semi-Autonomous (Recommended)**
- Human creates refactoring scripts (2 hours)
- Autonomous orchestrator executes each sub-phase
- Human reviews results after each sub-phase
- Human approves proceeding to next sub-phase

**Option B: Fully Autonomous (Risky)**
- Provide this plan to autonomous orchestrator
- Orchestrator creates all scripts and executes
- Human reviews only at end
- Higher risk, but faster

**Recommended:** Start with Option A for Phase 2, use lessons learned for Phase 3+.

### Autonomous Execution Command

```bash
python3 autonomous_dev_tool.py run \
  --target-goal naming_refactoring_phase_2 \
  --instructions-file docs/PHASE_2_EXECUTION_PLAN.md \
  --iterations 4 \
  --mode thorough \
  --model sonnet4.5 \
  --collect-metrics
```

---

## Critique

### What Could Go Wrong?

1. **AST parsing fails for complex Python constructs**
   - Mitigation: Manual fallback
   - Impact: 10-20% of functions need manual refactoring

2. **Compatibility shims don't work for all import styles**
   - Example: `from src.entities.agent import Agent` vs `import src.entities.agent`
   - Mitigation: Test multiple import styles
   - Impact: May need additional shims

3. **Tests fail after function renames**
   - Some tests may use reflection or string-based lookups
   - Mitigation: Search for string literals with old names
   - Impact: 5-10 test fixes needed

4. **Performance regression from deprecation warnings**
   - Mitigation: Warnings only fire once per location
   - Impact: Negligible (<1ms overhead)

5. **Merge conflicts during Phase 2 execution**
   - Mitigation: Execute during low-activity window
   - Impact: 1-2 hours to resolve conflicts

### Assumptions

1. **Test suite is comprehensive** - If not, refactoring may introduce bugs that aren't caught
2. **No dynamic imports** - If code uses `importlib` or `__import__`, shims may not work
3. **Clean git state** - No uncommitted changes before starting
4. **Single branch** - No parallel work on affected files
5. **Python 3.8+** - AST manipulation requires modern Python

### Trade-offs

| Approach | Speed | Safety | Maintenance |
|----------|-------|--------|-------------|
| **Chosen: Compatibility Shims** | Medium | High | Medium (remove shims later) |
| **Alternative: Big Bang** | Fast | Low | Low (clean, but risky) |
| **Alternative: Gradual** | Slow | Highest | High (long transition) |

**Chosen approach balances all three concerns.**

---

**END OF PHASE 2 EXECUTION PLAN**

*Last Updated: October 14, 2025*
*Version: 1.0*
*Status: Ready for Execution*
