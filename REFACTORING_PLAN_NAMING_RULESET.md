# Autonomous Orchestrator: Comprehensive Naming Ruleset Refactoring Plan

**Document Version:** 1.0
**Created:** 2025-10-14
**Based On:** `Naming Ruleset.md` (Clean Code by Robert C. Martin)
**Execution Method:** Autonomous Orchestrator with staged goals

---

## Executive Summary

This plan outlines a **systematic, multi-phase refactoring** of the entire codebase to align with Clean Code naming principles. The autonomous orchestrator will execute this refactoring in **manageable, testable increments** to maintain code stability while improving readability, maintainability, and compliance with industry best practices.

**Estimated Duration:** 15-25 autonomous iterations
**Risk Level:** Medium (mitigated by phased approach + comprehensive testing)
**Success Metrics:**
- 100% compliance with Naming Ruleset
- All tests passing after each phase
- Zero functional regressions
- Improved code readability scores

---

## Phase 1: Discovery and Analysis (Iterations 1-3)

**Goal:** Identify all naming violations across the codebase

### Tasks

#### 1.1 Automated Naming Audit
**Instruction:**
```
Create a Python script `naming_audit.py` that scans the entire codebase and generates a comprehensive report of naming violations:

1. **Directory Naming Violations:**
   - Check for plural directory names (should be singular)
   - Identify inconsistent casing (e.g., mixedCase vs snake_case)
   - Flag deep nesting (>4 levels)
   - List ambiguous names (e.g., "stuff", "misc", "things")

2. **File Naming Violations:**
   - Check Python files for non-snake_case names
   - Identify files with cryptic names (e.g., single letters, abbreviations)
   - Flag inconsistent naming patterns

3. **Function/Method Naming Violations:**
   - Functions without verb-noun pairs
   - Functions with flag arguments (boolean parameters)
   - Functions with misleading names (side effects not described)
   - Functions with short/cryptic names in large scopes

4. **Variable Naming Violations:**
   - Variables with single-letter names in large scopes (>10 lines)
   - Variables with Hungarian notation or type prefixes
   - Variables with unclear purpose
   - Variables with inconsistent naming (fetch vs get vs retrieve)

Output: JSON report with:
- violation_type
- file_path
- line_number (for code violations)
- current_name
- suggested_name
- severity (critical, high, medium, low)
- ruleset_reference (which rule from Naming Ruleset.md)
```

**Estimated Time:** 45-60 minutes
**Deliverables:**
- `naming_audit.py` script
- `naming_violations_report.json`
- `naming_violations_summary.md` (human-readable)

#### 1.2 Prioritization Matrix
**Instruction:**
```
Analyze the violations report and create a prioritization matrix:

1. **Critical Priority** (Phase 2):
   - Public API function names (high visibility)
   - Core entity/domain model names
   - Architectural layer misalignments

2. **High Priority** (Phase 3):
   - Service/use case function names
   - Adapter method names
   - Frequently used utility functions

3. **Medium Priority** (Phase 4):
   - Internal helper functions
   - Private methods
   - Test function names

4. **Low Priority** (Phase 5):
   - Variable names in small scopes
   - Local helper variables
   - Temporary variables

Output:
- `refactoring_priority_matrix.md`
- `phase_2_goals.json` (specific files and functions to refactor)
- `phase_3_goals.json`
- `phase_4_goals.json`
- `phase_5_goals.json`
```

**Estimated Time:** 30 minutes
**Deliverables:** Priority matrix + phase-specific goal files

#### 1.3 Impact Analysis
**Instruction:**
```
For each high/critical priority violation, perform impact analysis:

1. **Dependency Graph:**
   - Identify all files that import/use the violated name
   - Map call chains and dependencies
   - Flag potential breaking changes

2. **Test Coverage:**
   - Check if violated names have test coverage
   - Identify tests that will need updates
   - Flag missing tests

3. **Documentation References:**
   - Search README, docs for references
   - Check docstrings for examples using old names
   - List all documentation that needs updates

Output:
- `impact_analysis_report.json`
- `breaking_changes_forecast.md`
- `test_update_requirements.md`
```

**Estimated Time:** 45 minutes
**Deliverables:** Comprehensive impact analysis

---

## Phase 2: Core Domain Refactoring (Iterations 4-8)

**Goal:** Refactor critical priority violations in core entities and domain models

### Approach
1. One entity/module per iteration
2. Refactor + update tests + update docs in single atomic commit
3. Run full test suite after each change
4. Rollback if any tests fail

### Execution Pattern (per iteration)

**Instruction Template:**
```
Refactor [MODULE_NAME] according to Naming Ruleset:

1. **Analysis:**
   - Review naming_violations_report.json for [MODULE_NAME]
   - List all violations (functions, variables, classes)
   - Plan rename mappings (old_name → new_name)

2. **Refactoring:**
   - Rename functions to verb-noun pairs
   - Remove flag arguments (split into separate functions)
   - Describe side effects in function names
   - Update all references across codebase
   - Maintain backward compatibility where possible

3. **Testing:**
   - Update unit tests with new names
   - Update integration tests
   - Run full test suite: pytest
   - Verify zero regressions

4. **Documentation:**
   - Update docstrings
   - Update README examples
   - Update API documentation

5. **Validation:**
   - Verify all tests pass
   - Check import statements resolve
   - Confirm no circular dependencies introduced

Output:
- Refactored code files
- Updated tests
- Updated documentation
- Commit message following template
```

### Modules to Refactor (Priority Order)

1. **src/entities/** (Core domain models)
   - `agent.py`
   - `agent_team.py`
   - `execution.py`
   - `metrics.py`

2. **src/claude_orchestrator/entities/** (Orchestrator entities)
   - `worker.py`
   - `generated_task.py`

3. **src/interfaces/** (Contracts)
   - All interface files

4. **src/use_cases/** (Business logic)
   - All use case files

5. **src/adapters/** (External integrations)
   - All adapter files

**Estimated Time per Module:** 45-90 minutes
**Total Phase 2 Time:** 5 iterations × 60 min avg = 300 minutes (5 hours)

---

## Phase 3: Service Layer Refactoring (Iterations 9-13)

**Goal:** Refactor high priority violations in service/use case layers

### Focus Areas

1. **Use Case Functions:**
   - Ensure all use case methods use verb-noun pairs
   - Example: `get_user()` → `fetch_user_by_id()` (more specific)
   - Example: `process()` → `process_payment_transaction()` (reveals intent)

2. **Service Methods:**
   - Remove boolean flags: `render(true)` → `render_for_web()`
   - Describe side effects: `check_password()` → `validate_password_and_initialize_session()`
   - Use keywords: `write(name)` → `write_field_to_database(name)`

3. **Adapter Methods:**
   - Standardize terminology: Choose `fetch` OR `get` OR `retrieve` (not mix)
   - Use consistent patterns across all adapters
   - Example: All database adapters use `fetch_*`, all API adapters use `call_*`

**Execution:**
- Follow same pattern as Phase 2
- One service/use case per iteration
- Atomic commits with full test coverage

**Estimated Time:** 5 iterations × 60 min = 300 minutes (5 hours)

---

## Phase 4: Internal Implementation Refactoring (Iterations 14-18)

**Goal:** Refactor medium priority violations in internal helpers and utilities

### Focus Areas

1. **Helper Functions:**
   - Rename cryptic helpers: `_h()` → `_validate_input_parameters()`
   - Add descriptive names to internal utilities
   - Clarify purpose of private methods

2. **Variable Names:**
   - Replace single-letter variables in large scopes (>10 lines)
   - Remove Hungarian notation: `strName` → `name`
   - Remove scope prefixes: `m_count` → `count` (rely on IDE)

3. **Test Function Names:**
   - Ensure test names describe what they test
   - Example: `test_1()` → `test_fetch_user_returns_user_when_id_exists()`
   - Follow pattern: `test_[function]_[scenario]_[expected_outcome]()`

**Execution:**
- Group related helpers/utilities per iteration
- Lower risk (internal changes, less breaking potential)
- Focus on readability improvements

**Estimated Time:** 5 iterations × 45 min = 225 minutes (3.75 hours)

---

## Phase 5: Directory Structure Refactoring (Iterations 19-22)

**Goal:** Refactor directory/file naming violations

### Tasks

#### 5.1 Directory Naming Cleanup
**Instruction:**
```
Refactor directory structure to align with Naming Ruleset:

1. **Convert Plural to Singular:**
   - Identify all plural directories
   - Plan rename: `controllers/` → `controller/`
   - Update all import statements
   - Update Python package paths

2. **Flatten Deep Nesting:**
   - Identify directories with >4 levels
   - Restructure to reduce nesting
   - Maintain logical grouping

3. **Remove Ambiguous Names:**
   - Rename `misc/` → specific purpose
   - Rename `utils/` → grouped by function (e.g., `string_util/`, `date_util/`)
   - Ensure each directory has clear single responsibility

Output:
- Directory restructuring plan
- Import statement updates
- Git mv commands with history preservation
```

**Estimated Time:** 60-90 minutes per iteration
**Risk:** Medium (affects imports across codebase)

#### 5.2 File Naming Cleanup
**Instruction:**
```
Refactor file names to follow snake_case and descriptive naming:

1. **Snake Case Conversion:**
   - Convert any camelCase files to snake_case
   - Update imports

2. **Descriptive Names:**
   - Rename cryptic files: `proc.py` → `payment_processor.py`
   - Ensure file name matches primary class/function

3. **Consistency:**
   - Standardize suffixes: `*_adapter.py`, `*_service.py`, `*_repository.py`

Output:
- File renaming script
- Updated imports
- Git history preservation
```

**Estimated Time:** 45-60 minutes per iteration

---

## Phase 6: Validation and Documentation (Iterations 23-25)

**Goal:** Verify refactoring completeness and update all documentation

### Tasks

#### 6.1 Comprehensive Testing
**Instruction:**
```
Run comprehensive validation:

1. **Test Suite:**
   - pytest (all tests)
   - Coverage analysis (ensure no drop in coverage)
   - Integration tests
   - End-to-end tests

2. **Static Analysis:**
   - pylint (check for new issues)
   - mypy (type checking)
   - flake8 (style compliance)

3. **Manual Smoke Tests:**
   - CLI commands work
   - API endpoints functional
   - Orchestrator can run iterations

Output:
- Test results report
- Coverage delta (before/after)
- List of any remaining issues
```

**Estimated Time:** 60 minutes

#### 6.2 Documentation Update
**Instruction:**
```
Update all documentation to reflect new naming:

1. **README Files:**
   - Update all examples with new function names
   - Update installation/usage instructions

2. **API Documentation:**
   - Regenerate API docs (Sphinx/etc)
   - Update docstrings examples

3. **Architecture Docs:**
   - Update diagrams with new naming
   - Update architectural decision records (ADRs)

4. **CHANGELOG:**
   - Document all naming changes
   - Provide migration guide for users

Output:
- Updated documentation
- NAMING_REFACTORING_CHANGELOG.md
- Migration guide for developers
```

**Estimated Time:** 90 minutes

#### 6.3 Final Audit
**Instruction:**
```
Run naming_audit.py again and verify:

1. **Zero Critical/High Violations:**
   - All critical issues resolved
   - All high priority issues resolved

2. **Acceptable Medium/Low Violations:**
   - Document any intentional exceptions
   - Create tickets for remaining low-priority items

3. **Compliance Report:**
   - Generate final compliance report
   - Compare before/after metrics

Output:
- Final naming_violations_report.json
- Compliance improvement report
- List of intentional exceptions with justifications
```

**Estimated Time:** 30 minutes

---

## Execution Strategy

### Autonomous Orchestrator Configuration

**priorities.yaml Entry:**
```yaml
- id: naming_refactoring_phase_1
  title: "Naming Ruleset Refactoring - Phase 1: Discovery"
  description: "Automated audit and impact analysis of naming violations"
  priority: P1
  status: pending
  estimated_hours: 2.5
  dependencies: []
  acceptance_criteria:
    - naming_audit.py script created
    - violations_report.json generated
    - prioritization_matrix.md created
    - impact_analysis_report.json completed

- id: naming_refactoring_phase_2
  title: "Naming Ruleset Refactoring - Phase 2: Core Domain"
  description: "Refactor entities and core domain models"
  priority: P1
  status: pending
  estimated_hours: 5.0
  dependencies: [naming_refactoring_phase_1]
  acceptance_criteria:
    - All entity files refactored
    - All tests passing
    - Zero regressions
    - Documentation updated

# ... (continue for phases 3-6)
```

### CLI Execution

```bash
# Phase 1: Discovery
python autonomous_dev_tool.py run \
  --target-goal naming_refactoring_phase_1 \
  --mode thorough \
  --iterations 3

# Phase 2: Core Domain
python autonomous_dev_tool.py run \
  --target-goal naming_refactoring_phase_2 \
  --mode full \
  --iterations 5

# Continue for each phase...
```

### Constraints and Limitations

1. **Permissions:** ✅ RESOLVED
   - Previously root-owned directories have been fixed with `chown`
   - Passwordless sudo configured for ui-cli_jake
   - All directories and files now accessible for refactoring

2. **Backward Compatibility:**
   - Maintain compatibility during refactoring using deprecation warnings where possible
   - Provide compatibility shims for public APIs
   - Version bump to indicate breaking changes

3. **Test Requirements:**
   - All tests must pass after each iteration
   - No commits unless full test suite passes
   - Maintain or improve test coverage

### Safety Mechanisms

1. **Atomic Commits:** Each refactoring creates single atomic commit
2. **Test Gates:** No commit unless all tests pass
3. **Rollback Plan:** Git revert if issues discovered
4. **Branch Strategy:** Work on `refactor/naming-ruleset` branch
5. **Review Points:** PR review after each phase completion

---

## Risk Mitigation

### High-Risk Items

1. **Public API Changes:**
   - Maintain backward compatibility with deprecation warnings
   - Provide compatibility shims where necessary
   - Version bump to indicate breaking changes

2. **Import Chain Breaks:**
   - Use automated refactoring tools (rope, pyre)
   - Verify all imports resolve before commit
   - Test in isolated environment first

3. **Test Breakage:**
   - Update tests in same commit as code changes
   - Ensure test coverage maintained
   - Add tests if coverage drops

### Rollback Procedure

```bash
# If phase fails:
git log --oneline -10  # Identify last good commit
git revert <commit-sha>  # Revert problematic commit
git push origin refactor/naming-ruleset --force  # Update branch

# Analyze failure:
- Review test output
- Check for circular dependencies
- Verify import paths

# Fix and retry:
- Apply fix
- Re-run autonomous iteration
```

---

## Success Metrics

### Quantitative Metrics

| Metric | Before | Target | Measure |
|--------|--------|--------|---------|
| Critical Violations | TBD | 0 | naming_audit.py |
| High Violations | TBD | 0 | naming_audit.py |
| Medium Violations | TBD | <10 | naming_audit.py |
| Test Coverage | TBD | ≥ Current | pytest --cov |
| Code Readability | TBD | +20% | radon |

### Qualitative Metrics

- ✅ Function names clearly reveal intent without reading code
- ✅ No boolean flag arguments in public APIs
- ✅ Consistent terminology across entire codebase
- ✅ Directory structure follows Clean Architecture
- ✅ All side effects described in function names

---

## Timeline Estimate

| Phase | Iterations | Est. Hours | Cumulative |
|-------|-----------|-----------|------------|
| Phase 1 | 1-3 | 2.5h | 2.5h |
| Phase 2 | 4-8 | 5.0h | 7.5h |
| Phase 3 | 9-13 | 5.0h | 12.5h |
| Phase 4 | 14-18 | 3.75h | 16.25h |
| Phase 5 | 19-22 | 4.0h | 20.25h |
| Phase 6 | 23-25 | 3.0h | 23.25h |

**Total Estimated Time:** 23-25 hours (autonomous orchestrator runtime)
**Wall Clock Time:** 3-4 days (with review/validation breaks)

---

## Appendix A: Example Refactorings

### Example 1: Function Naming

**Before:**
```python
def check(user, pwd):
    if validate_credentials(user, pwd):
        init_session(user)
        return True
    return False
```

**After:**
```python
def validate_credentials_and_initialize_session(username: str, password: str) -> bool:
    """Validate user credentials and initialize session if valid.

    Side effect: Initializes user session in database.
    """
    if _validate_password_hash(username, password):
        _initialize_user_session(username)
        return True
    return False
```

### Example 2: Boolean Flag Removal

**Before:**
```python
def render(is_web: bool):
    if is_web:
        # web rendering
    else:
        # console rendering
```

**After:**
```python
def render_for_web():
    # web rendering

def render_for_console():
    # console rendering
```

### Example 3: Directory Structure

**Before:**
```
src/
  controllers/
    userController.py
    postController.py
  services/
    userService.py
  utils/
    misc/
      stuff.py
```

**After:**
```
src/
  controller/
    user_controller.py
    post_controller.py
  service/
    user_service.py
  string_util/
    string_formatter.py
```

---

## Appendix B: Naming Audit Script Pseudocode

```python
#!/usr/bin/env python3
"""naming_audit.py - Automated naming compliance checker"""

import ast
import os
from pathlib import Path
from typing import List, Dict

class NamingViolation:
    """Represents a single naming violation"""
    def __init__(self, type, path, line, name, suggestion, severity, rule):
        self.type = type
        self.path = path
        self.line = line
        self.current_name = name
        self.suggested_name = suggestion
        self.severity = severity
        self.ruleset_reference = rule

class NamingAuditor:
    """Scans codebase for naming violations"""

    def audit_directories(self, root: Path) -> List[NamingViolation]:
        """Check directory naming violations"""
        violations = []
        for dirpath in root.rglob("*"):
            if dirpath.is_dir():
                # Check for plural names
                if dirpath.name.endswith('s') and dirpath.name not in ['tests']:
                    violations.append(NamingViolation(
                        type="directory_plural",
                        path=str(dirpath),
                        line=None,
                        name=dirpath.name,
                        suggestion=dirpath.name[:-1],  # Remove 's'
                        severity="high",
                        rule="Prefer Singular Names for Directories"
                    ))
        return violations

    def audit_functions(self, file_path: Path) -> List[NamingViolation]:
        """Check function naming violations"""
        violations = []
        with open(file_path) as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check for verb-noun pattern
                if not self._has_verb_noun_pattern(node.name):
                    violations.append(NamingViolation(
                        type="function_no_verb",
                        path=str(file_path),
                        line=node.lineno,
                        name=node.name,
                        suggestion=self._suggest_verb_noun(node.name),
                        severity="medium",
                        rule="Form Verb-Noun Pairs"
                    ))

                # Check for boolean flags
                if self._has_boolean_flag(node):
                    violations.append(NamingViolation(
                        type="function_flag_arg",
                        path=str(file_path),
                        line=node.lineno,
                        name=node.name,
                        suggestion=f"Split into separate functions",
                        severity="high",
                        rule="Avoid Flag Arguments"
                    ))

        return violations

    def _has_verb_noun_pattern(self, name: str) -> bool:
        """Check if function name follows verb-noun pattern"""
        verbs = ['get', 'set', 'create', 'delete', 'update', 'fetch',
                 'save', 'load', 'process', 'validate', 'calculate',
                 'generate', 'parse', 'render', 'send', 'receive']
        return any(name.startswith(verb) for verb in verbs)

    # ... more methods
```

---

**End of Refactoring Plan**

This plan can be executed by the autonomous orchestrator by creating goals in `priorities.yaml` and running targeted iterations for each phase.
