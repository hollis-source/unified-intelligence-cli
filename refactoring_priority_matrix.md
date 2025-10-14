# Refactoring Priority Matrix

**Generated from:** naming_violations_report.json
**Total Violations:** 1440

## Overview

This matrix categorizes naming violations by priority for systematic refactoring.
Each phase should be completed before moving to the next.

| Phase | Priority | Violations | Est. Hours | Description |
|-------|----------|------------|------------|-------------|
| 2 | Critical Priority | 112 | 22.2h | Public API functions, core entity names, architectural layer misalignments |
| 3 | High Priority | 241 | 76.0h | Service/use case function names, adapter method names, frequently used utilities |
| 4 | Medium Priority | 886 | 133.7h | Internal helper functions, private methods, test function names |
| 5 | Low Priority | 201 | 22.9h | Variable names in small scopes, local helper variables, temporary variables |

## Phase 2: Critical Priority

**Estimated Time:** 22.2 hours
**Total Violations:** 112

Public API functions, core entity names, architectural layer misalignments

### Breakdown by Type

- **Directory Plural:** 4 violations
- **Function No Verb Noun:** 92 violations
- **Variable Single Letter:** 12 violations
- **Variable Hungarian Notation:** 4 violations

### Key Files to Refactor

- `src/entities/agent_team.py` (15 violations)
- `src/entities/metrics.py` (14 violations)
- `src/entities/category_theory/workflow_morphism.py` (11 violations)
- `src/entities/task_model/task_model.py` (11 violations)
- `src/entities/graph/graph.py` (11 violations)
- `src/entities/lifecycle/lifecycle.py` (9 violations)
- `src/entities/category_theory/morphism.py` (8 violations)
- `src/entities/executor/executor.py` (8 violations)
- `src/entities/htn/htn_node.py` (5 violations)
- `src/claude_orchestrator/interfaces/worker_pool.py` (5 violations)
- *... and 13 more files*

## Phase 3: High Priority

**Estimated Time:** 76.0 hours
**Total Violations:** 241

Service/use case function names, adapter method names, frequently used utilities

### Breakdown by Type

- **Directory Plural:** 67 violations
- **Directory Ambiguous:** 1 violations
- **Directory Deep Nesting:** 2 violations
- **Function Boolean Flag:** 6 violations
- **Function No Verb Noun:** 80 violations
- **Variable Hungarian Notation:** 3 violations
- **Variable Single Letter:** 81 violations
- **File Cryptic Name:** 1 violations

### Key Files to Refactor

- `src/claude_orchestrator/adapters/auggie_pr_reviewer.py` (12 violations)
- `src/routing/team_router.py` (11 violations)
- `src/claude_orchestrator/entities/validation_result.py` (9 violations)
- `src/routing/hierarchical_router.py` (8 violations)
- `src/claude_orchestrator/entities/worker.py` (8 violations)
- `src/routing/orchestrator_router.py` (7 violations)
- `src/use_cases/task_planner.py` (7 violations)
- `src/adapters/agent/tools/file_reader.py` (6 violations)
- `src/claude_orchestrator/adapters/kubernetes_worker_pool.py` (6 violations)
- `src/adapters/cli/result_formatter.py` (5 violations)
- *... and 111 more files*

## Phase 4: Medium Priority

**Estimated Time:** 133.7 hours
**Total Violations:** 886

Internal helper functions, private methods, test function names

### Breakdown by Type

- **Variable Single Letter:** 322 violations
- **Function No Verb Noun:** 515 violations
- **Variable Hungarian Notation:** 49 violations

### Key Files to Refactor

- `tests/entities/category_theory/test_morphism.py` (45 violations)
- `tests/dsl/types/test_type_checker.py` (32 violations)
- `tests/dsl/types/test_type_inference_visitor.py` (26 violations)
- `src/dsl/types/type_system.py` (23 violations)
- `tests/monitoring/adapters/test_hf_inference_waker.py` (19 violations)
- `tests/entities/category_theory/test_workflow_morphism.py` (19 violations)
- `src/dsl/adapters/parser.py` (18 violations)
- `tests/monitoring/adapters/test_hf_inference_health_adapter.py` (15 violations)
- `tests/dsl/entities/test_monad.py` (15 violations)
- `tests/unit/test_tool_registry.py` (14 violations)
- *... and 190 more files*

## Phase 5: Low Priority

**Estimated Time:** 22.9 hours
**Total Violations:** 201

Variable names in small scopes, local helper variables, temporary variables

### Breakdown by Type

- **Directory Deep Nesting:** 3 violations
- **Variable Single Letter:** 177 violations
- **Variable Hungarian Notation:** 18 violations
- **File Not Snake Case:** 3 violations

### Key Files to Refactor

- `scripts/syd2_agent.py` (25 violations)
- `scripts/evaluate_baseline.py` (11 violations)
- `naming_audit.py` (9 violations)
- `scripts/parallel_data_collection.py` (9 violations)
- `training/scripts/prepare_training_data.py` (8 violations)
- `autonomous_dev_tool.py` (7 violations)
- `scripts/implement_phase2_recommendations.py` (7 violations)
- `scripts/grok_session.py` (6 violations)
- `tmp/mock_provider_container.py` (6 violations)
- `.claude/hooks/autocommit_post.py` (6 violations)
- *... and 56 more files*

