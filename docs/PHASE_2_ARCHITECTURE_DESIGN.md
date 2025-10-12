# Phase 2 Architecture Design: DSL/HTN + HMAS + Tool Integration

Date: 2025-10-12
Status: Design Approved for Implementation (Incremental)

## 1. Executive Summary
- We extend the Phase 1 ReAct tool-use system with a Category-Theory DSL and HTN execution, enabling declarative workflows with sequential (∘), parallel (×), and planned choice (+) composition.
- Team-based routing (HMAS) gains explicit, configurable tool restrictions and context propagation from TeamRouter → Agent → Executor.
- SurrealDB becomes the unified state/telemetry backend for tool execution history, metrics, and audit trails, integrated at precise hook points in the executor and router.
- All additions preserve Clean Architecture and DIP: entities and use cases remain framework-agnostic; adapters encapsulate infrastructure concerns; integration is incremental and backward compatible.
- Success will be validated via unit/integration tests, DAG validation for HTN, category-law checks, and metrics improvements.

## 2. Architecture Overview Diagram (ASCII)
```
DSL (CT) Text → Parser → AST ─┐
                              │
                          HTN Compiler → HTN Tree → Graph Validator (DAG)
                              │                          │
                              └──────────────→ Interpreter (executes AST)
                                                      │
                                           TaskExecutor/Tools (ReAct)
                                                      │
TeamRouter (phase 1: team) → AgentTeam.route_internally → Agent → LLMAgentExecutor
                                                      │
                                             SurrealDB (tool history, metrics)
                                                      │
                                           Observability/Dogfooding Loop
```

## 3. Component Design

### 3.1 DSL/HTN Integration
- Existing execution path with HTN: src/dsl/use_cases/htn_workflow_executor.py
  - DECOMPOSE phase with HTN + graph validation (lines 128–177)
  - Interpreter execution remains backward compatible (lines 178–201)
- Operator semantics (Interpreter): src/dsl/use_cases/interpreter.py
  - Composition f ∘ g: lines 124–144 (sequential)
  - Product f × g: lines 146–179 (parallel with asyncio.gather)
  - Duplicate Δ: lines 181–195 (broadcast)
  - Functor: lines 197–208 (named workflow)
- Entities and parsing
  - Composition entity: src/dsl/entities/composition.py (lines 11–33; repr at 48–50)
  - Product entity: src/dsl/entities/product.py (lines 11–23, 33–51)
  - Functor entity: src/dsl/entities/functor.py (lines 11–23, 33–46)
  - Parser grammar: src/dsl/adapters/grammar.lark (operators at lines 76–82)
  - Parser transforms: src/dsl/adapters/parser.py
    - composition(): lines 67–73
    - product_expr(): lines 75–80
    - broadcast desugaring (product ∘ duplicate): lines 94–106
    - definition() to Functor: lines 122–140
- Mapping DSL operators to tool compositions
  - Sequential (∘): already implemented via visit_composition (interpreter.py 124–144); maps to sequential tool calls via recursive execute.
  - Parallel (×): already implemented via visit_product (interpreter.py 172–176) using asyncio.gather for concurrent tool invocations.
  - Choice (+): not yet implemented. Plan: introduce Coproduct entity and parser rule, with interpreter support for first-success/fallback strategy.
    - Reference: docs/CT_DSL_CLEAN_ARCHITECTURE.md lines 290–306.
- HTN integration points
  - HTN compilation: src/dsl/adapters/htn_compiler.py (lines 1–17) compiles AST→HTNNode.
  - Graph validation (DAG): src/dsl/use_cases/htn_workflow_executor.py lines 134–151.
  - Formal verification: type/category laws in src/dsl/types/category_laws.py (e.g., associativity checks lines 51–90, identities lines 93–147, product laws 149–258).

Design decision trade-offs
- Where to place tool composition logic: Interpreter (use case) vs TaskExecutor
  - Chosen: Interpreter orchestrates composition; TaskExecutor remains focused on primitive task execution. Pros: clear separation of concerns; Cons: Interpreter complexity increases. Mitigation: keep visit_* methods small and compositional (see lines 124–208).
- Represent workflows as AST+HTN
  - Pros: DSL stays declarative; HTN enables validation/planning; Cons: additional compilation step. Mitigation: keep HTN compiler adapter-only (htn_compiler.py) and DAG validation isolated.
- Choice operator semantics
  - Pros (first-success): simple, practical for tool fallbacks; Cons: non-determinism. Mitigation: deterministic priority order and explicit metrics logging per branch.

### 3.2 HMAS Integration (Teams + Tool Restrictions)
- Team abstraction: src/entities/agent_team.py
  - Default route_internally fallback: lines 55–61
  - FrontendTeam routing: lines 121–139
  - BackendTeam routing: lines 155–172
  - TestingTeam routing: lines 194–233
  - Additional teams (Infrastructure/Research/etc.): lines 235–427
- Team Router: src/routing/team_router.py
  - route(): lines 52–103 (two-phase: team then agent)
  - _select_team(): lines 104–181 (domain mapping lines 130–147, metrics integration at 92–101)
- Tool registry (Phase 1): src/adapters/agent/tools/registry.py (lines 18–40)

Design additions for Phase 2
- Team→Tool mapping configuration
  - New adapter config: team_tool_policy in composition root (src/composition.py) to construct a TeamAwareToolRegistry per team.
  - Enforce policy in LLMAgentExecutor._execute_react at action parsing (src/adapters/agent/llm_executor.py lines 441–456): reject tools not in allowed set and log policy violations.
- Passing tool context through router
  - Extend ExecutionContext (src/entities/execution.py lines 43–52) with optional allowed_tools: List[str] and tool_session_id: str.
  - When TeamRouter selects team (team_router.py route lines 75–103), the coordinator builds ExecutionContext with allowed_tools = team_policy[team.name].
  - LLMAgentExecutor._build_react_context (lines 375–388) uses either context.allowed_tools to filter tool descriptions or a TeamAwareToolRegistry.
- Inter-agent tool result sharing
  - Use SurrealDB ToolHistory (see 3.3) keyed by session_id and task_id; LLMAgentExecutor records each tool invocation (see integration points below). Subsequent agents retrieve summarized results via context.llm_state and/or explicit history fetch before execution.

Trade-offs
- Central policy in composition.py vs per-team class embedding
  - Chosen: central declarative config at composition root to avoid modifying domain entities; Pros: DIP and SRP preserved; Cons: indirection. Mitigation: helper to access team policy quickly.
- Allowlist vs Denylist
  - Chosen: Allowlist (secure by default). Denylist can be added for overrides.

### 3.3 State Management (SurrealDB)
- Existing repository: src/project_builder/state/surreal_repository.py
  - Connection and health: lines 82–95
  - Query exec: lines 96–155
  - CRUD for projects: save (156–208), load (209–265), exists (266–288), delete (289–300)
  - Metrics/dashboard example: get_project_dashboard_data (386–434)

Phase 2 schema (new records)
- Tables
  - tool_executions: one row per tool call
  - agent_executions: one row per agent execution
  - tasks: existing or mirrored as needed for cross-linking
- Edges/relations (logical): executed_by (tool_execution → agent), part_of_task (tool_execution → task), belongs_to_session (any → session), produces_artifact

SurrealQL (conceptual)
```sql
-- tool execution history
CREATE TABLE tool_executions;
-- Fields: id, session_id, task_id, agent_role, tool_name, params_json, success, error, started_at, duration_ms, output_summary

-- agent execution summary
CREATE TABLE agent_executions;
-- Fields: id, session_id, task_id, agent_role, status, duration_ms, cache_hit, provider, orchestrator
```

Persistence hook points
- LLMAgentExecutor._execute_react (src/adapters/agent/llm_executor.py)
  - Before tool call: lines 441–449
  - After tool call: lines 449–453
  - Integration: insert ToolHistoryRepository.record_invocation(session_id, task_id, agent_role, tool_name, params, result/duration)
- LLMAgentExecutor.execute success/failure returns
  - Success path: lines 263–273
  - Failure path: lines 321–327
  - Integration: record agent_executions with status, duration, cache_hit, errors
- TeamRouter.route metrics
  - Lines 92–101 integrate with DomainClassifier.metrics_collector; add hook to also upsert routing events into SurrealDB if configured.

Trade-offs
- Single SurrealDB repo vs dedicated ToolHistoryRepository
  - Chosen: dedicated ToolHistoryRepository adapter to keep concerns separate from project state; Pros: SRP, testability; Cons: two repos. Mitigation: shared base client for Surreal HTTP.

### 3.4 Dogfooding Loop
- Agents access their own execution history via ToolHistoryRepository queries filtered by session_id/agent_role.
- Self-improvement workflow
  1) Gather metrics (exec and tool histories) from SurrealDB
  2) Analyze via QA/Research agents (routed by TeamRouter)
  3) Produce recommendations (docs/issues) and optionally trigger refactoring tasks
- Integration with Observability (src/observability/)
  - Use json_logger and tracing to enrich logs with session_id/task_id/tool_name for correlation.

## 4. Integration Points (file paths + line numbers + examples)
1) Add Coproduct (+) operator
- File: src/dsl/entities/coproduct.py (NEW)
- File: src/dsl/adapters/grammar.lark — add TOKEN for "+" (next to PRODUCT at lines 80–82) and rule: expression COPRODUCT expression -> coproduct
- File: src/dsl/adapters/parser.py — add coproduct() transformer and visit_coproduct in interpreter
- Trade-off: Adds non-determinism; document first-success semantics and metrics logging.

2) Team-aware tool policy wiring
- File: src/composition.py
  - Around lines 84–92, after ToolRegistry creation, build TeamAwareToolRegistry per team and pass into LLMAgentExecutor via enable_react.
  - Example insertion:
    - Inject policy map from config, e.g., {"Testing": ["pytest"], "Frontend": ["npm"]}.

3) Enforce tool allowlist during ReAct
- File: src/adapters/agent/llm_executor.py
  - At lines 441–456 (after parsing action), check tool name against allowed_tools from context or team registry; on violation, append Observation with error and continue.
  - Also call ToolHistoryRepository.record_invocation before/after tool.execute (lines 449–453) with status and latency.

4) Pass allowed_tools via ExecutionContext
- File: src/entities/execution.py — extend dataclass at lines 43–52 with: allowed_tools: list[str] = field(default_factory=list); tool_session_id: str = "".
- File: src/project_builder/execution/coordinator.py — when building ExecutionContext (lines 472–482), set allowed_tools via team policy and propagate session_id.

5) Persist agent executions
- File: src/adapters/agent/llm_executor.py
  - Success record at lines 263–273
  - Failure record at lines 321–327

6) Optional: Domain routing persistence
- File: src/routing/team_router.py — after lines 92–101, if ToolHistoryRepository is configured, upsert routing event (task_description, domain, team, agent, score).

## 5. Data Flow Diagrams (Textual)
- DSL Path: text → Parser → AST → HTNCompiler → HTN Tree → GraphValidator(DAG) → Interpreter → TaskExecutor/Tools → SurrealDB (history) → Observability.
- HMAS Path: Task → TeamRouter(classify) → AgentTeam.route_internally → Agent → LLMAgentExecutor (ReAct, tools) → SurrealDB (agent_executions, tool_executions).
- Dogfooding Path: SurrealDB (history, metrics) → Research/QA agents → recommendations → new tasks → repeat.

## 6. Database Schema (SurrealDB)
Minimal initial schema (iterative):
- tool_executions(id, session_id, task_id, agent_role, tool_name, params_json, started_at, duration_ms, success, error, output_preview)
- agent_executions(id, session_id, task_id, agent_role, status, duration_ms, cache_hit, provider, orchestrator)
Indices: session_id, task_id, agent_role, tool_name; time-based ordering on started_at.

## 7. Implementation Sequence (Incremental)
- Phase 2a: Team tool policy + allowlist enforcement + persistence hooks (executor/router)
- Phase 2b: SurrealDB ToolHistoryRepository + write paths + dashboards via get_project_dashboard_data pattern
- Phase 2c: Coproduct (+) operator (entities, grammar, parser, interpreter with first-success) + tests
- Phase 2d: Dogfooding loop: QA/Research agents analyze histories; surface recommendations
- Phase 2e: Formal verification tests (category_laws) + HTN DAG tests; perf tuning

## 8. Risk Assessment
- Non-determinism with +: mitigate via ordering and metrics; provide deterministic mode in tests.
- SurrealDB availability: add health checks and fallbacks (buffer to file) if unreachable.
- Tool policy drift: centralize config; unit tests to enforce allowlists per team.
- Performance of parallel ×: ensure bounded concurrency; measure via observability.

## 9. Success Criteria
- Backward compatibility: existing Phase 1 flows still pass (8/8 pytest).
- New unit tests for: tool allowlists, persistence hooks, coproduct semantics, category laws.
- HTN: DAG validation errors caught and surfaced; interpreter executes parallel branches concurrently.
- Metrics: routing and tool usage visible; cache effectiveness unchanged or improved for ULTRATHINK tasks.

