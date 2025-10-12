# Clean Architecture Governance Plan

## Objective
Establish a comprehensive Clean Architecture ruleset derived from the full book and enforce it across development via docs, agent guidance, and automated checks.

## Strategy
1. Source of truth: Generate `docs/clean-architecture-rules.md` using Auggie from the full PDF on the doc server; store in repo.
2. Human guidance: Update `CLAUDE.md` to align with the generated rules; reference the rules doc as canonical.
3. Automated enforcement: Use a lightweight linter (governance/clean_architecture_linter.py) + Git hooks + CI to prevent regressions.

## Auggie Workflow
- Create an `.auggie_task_rules_extraction.txt` describing: input (PDF URL/path), goal (produce structured, testable rules), and output path `docs/clean-architecture-rules.md`.
- Run Auggie with that task file. Review and iterate once; then merge.

## Enforcement
- Local: `.githooks/pre-commit` runs the linter (function length rule initially). Configure with `git config core.hooksPath .githooks`.
- CI: Add a step to execute `python -m governance.clean_architecture_linter --files $(git ls-files '*.py')`.
- Extend linter rules incrementally (docstrings, explicit exceptions, adapter boundaries) with tests first.

## Maintenance
- Re-run Auggie when the rules evolve; track changes in changelog.
- Keep functions < 20 lines and follow SOLID across governance code.

