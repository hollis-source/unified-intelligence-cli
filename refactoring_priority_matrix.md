# Refactoring Priority Matrix

**Generated from:** naming_violations_report.json
**Total Violations:** 938

## Overview

This matrix categorizes naming violations by priority for systematic refactoring.
Each phase should be completed before moving to the next.

| Phase | Priority | Violations | Est. Hours | Description |
|-------|----------|------------|------------|-------------|
| 2 | Critical Priority | 19 | 5.0h | Public API functions, core entity names, architectural layer misalignments |
| 3 | High Priority | 172 | 62.5h | Service/use case function names, adapter method names, frequently used utilities |
| 4 | Medium Priority | 535 | 67.1h | Internal helper functions, private methods, test function names |
| 5 | Low Priority | 212 | 23.4h | Variable names in small scopes, local helper variables, temporary variables |

## Phase 2: Critical Priority

**Estimated Time:** 5.0 hours
**Total Violations:** 19

Public API functions, core entity names, architectural layer misalignments

### Breakdown by Type

- **Directory Plural:** 4 violations
- **Function No Verb Noun:** 12 violations
- **Variable Single Letter:** 3 violations

### Key Files to Refactor

- `src/entities/graph/graph.py` (6 violations)
- `src/entities/category_theory/morphism.py` (5 violations)
- `src/entities/category_theory/workflow_morphism.py` (4 violations)
- `src/entities` (1 violations)
- `src/interfaces` (1 violations)
- `src/core/entities` (1 violations)
- `src/core/ports` (1 violations)

## Phase 3: High Priority

**Estimated Time:** 62.5 hours
**Total Violations:** 172

Service/use case function names, adapter method names, frequently used utilities

### Breakdown by Type

- **Directory Plural:** 67 violations
- **Directory Ambiguous:** 1 violations
- **Directory Deep Nesting:** 2 violations
- **Function Boolean Flag:** 6 violations
- **Variable Single Letter:** 81 violations
- **Function No Verb Noun:** 14 violations
- **File Cryptic Name:** 1 violations

### Key Files to Refactor

- `src/claude_orchestrator/adapters/auggie_pr_reviewer.py` (11 violations)
- `src/routing/team_router.py` (9 violations)
- `src/use_cases/task_planner.py` (7 violations)
- `src/claude_orchestrator/entities/validation_result.py` (7 violations)
- `src/routing/hierarchical_router.py` (6 violations)
- `src/adapters/agent/tools/file_reader.py` (6 violations)
- `src/routing/orchestrator_router.py` (5 violations)
- `src/adapters/agent/tools/file_writer.py` (5 violations)
- `tests/test_llm_cache.py` (4 violations)
- `src/adapters/orchestration/hybrid_orchestrator.py` (4 violations)
- *... and 91 more files*

## Phase 4: Medium Priority

**Estimated Time:** 67.1 hours
**Total Violations:** 535

Internal helper functions, private methods, test function names

### Breakdown by Type

- **Variable Single Letter:** 322 violations
- **Function No Verb Noun:** 200 violations
- **Variable Hungarian Notation:** 13 violations

### Key Files to Refactor

- `tests/entities/category_theory/test_morphism.py` (43 violations)
- `tests/dsl/types/test_type_checker.py` (32 violations)
- `tests/dsl/types/test_type_inference_visitor.py` (26 violations)
- `tests/monitoring/adapters/test_hf_inference_waker.py` (19 violations)
- `tests/entities/category_theory/test_workflow_morphism.py` (19 violations)
- `tests/monitoring/adapters/test_hf_inference_health_adapter.py` (15 violations)
- `src/dsl/adapters/parser.py` (15 violations)
- `tests/dsl/entities/test_monad.py` (14 violations)
- `tests/user_simulation/user_agent.py` (13 violations)
- `tests/integration/test_cli_end_to_end.py` (12 violations)
- *... and 102 more files*

## Phase 5: Low Priority

**Estimated Time:** 23.4 hours
**Total Violations:** 212

Variable names in small scopes, local helper variables, temporary variables

### Breakdown by Type

- **Directory Deep Nesting:** 3 violations
- **Variable Single Letter:** 203 violations
- **File Not Snake Case:** 3 violations
- **Variable Hungarian Notation:** 3 violations

### Key Files to Refactor

- `scripts/syd2_agent.py` (25 violations)
- `impact_analyzer.py` (17 violations)
- `simple_impact_analyzer.py` (11 violations)
- `scripts/evaluate_baseline.py` (11 violations)
- `naming_audit.py` (9 violations)
- `scripts/parallel_data_collection.py` (9 violations)
- `scripts/implement_phase2_recommendations.py` (7 violations)
- `tmp/mock_provider_container.py` (6 violations)
- `.claude/hooks/autocommit_post.py` (6 violations)
- `scripts/grok_session.py` (5 violations)
- *... and 57 more files*

