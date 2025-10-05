# Sprint 3: Graph Modeling + Executor Pool - Implementation Plan

**Sprint Goal**: Enable explicit dependency graphs with cycle detection and dynamic executor pool-based task execution

**Timeline**: 5-7 days
**Priority**: High
**Prerequisites**: Sprint 1 ✅, Sprint 2 ✅

---

## Executive Summary

Sprint 3 completes the DSL-CLI integration by adding:
1. **Graph-based workflow representation** (HTN → Graph conversion)
2. **DAG validation** (cycle detection before execution)
3. **Executor pool integration** (dynamic task routing)
4. **Enhanced VERIFY phase** (graph validation checks)

**Key Deliverable**: Workflows validated as DAGs and executed via executor pool with agent/team routing.

---

## Current State Analysis

### ✅ Already Implemented (Sprint 1-2)

**Entities Layer** (`src/entities/`):
- ✅ `Graph` class with cycle detection and topological sort (387 lines)
- ✅ `Executor` abstract class + `LocalExecutor` implementation (375 lines)
- ✅ `ExecutorPool` for executor management
- ✅ `HTNNode` with decomposition support (158 lines)
- ✅ `Lifecycle` state machine (336 lines)

**DSL Layer** (`src/dsl/`):
- ✅ `HTNCompiler` (AST → HTN conversion, visitor pattern)
- ✅ `HTNWorkflowExecutor` (lifecycle-aware execution)
- ✅ `CLITaskExecutor` (basic task → agent mapping)

**Test Coverage**:
- ✅ Graph tests: 33 tests (cycle detection, topological sort, traversal)
- ✅ Executor tests: 30 tests (pool, local executor, execution results)
- ✅ HTN tests: 23 tests (compilation, decomposition)
- ✅ Total: 609 tests passing

### 🔄 Sprint 3 Scope

**What We're Building**:

1. **GraphWorkflowExecutor** (`src/dsl/use_cases/graph_workflow_executor.py`)
   - Convert HTN → Graph for dependency modeling
   - Validate DAG (no cycles)
   - Execute in topological order

2. **PoolTaskExecutor** (`src/dsl/adapters/pool_task_executor.py`)
   - Replace CLITaskExecutor with executor pool
   - Integrate with AgentFactory and TeamFactory
   - Dynamic task routing based on agent/team capabilities

3. **Enhanced VERIFY Phase**
   - Add DAG validation (cycle detection)
   - Check executor availability for all tasks
   - Validate resource requirements

4. **Integration Tests**
   - Graph workflow execution tests
   - Executor pool integration tests
   - End-to-end workflow validation tests

---

## Architecture Design

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ HTNWorkflowExecutor (Sprint 2)                              │
│ ┌─────────┐ ┌────────┐ ┌──────────┐ ┌─────────┐ ┌─────────┤
│ │  PLAN   │→│ VERIFY │→│ DECOMPOSE│→│ EXECUTE │→│COMPLETE │
│ └─────────┘ └────────┘ └──────────┘ └─────────┘ └─────────┤
│                  │           │            │                  │
│                  ▼           ▼            ▼                  │
│         ┌──────────────────────────────────────┐            │
│         │  GraphWorkflowExecutor (NEW)         │            │
│         │  - htn_to_graph()                    │            │
│         │  - validate_dag()                    │            │
│         │  - execute_graph()                   │            │
│         └──────────────────────────────────────┘            │
│                              │                               │
│                              ▼                               │
│         ┌──────────────────────────────────────┐            │
│         │  PoolTaskExecutor (NEW)              │            │
│         │  - ExecutorPool                      │            │
│         │  - AgentExecutor wrappers            │            │
│         │  - TeamExecutor wrappers             │            │
│         └──────────────────────────────────────┘            │
│                              │                               │
│                              ▼                               │
│         ┌───────────────────────────────────────┐           │
│         │  Multi-Agent CLI Infrastructure       │           │
│         │  (AgentFactory, TeamFactory)          │           │
│         └───────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

### Class Relationships

```python
# Existing (Sprint 2)
HTNWorkflowExecutor extends LifecycleWorkflowExecutor
  - Uses HTNCompiler
  - Uses Lifecycle

# New (Sprint 3)
GraphWorkflowExecutor
  - Uses Graph entity
  - Uses HTNNode entity
  - Uses PoolTaskExecutor

PoolTaskExecutor
  - Uses ExecutorPool
  - Uses AgentFactory
  - Uses TeamFactory
  - Wraps agents/teams as Executor instances
```

---

## Detailed Implementation Plan

### Task 1: GraphWorkflowExecutor Implementation

**File**: `src/dsl/use_cases/graph_workflow_executor.py`

**Implementation**:
```python
from src.entities.graph import Graph
from src.entities.htn import HTNNode
from src.dsl.adapters.pool_task_executor import PoolTaskExecutor
from typing import Any, Dict, List

class GraphWorkflowExecutor:
    """Converts HTN to dependency graph and executes in topological order.

    Clean Architecture: Use Case layer (orchestrates graph conversion and execution)
    SOLID: SRP (single responsibility: graph-based execution)
    """

    def __init__(self, task_executor: PoolTaskExecutor):
        """Initialize with executor pool.

        Args:
            task_executor: Pool-based task executor for dynamic routing
        """
        self.task_executor = task_executor

    def htn_to_graph(self, htn: HTNNode) -> Graph:
        """Convert HTN to dependency graph.

        Nodes: Task IDs
        Edges: Dependencies (composition = sequential, product = parallel fork)

        Args:
            htn: Root HTN node

        Returns:
            Graph with task dependencies
        """
        graph = Graph()

        def add_htn_to_graph(node: HTNNode, parent_id: str = None):
            """Recursively add HTN nodes to graph."""
            # Add node if not already present
            if not graph.has_node(node.task_id):
                graph.add_node(
                    node_id=node.task_id,
                    data={
                        "description": node.description,
                        "preconditions": node.preconditions,
                        "effects": node.effects,
                        "metadata": node.metadata
                    }
                )

            # Add dependency edge from parent (composition = sequential dependency)
            if parent_id and parent_id != node.task_id:
                # Check if parent exists
                if not graph.has_node(parent_id):
                    graph.add_node(parent_id, data={"description": f"Parent: {parent_id}"})
                graph.add_edge(from_node=parent_id, to_node=node.task_id)

            # Process subtasks
            if node.is_compound():
                # Composition (sequential): Create chain
                if node.metadata.get("operator") == "∘":
                    # Right-to-left execution order (already in subtasks)
                    for i in range(len(node.subtasks)):
                        subtask = node.subtasks[i]
                        add_htn_to_graph(subtask, parent_id=node.task_id if i == 0 else node.subtasks[i-1].task_id)

                # Product (parallel): All depend on parent, no inter-dependencies
                elif node.metadata.get("operator") == "×":
                    for subtask in node.subtasks:
                        add_htn_to_graph(subtask, parent_id=node.task_id)

                # Functor or other compound node
                else:
                    for subtask in node.subtasks:
                        add_htn_to_graph(subtask, parent_id=node.task_id)

        add_htn_to_graph(htn)
        return graph

    def validate_dag(self, graph: Graph) -> List[str]:
        """Validate graph is a DAG (no cycles).

        Args:
            graph: Dependency graph

        Returns:
            List of validation issues (empty if valid)
        """
        issues = []

        if graph.has_cycle():
            issues.append("Workflow contains circular dependencies (cycle detected)")

        return issues

    async def execute_graph(self, graph: Graph, verbose: bool = False) -> Dict[str, Any]:
        """Execute graph in topological order.

        Args:
            graph: Dependency graph
            verbose: Enable verbose output

        Returns:
            Dictionary mapping task_id → execution result

        Raises:
            ValueError: If graph has cycles or dependencies not met
        """
        # Validate DAG
        issues = self.validate_dag(graph)
        if issues:
            raise ValueError(f"Cannot execute: {', '.join(issues)}")

        # Get topological order
        execution_order = graph.topological_sort()

        if verbose:
            print(f"Execution order: {execution_order}")

        # Execute tasks in order
        results = {}
        state = {}

        for task_id in execution_order:
            node = graph.get_node(task_id)

            if not node:
                continue  # Skip if node doesn't exist

            # Check dependencies met (all predecessors executed)
            predecessors = graph.get_predecessors(task_id)
            dependencies_met = all(pred in results for pred in predecessors)

            if not dependencies_met:
                missing = [p for p in predecessors if p not in results]
                raise ValueError(f"Dependencies not met for {task_id}: {missing}")

            # Execute task via pool
            result = await self.task_executor.execute_task(
                task_name=task_id,
                input_data=state
            )

            results[task_id] = result

            # Update state with effects
            if node.data and "effects" in node.data:
                state.update(node.data["effects"])

        return results
```

**Tests** (`tests/dsl/use_cases/test_graph_workflow_executor.py`):
- `test_htn_to_graph_simple_composition`
- `test_htn_to_graph_parallel_product`
- `test_htn_to_graph_nested_structure`
- `test_validate_dag_no_cycles`
- `test_validate_dag_detects_cycle`
- `test_execute_graph_topological_order`
- `test_execute_graph_dependency_validation`

**Estimated Lines**: 250-300
**Estimated Time**: 1.5 days

---

### Task 2: PoolTaskExecutor Implementation

**File**: `src/dsl/adapters/pool_task_executor.py`

**Implementation**:
```python
from src.entities.executor import ExecutorPool, Executor, ExecutionResult
from src.factories.agent_factory import AgentFactory
from src.factories.team_factory import TeamFactory
from typing import Any, Dict
import asyncio

class AgentExecutor(Executor):
    """Wraps an agent as an Executor.

    Adapter pattern: Adapts Agent interface to Executor interface.
    """

    def __init__(self, agent, llm_provider):
        """Initialize with agent and LLM provider.

        Args:
            agent: Agent entity from AgentFactory
            llm_provider: LLM provider for agent execution
        """
        super().__init__(
            executor_id=f"agent_{agent.role}",
            name=f"Agent: {agent.role}"
        )
        self.agent = agent
        self.llm_provider = llm_provider

    def can_execute(self, task: Any) -> bool:
        """Check if agent can handle task.

        Args:
            task: Task description (string) or dict with 'description'

        Returns:
            True if task matches agent capabilities
        """
        task_desc = task if isinstance(task, str) else task.get('description', '')
        task_lower = task_desc.lower()

        # Check if task matches agent capabilities
        for capability in self.agent.capabilities:
            if capability.lower() in task_lower:
                return True

        return False

    def execute(self, task: Any, **kwargs) -> ExecutionResult:
        """Execute task via agent.

        Args:
            task: Task to execute
            **kwargs: Additional parameters (input_data, state, etc.)

        Returns:
            ExecutionResult with agent output
        """
        # Update status
        self.status = ExecutorStatus.BUSY
        self.execution_count += 1

        try:
            # Extract task description
            task_desc = task if isinstance(task, str) else task.get('description', str(task))

            # Execute via LLM
            from src.adapters.agent.llm_executor import execute_agent_task
            result = execute_agent_task(
                agent=self.agent,
                task_description=task_desc,
                llm_provider=self.llm_provider
            )

            self.status = ExecutorStatus.IDLE
            return ExecutionResult(
                success=True,
                output=result.output if hasattr(result, 'output') else result,
                metadata={"agent": self.agent.role}
            )

        except Exception as e:
            self.status = ExecutorStatus.FAILED
            return ExecutionResult(
                success=False,
                error=str(e),
                metadata={"agent": self.agent.role}
            )


class PoolTaskExecutor:
    """Task executor using ExecutorPool for dynamic routing.

    Replaces CLITaskExecutor with pool-based approach for better:
    - Extensibility (Open/Closed Principle)
    - Dynamic routing (no hardcoded mappings)
    - Agent/Team integration

    Clean Architecture: Adapter layer (bridges DSL to CLI infrastructure)
    """

    def __init__(self, agent_factory: AgentFactory, llm_provider, config: Dict[str, Any]):
        """Initialize with agent factory and configuration.

        Args:
            agent_factory: Factory for creating agents
            llm_provider: LLM provider for agent execution
            config: Configuration (agent_mode, routing_mode, etc.)
        """
        self.pool = ExecutorPool()
        self.agent_factory = agent_factory
        self.llm_provider = llm_provider
        self.config = config

        # Register agent executors
        agents = agent_factory.create_agents(config.get('agent_mode', 'default'))
        for agent in agents:
            executor = AgentExecutor(agent, llm_provider)
            self.pool.register_executor(executor)

    async def execute_task(self, task_name: str, input_data: Any = None) -> Any:
        """Execute task via executor pool.

        Args:
            task_name: Task description
            input_data: Optional input data/state

        Returns:
            Task execution result

        Raises:
            ValueError: If no executor can handle task
        """
        # Get capable executor from pool
        executor = self.pool.get_available_executor(task_name)

        if not executor:
            raise ValueError(f"No executor available for task: {task_name}")

        # Execute synchronously (executor.execute is sync)
        result = executor.execute(task_name, input_data=input_data)

        if not result.success:
            raise ValueError(f"Task execution failed: {result.error}")

        return result.output
```

**Tests** (`tests/dsl/adapters/test_pool_task_executor.py`):
- `test_agent_executor_can_execute`
- `test_agent_executor_execution`
- `test_pool_task_executor_initialization`
- `test_pool_task_executor_routes_to_capable_agent`
- `test_pool_task_executor_fails_when_no_executor`

**Estimated Lines**: 200-250
**Estimated Time**: 1.5 days

---

### Task 3: Enhance HTNWorkflowExecutor with Graph Validation

**File**: `src/dsl/use_cases/htn_workflow_executor.py` (modify existing)

**Changes**:
1. Add `GraphWorkflowExecutor` integration
2. Enhance VERIFY phase with DAG validation
3. Add executor availability checks

**Implementation**:
```python
# In HTNWorkflowExecutor class

from src.dsl.use_cases.graph_workflow_executor import GraphWorkflowExecutor

def __init__(self, task_executor=None, parser=None):
    super().__init__(task_executor, parser)
    self.htn_compiler = HTNCompiler()
    self.graph_executor = GraphWorkflowExecutor(task_executor)  # NEW

async def execute_workflow(self, workflow_file: str, verbose: bool = False):
    # ... existing PLAN and VERIFY phases ...

    # PHASE 3: DECOMPOSE - HTN + Graph validation
    main_node = self._get_main_node(ast)
    htn_root = self.htn_compiler.compile(main_node)

    # NEW: Convert to graph for validation
    graph = self.graph_executor.htn_to_graph(htn_root)

    # NEW: Validate DAG (no cycles)
    graph_issues = self.graph_executor.validate_dag(graph)
    if graph_issues:
        lifecycle.fail(error="Graph validation failed", issues=graph_issues)
        return WorkflowExecutionResult(
            success=False,
            error=f"Graph validation failed: {', '.join(graph_issues)}",
            ...
        )

    # Existing HTN decomposition
    htn_decomposed = htn_root.decompose(state={})
    htn_depth = self._calculate_htn_depth(htn_root)

    lifecycle.decompose(decomposed_units={
        "htn_root": htn_root,
        "graph": graph,  # NEW
        "task_count": len(htn_decomposed),
        "htn_depth": htn_depth
    })

    if verbose:
        self._print_phase("DECOMPOSE",
            f"HTN: {len(htn_decomposed)} tasks, depth={htn_depth}, nodes={self._count_htn_nodes(htn_root)}")
        self._print_detail(f"Graph: {len(graph.nodes)} nodes, DAG validated ✓")  # NEW

    # ... continue with EXECUTE phase ...
```

**Tests** (`tests/dsl/use_cases/test_htn_workflow_executor.py` - extend existing):
- `test_execute_workflow_validates_dag`
- `test_execute_workflow_detects_cycles`
- `test_execute_workflow_graph_integration`

**Estimated Lines**: +100 (modification)
**Estimated Time**: 1 day

---

### Task 4: Integration Tests

**File**: `tests/integration/test_graph_workflow_integration.py`

**Test Scenarios**:
1. End-to-end workflow with graph validation
2. Cycle detection prevents execution
3. Executor pool routes tasks to correct agents
4. Topological execution order respected
5. Parallel product execution

**Example Test**:
```python
def test_workflow_validates_dag_before_execution(runner):
    """Test workflow validates DAG and rejects cycles."""
    # Create workflow with cycle
    workflow_file = tmp_path / "cycle_workflow.ct"
    workflow_file.write_text("""
        functor a = task_a
        functor b = task_b o a
        functor main = a o b  # Creates cycle: a → b → a
    """)

    result = runner.invoke(main, [
        '--workflow', str(workflow_file),
        '--verbose'
    ])

    assert result.exit_code != 0
    assert 'circular dependencies' in result.output
    assert 'Graph validation failed' in result.output
```

**Estimated Lines**: 300-400
**Estimated Time**: 1.5 days

---

### Task 5: Documentation Updates

**Files**:
1. `docs/DSL_CLI_INTEGRATION_IMPROVEMENTS.md` - Mark Sprint 3 COMPLETED
2. `README.md` - Add Graph validation section
3. `docs/ARCHITECTURE.md` - Update with graph workflow executor

**Content Updates**:
- Sprint 3 implementation details
- Graph validation examples
- Executor pool architecture
- Updated feature list

**Estimated Time**: 0.5 day

---

## Success Criteria

### Functional Requirements

✅ **Requirement 1**: HTN → Graph Conversion
- Given an HTN workflow
- When converted to graph
- Then all tasks are nodes, dependencies are edges

✅ **Requirement 2**: Cycle Detection
- Given a workflow with circular dependencies
- When validated
- Then cycle is detected and workflow rejected

✅ **Requirement 3**: Topological Execution
- Given a valid DAG workflow
- When executed
- Then tasks run in dependency order

✅ **Requirement 4**: Executor Pool Routing
- Given a task and pool of agent executors
- When task is submitted
- Then routed to capable agent automatically

✅ **Requirement 5**: Enhanced VERIFY Phase
- Given a workflow
- When in VERIFY phase
- Then DAG validation and executor availability checked

### Non-Functional Requirements

✅ **Performance**: Graph conversion < 100ms for workflows with 100 nodes
✅ **Backward Compatibility**: All Sprint 1-2 workflows still work
✅ **Test Coverage**: 95%+ for new code
✅ **Zero Regressions**: All 609 existing tests pass

### Acceptance Tests

```bash
# Test 1: Simple composition with graph validation
python -m src.main --workflow examples/workflows/simple_pipeline.ct --verbose
# Output includes: "Graph: 3 nodes, DAG validated ✓"

# Test 2: Cycle detection
python -m src.main --workflow examples/workflows/cycle_test.ct --verbose
# Output includes: "Graph validation failed: circular dependencies"

# Test 3: Executor pool routing
python -m src.main --workflow examples/workflows/multi_agent.ct --verbose
# Output shows different agents executing different tasks
```

---

## Implementation Timeline

### Day 1-2: GraphWorkflowExecutor
- Implement `htn_to_graph()` method
- Implement `validate_dag()` method
- Implement `execute_graph()` method
- Write unit tests (7 tests)

### Day 3-4: PoolTaskExecutor
- Implement `AgentExecutor` wrapper
- Implement `PoolTaskExecutor` class
- Integrate with AgentFactory
- Write unit tests (5 tests)

### Day 5: HTN Integration
- Enhance HTNWorkflowExecutor with graph validation
- Update DECOMPOSE phase
- Update VERIFY phase
- Write integration tests

### Day 6: Integration Testing
- End-to-end workflow tests
- Cycle detection tests
- Executor routing tests
- Performance tests

### Day 7: Documentation & Polish
- Update documentation
- Create example workflows
- Code review
- Final commit and merge

---

## Risk Analysis

### Risk 1: Graph Conversion Complexity
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**: HTN structure is already hierarchical; conversion is straightforward traversal

### Risk 2: Executor Pool Performance
**Likelihood**: Low
**Impact**: Medium
**Mitigation**: Executor pool already implemented and tested

### Risk 3: Backward Compatibility
**Likelihood**: Low
**Impact**: High
**Mitigation**: Sprint 3 extends Sprint 2 executor, no breaking changes

### Risk 4: Test Coverage
**Likelihood**: Low
**Impact**: Medium
**Mitigation**: Comprehensive test plan with clear test cases

---

## Deliverables Checklist

### Code Artifacts
- [ ] `src/dsl/use_cases/graph_workflow_executor.py` (250-300 lines)
- [ ] `src/dsl/adapters/pool_task_executor.py` (200-250 lines)
- [ ] Enhanced `src/dsl/use_cases/htn_workflow_executor.py` (+100 lines)
- [ ] `tests/dsl/use_cases/test_graph_workflow_executor.py` (200-300 lines)
- [ ] `tests/dsl/adapters/test_pool_task_executor.py` (150-200 lines)
- [ ] `tests/integration/test_graph_workflow_integration.py` (300-400 lines)
- [ ] Example workflow: `examples/workflows/graph_validated_pipeline.ct`

### Documentation
- [ ] `docs/DSL_CLI_INTEGRATION_IMPROVEMENTS.md` updated (Sprint 3 COMPLETED)
- [ ] `README.md` updated (Graph validation section)
- [ ] `docs/SPRINT_3_PLAN.md` (this document)
- [ ] Code review document

### Testing
- [ ] 15-20 new unit tests (graph executor, pool executor)
- [ ] 5-10 integration tests (end-to-end workflows)
- [ ] All 609 existing tests passing (no regressions)
- [ ] Target: 625-640 total tests passing

### Git Commits
- [ ] Commit 1: GraphWorkflowExecutor implementation + tests
- [ ] Commit 2: PoolTaskExecutor implementation + tests
- [ ] Commit 3: HTN integration with graph validation
- [ ] Commit 4: Integration tests and example workflows
- [ ] Commit 5: Documentation updates

---

## Post-Sprint Activities

### Sprint Review
- Demo graph-validated workflow execution
- Show cycle detection in action
- Present executor pool routing
- Review metrics (test coverage, performance)

### Retrospective Questions
1. Did graph conversion meet performance requirements?
2. Is executor pool routing working as expected?
3. Are error messages clear for cycle detection?
4. What challenges did we encounter?

### Next Steps (Sprint 4 - Optional)
- Morphism transformations (formal verification)
- Composition law verification
- Property-based testing with Hypothesis
- Advanced workflow optimizations

---

## References

- Sprint 1 Plan: `docs/DSL_CLI_INTEGRATION_IMPROVEMENTS.md` (Unified Entry Point)
- Sprint 2 Plan: `docs/DSL_CLI_INTEGRATION_IMPROVEMENTS.md` (HTN Decomposition)
- Graph Entity: `src/entities/graph/graph.py` (387 lines, fully tested)
- Executor Entity: `src/entities/executor/executor.py` (375 lines, fully tested)
- HTN Entity: `src/entities/htn/htn_node.py` (158 lines)

---

**Plan Created**: October 5, 2025
**Author**: Claude (Sonnet 4.5)
**Status**: READY FOR REVIEW
**Estimated Effort**: 5-7 days (1 developer)

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
