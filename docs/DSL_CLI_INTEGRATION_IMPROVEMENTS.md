# DSL-CLI Integration Improvements

## Implementation Status

### ✅ Sprint 1: Unified Entry Point + Lifecycle (COMPLETED)

**Implementation Date**: October 5, 2025

**Completed Tasks**:
1. ✅ Updated `src/main.py` with unified `--workflow` option
2. ✅ Implemented `LifecycleWorkflowExecutor` with Plan→Verify→Decompose→Execute phases
3. ✅ Added validation phase with workflow structure checks
4. ✅ Created comprehensive integration tests (21 tests, all passing)

**Deliverables**:
- **Unified CLI Interface**: Single entry point supporting both workflow and direct modes
  ```bash
  # Workflow mode
  python -m src.main --workflow examples/workflows/simple_pipeline.ct --verbose

  # Direct mode (backward compatible)
  python -m src.main --task "analyze code" --provider mock
  ```

- **Lifecycle-Aware Execution**: All workflows execute through lifecycle phases:
  - **PLAN**: Parse DSL file to AST, extract symbol table
  - **VERIFY**: Validate workflow structure (non-empty, executable nodes, functor definitions)
  - **DECOMPOSE**: Identify and count executable tasks
  - **EXECUTE**: Run workflow via interpreter with result tracking
  - **COMPLETE**: Return execution results with timing and phase information

- **Validation System**: `ValidationResult` dataclass with:
  - Boolean validity flag
  - List of validation issues
  - List of passed checks

- **Result Reporting**: `WorkflowExecutionResult` dataclass with:
  - Success/failure status
  - Execution results
  - Lifecycle state tracking
  - Execution time
  - Completed phases list
  - Error information

**Test Coverage**:
- Unit tests: `tests/dsl/use_cases/test_lifecycle_executor.py` (26 tests)
- Integration tests: `tests/integration/test_dsl_workflow_integration.py` (21 tests)
- Total: **47 tests, all passing**

**Git Commits**:
- Lifecycle executor implementation: `2a3f8cd`
- Unified CLI entry point: `f06f216`
- Integration tests: `7fc76b5`

**Benefits Achieved**:
- ✅ Single entry point for all execution modes
- ✅ Consistent configuration across DSL and direct modes
- ✅ Lifecycle phase tracking with verbose output
- ✅ Backward compatibility maintained
- ✅ Comprehensive test coverage

### 🔄 Sprint 2: HTN Decomposition (PENDING)
Status: Not started

### 🔄 Sprint 3: Graph Modeling + Executor Pool (PENDING)
Status: Not started

### 🔄 Sprint 4: Morphism Transformations (PENDING)
Status: Optional enhancement

---

## Current State Analysis

### Architecture Overview

**DSL Component** (`src/dsl/`):
- **Parser**: Converts `.ct` files to AST (category theory expressions)
- **Interpreter**: Executes AST via visitor pattern
- **CLITaskExecutor**: Bridges DSL to multi-agent CLI system
- **Entry Point**: Separate `run-dsl` command

**CLI Component** (`src/main.py`):
- **Main Entry**: Standard task execution with agent orchestration
- **Agent Factory**: Creates agents based on configuration
- **Team Factory**: Creates team-based routing (Week 12+)
- **Task Coordinator**: Orchestrates task execution across agents

**Current Integration**: The DSL and CLI are **loosely coupled** via `CLITaskExecutor`, which maps task names to agent names using hardcoded dictionaries and module imports.

### Pain Points Identified

#### 1. **Separate Execution Paths** ❌
```bash
# Standard CLI execution
python -m src.main --task "analyze code"

# DSL execution (separate command)
python -m src.main run-dsl workflow.ct
```
- **Problem**: Two entry points, inconsistent user experience
- **Impact**: Users must know which mode to use, can't mix paradigms

#### 2. **Hardcoded Task Mappings** ❌
```python
DEFAULT_TASK_MAPPING = {
    "plan": "master-orchestrator",
    "build": "python-specialist",
    "test": "unit-test-engineer",
    # ... brittle, not extensible
}
```
- **Problem**: Violates Open/Closed Principle, requires code changes for new tasks
- **Impact**: Can't dynamically add tasks, tight coupling to agent names

#### 3. **No Hierarchical Decomposition** ❌
- DSL supports composition (`f ∘ g`) and products (`f × g`)
- But no recursive task decomposition (Project → Task → Todo)
- **Impact**: Can't model complex, multi-level workflows

#### 4. **No Formal Verification** ❌
- DSL executes immediately after parsing
- No Plan → Verify → Decompose → Execute lifecycle
- **Impact**: Invalid workflows fail at runtime, not planning time

#### 5. **No Dependency Graph Modeling** ❌
- Task relationships are implicit in composition
- No explicit DAG for dependency tracking
- **Impact**: Can't detect cycles, optimize execution order, or visualize workflows

#### 6. **Limited Error Handling** ❌
```python
try:
    result = await interpreter.execute(main_node)
except Exception as e:
    click.echo(f"Execution error: {e}", err=True)
    raise
```
- **Problem**: Generic exception handling, no retry logic
- **Impact**: Transient failures kill entire workflow

## Proposed Improvements

### Phase 1: Unified Entry Point

**Goal**: Merge DSL and CLI execution paths into single cohesive interface.

**Implementation**:
```python
# src/main.py - Enhanced CLI
@click.command()
@click.option("--workflow", "-w", type=click.Path(exists=True),
              help="Execute .ct workflow file")
@click.option("--task", "-t", multiple=True,
              help="Direct task execution (existing)")
def main(workflow: str, task: tuple, ...):
    """Unified entry supporting both direct tasks and DSL workflows."""
    if workflow:
        # Execute DSL workflow with full CLI integration
        return execute_dsl_workflow(workflow, config)
    else:
        # Standard task execution
        return execute_tasks(task, config)
```

**Benefits**:
- ✅ Single entry point for all execution modes
- ✅ Consistent configuration (--provider, --routing, etc.)
- ✅ Shared agent infrastructure
- ✅ Better user experience

**Example**:
```bash
# Before: Separate commands
python -m src.main run-dsl workflow.ct
python -m src.main --task "analyze"

# After: Unified interface
python -m src.main --workflow workflow.ct --provider grok
python -m src.main --task "analyze" --provider grok
```

### Phase 2: HTN-Based Task Decomposition

**Goal**: Map DSL functors to hierarchical task networks for recursive decomposition.

**Implementation** (`src/dsl/use_cases/htn_executor.py`):
```python
from src.entities.htn import HTNNode

class HTNWorkflowExecutor:
    """Executes DSL workflows as hierarchical task networks."""

    def compile_to_htn(self, ast_node) -> HTNNode:
        """Convert DSL AST to HTN node hierarchy.

        Examples:
            - Literal("build") → Primitive HTN node
            - Composition(f, g) → Compound HTN with subtasks [g, f]
            - Functor("pipeline", expr) → Named HTN with decomposition
        """
        if isinstance(ast_node, Literal):
            # Primitive task (leaf node)
            return HTNNode(
                task_id=ast_node.value,
                description=f"Execute {ast_node.value}",
                subtasks=[],  # No decomposition
                preconditions={},
                effects={}
            )

        elif isinstance(ast_node, Composition):
            # Compound task: f ∘ g = execute g, then f
            parent = HTNNode(
                task_id=f"composition_{id(ast_node)}",
                description="Sequential composition",
                subtasks=[]
            )
            # Right-to-left execution (category theory semantics)
            parent.add_subtask(self.compile_to_htn(ast_node.right))
            parent.add_subtask(self.compile_to_htn(ast_node.left))
            return parent

        elif isinstance(ast_node, Product):
            # Parallel tasks: f × g = execute both concurrently
            parent = HTNNode(
                task_id=f"product_{id(ast_node)}",
                description="Parallel execution",
                subtasks=[]
            )
            parent.add_subtask(self.compile_to_htn(ast_node.left))
            parent.add_subtask(self.compile_to_htn(ast_node.right))
            return parent

        elif isinstance(ast_node, Functor):
            # Named workflow with recursive decomposition
            return HTNNode(
                task_id=ast_node.name,
                description=f"Execute functor: {ast_node.name}",
                subtasks=[self.compile_to_htn(ast_node.expression)]
            )

    async def execute_htn(self, htn_node: HTNNode, state: dict) -> Any:
        """Execute HTN node with state tracking."""
        # Check preconditions
        if not htn_node.check_preconditions(state):
            raise ValueError(f"Preconditions failed for {htn_node.task_id}")

        if htn_node.is_primitive():
            # Execute via task executor
            result = await self.task_executor.execute_task(
                htn_node.task_id, state
            )
            # Apply effects
            return htn_node.apply_effects(state), result
        else:
            # Decompose and execute subtasks
            decomposed = htn_node.decompose(state)
            results = []
            current_state = state.copy()

            for subtask in decomposed:
                new_state, result = await self.execute_htn(subtask, current_state)
                results.append(result)
                current_state = new_state

            return current_state, results
```

**Benefits**:
- ✅ Recursive decomposition (Project → Task → Todo)
- ✅ Precondition checking before execution
- ✅ State propagation with effects
- ✅ Supports hierarchical workflows

**Example DSL**:
```haskell
# workflow.ct - HTN decomposition example
build_feature :: () -> Feature
build_feature = deploy o test o implement o design

# Compiles to HTN:
# HTNNode(id="build_feature", subtasks=[
#   HTNNode(id="design"),
#   HTNNode(id="implement"),
#   HTNNode(id="test"),
#   HTNNode(id="deploy")
# ])
```

### Phase 3: Lifecycle Integration

**Goal**: Add Plan → Verify → Decompose → Execute phases to DSL workflows.

**Implementation** (`src/dsl/use_cases/lifecycle_workflow_executor.py`):
```python
from src.entities.lifecycle import Lifecycle, LifecycleState
from src.entities.htn import HTNNode

class LifecycleWorkflowExecutor:
    """Executes DSL workflows with lifecycle phases."""

    async def execute_with_lifecycle(
        self,
        dsl_text: str,
        verbose: bool = False
    ) -> Any:
        """Execute DSL workflow through full lifecycle."""
        lifecycle = Lifecycle()

        # Phase 1: PLAN - Parse DSL and compile to HTN
        ast = self.parser.parse(dsl_text)
        htn = self.compile_to_htn(ast)
        lifecycle.plan(plan_data={"ast": ast, "htn": htn})

        if verbose:
            click.echo(f"✓ PLAN: Compiled workflow to HTN (depth={htn.get_depth()})")

        # Phase 2: VERIFY - Validate workflow before execution
        validation_result = self.verify_workflow(htn)
        lifecycle.verify(
            verification_result=validation_result.is_valid,
            checks=validation_result.checks
        )

        if not validation_result.is_valid:
            lifecycle.fail(error="Validation failed",
                          issues=validation_result.issues)
            raise ValueError(f"Workflow validation failed: {validation_result.issues}")

        if verbose:
            click.echo(f"✓ VERIFY: Passed {len(validation_result.checks)} validation checks")

        # Phase 3: DECOMPOSE - Recursively decompose to executables
        initial_state = {}
        decomposed = htn.decompose(initial_state)
        lifecycle.decompose(decomposed_units=decomposed)

        if verbose:
            click.echo(f"✓ DECOMPOSE: {len(decomposed)} executable tasks")

        # Phase 4: EXECUTE - Run tasks with monitoring
        lifecycle.execute()

        try:
            final_state, results = await self.execute_htn(htn, initial_state)
            lifecycle.complete(
                final_state=final_state,
                results=results
            )

            if verbose:
                click.echo(f"✓ EXECUTE: Workflow completed successfully")

            return results

        except Exception as e:
            lifecycle.fail(error=str(e))

            # Support retry logic
            if should_retry(e):
                if verbose:
                    click.echo(f"⚠ FAILED: {e}. Retrying...")
                lifecycle.retry()
                # Recursive retry with updated plan
                return await self.execute_with_lifecycle(dsl_text, verbose)
            else:
                raise

    def verify_workflow(self, htn: HTNNode) -> ValidationResult:
        """Verify workflow before execution.

        Checks:
        - No circular dependencies (DAG validation)
        - All tasks have registered executors
        - Preconditions are satisfiable
        - Resource requirements are available
        """
        issues = []
        checks = []

        # Build dependency graph
        graph = self.htn_to_graph(htn)

        # Check 1: Detect cycles
        if graph.has_cycle():
            issues.append("Workflow contains circular dependencies")
        else:
            checks.append("DAG validation")

        # Check 2: Executor availability
        all_tasks = self.extract_all_tasks(htn)
        for task in all_tasks:
            if not self.executor_pool.get_available_executor(task):
                issues.append(f"No executor available for task: {task}")
            else:
                checks.append(f"Executor for {task}")

        # Check 3: Precondition satisfiability
        # (Static analysis - check if preconditions can be met)

        return ValidationResult(
            is_valid=len(issues) == 0,
            issues=issues,
            checks=checks
        )
```

**Benefits**:
- ✅ Catch errors before execution (Plan → Verify phases)
- ✅ Systematic workflow processing (Decompose → Execute)
- ✅ Retry logic on failures
- ✅ Better error messages with lifecycle context

**Example Execution**:
```bash
$ python -m src.main --workflow ci_pipeline.ct --verbose

✓ PLAN: Compiled workflow to HTN (depth=3)
✓ VERIFY: Passed 12 validation checks
  - DAG validation
  - Executor for build
  - Executor for test
  - Executor for deploy
✓ DECOMPOSE: 8 executable tasks
✓ EXECUTE: Workflow completed successfully

Results:
  build: success
  test: 45 tests passed
  deploy: deployed to production
```

### Phase 4: Graph-Based Dependency Modeling

**Goal**: Convert DSL workflows to explicit dependency graphs for optimization and visualization.

**Implementation** (`src/dsl/use_cases/graph_workflow_executor.py`):
```python
from src.entities.graph import Graph, GraphNode
from src.entities.htn import HTNNode

class GraphWorkflowExecutor:
    """Executes DSL workflows as dependency graphs."""

    def htn_to_graph(self, htn: HTNNode) -> Graph:
        """Convert HTN to dependency graph.

        Nodes: Tasks
        Edges: Dependencies (sequential or parallel)
        """
        graph = Graph()

        def add_htn_to_graph(node: HTNNode, parent_id: str = None):
            """Recursively add HTN nodes to graph."""
            # Add node
            graph.add_node(
                node_id=node.task_id,
                data={
                    "description": node.description,
                    "preconditions": node.preconditions,
                    "effects": node.effects
                }
            )

            # Add dependency edge from parent
            if parent_id:
                graph.add_edge(from_node=parent_id, to_node=node.task_id)

            # Add subtasks recursively
            for subtask in node.subtasks:
                add_htn_to_graph(subtask, parent_id=node.task_id)

        add_htn_to_graph(htn)
        return graph

    async def execute_graph(self, graph: Graph) -> Any:
        """Execute graph in dependency order."""
        # Topological sort for execution order
        execution_order = graph.topological_sort()

        # Execute in order
        results = {}
        state = {}

        for node_id in execution_order:
            node = graph.get_node(node_id)

            # Get dependencies' results
            predecessors = graph.get_predecessors(node_id)
            dependencies_met = all(
                pred in results for pred in predecessors
            )

            if not dependencies_met:
                raise ValueError(f"Dependencies not met for {node_id}")

            # Execute task
            result = await self.executor_pool.execute_task(
                task=node.data,
                **state
            )

            results[node_id] = result
            # Update state with effects
            state.update(node.data.get("effects", {}))

        return results
```

**Benefits**:
- ✅ Explicit dependency modeling
- ✅ Cycle detection before execution
- ✅ Topological sort for optimal execution order
- ✅ Visualization support (export to GraphViz)

**Example**:
```python
# Visualize workflow dependencies
graph = executor.htn_to_graph(htn)
visualize_graph(graph, output="workflow.png")
```

### Phase 5: Executor Pool Integration

**Goal**: Replace hardcoded task mappings with dynamic executor pool.

**Implementation** (`src/dsl/adapters/pool_task_executor.py`):
```python
from src.entities.executor import ExecutorPool, LocalExecutor

class PoolTaskExecutor:
    """Task executor using executor pool for dynamic routing."""

    def __init__(self, agent_factory, team_factory, config):
        """Initialize with CLI infrastructure."""
        self.pool = ExecutorPool()

        # Register executors from agent factory
        for agent in agent_factory.create_agents(config.agent_mode):
            executor = AgentExecutor(agent)  # Wrap agent as executor
            self.pool.register_executor(executor)

        # Register team executors (Week 12+)
        if config.routing_mode == "team":
            for team in team_factory.create_scaled_teams():
                executor = TeamExecutor(team)
                self.pool.register_executor(executor)

    async def execute_task(self, task_name: str, input_data: Any = None) -> Any:
        """Execute task via executor pool."""
        # Create task object
        task = Task(description=task_name, input=input_data)

        # Get available executor
        executor = self.pool.get_available_executor(task)

        if not executor:
            raise RuntimeError(f"No available executor for task: {task_name}")

        # Execute
        result = executor.execute(task)

        return result
```

**Benefits**:
- ✅ Dynamic executor selection
- ✅ Load balancing across agents/teams
- ✅ Fault tolerance (fallback executors)
- ✅ No hardcoded mappings

### Phase 6: Morphism-Based Transformations

**Goal**: Formalize DSL transformations as category-theoretic morphisms.

**Implementation** (`src/dsl/use_cases/morphism_workflow.py`):
```python
from src.entities.category_theory import Morphism

class MorphismWorkflowExecutor:
    """Executes DSL workflows as morphism compositions."""

    def compile_to_morphisms(self, ast_node) -> Morphism:
        """Convert DSL AST to morphism composition.

        Each task becomes a morphism: Task → Result
        Compositions chain morphisms with type safety
        """
        if isinstance(ast_node, Literal):
            # Task as morphism
            return Morphism(
                name=ast_node.value,
                source="Input",
                target="Output",
                transform=lambda x: self.execute_task(ast_node.value, x)
            )

        elif isinstance(ast_node, Composition):
            # f ∘ g = morphism composition
            f = self.compile_to_morphisms(ast_node.left)
            g = self.compile_to_morphisms(ast_node.right)
            return f.compose(g)  # Type-safe composition

        elif isinstance(ast_node, Product):
            # f × g = product morphism (parallel)
            # (Would need additional Product morphism type)
            pass

    async def execute_morphism(self, morphism: Morphism, input_data: Any) -> Any:
        """Execute morphism with input."""
        # Verify composition laws
        if not morphism.verify_left_identity():
            raise ValueError("Left identity law violated")
        if not morphism.verify_right_identity():
            raise ValueError("Right identity law violated")

        # Execute
        result = morphism(input_data)
        return result
```

**Benefits**:
- ✅ Type safety via morphism composition
- ✅ Formal verification (composition laws)
- ✅ Mathematical correctness guarantees

## Recommended Implementation Order

### ✅ Sprint 1: Unified Entry Point + Lifecycle (COMPLETED)
**Goal**: Merge DSL and CLI execution with lifecycle phases

**Status**: ✅ Completed on October 5, 2025

Tasks:
1. ✅ Update `src/main.py` to accept `--workflow` option
2. ✅ Implement `LifecycleWorkflowExecutor`
3. ✅ Add validation phase with basic checks
4. ✅ Update DSL integration tests (21 new integration tests + 26 unit tests)

**Deliverable**: ✅ Single entry point supporting both modes with Plan→Verify→Decompose→Execute

**Implementation**: See Implementation Status section at top of document for full details.

### Sprint 2: HTN Decomposition (3-5 days)
**Goal**: Enable hierarchical task decomposition

Tasks:
1. Implement `HTNWorkflowExecutor`
2. Map DSL AST nodes to HTN nodes
3. Add precondition/effect support to DSL
4. Create HTN execution tests

**Deliverable**: DSL workflows decompose into hierarchical task networks

### Sprint 3: Graph Modeling + Executor Pool (5-7 days)
**Goal**: Explicit dependency graphs and dynamic execution

Tasks:
1. Implement `GraphWorkflowExecutor`
2. Add cycle detection and topological sort
3. Replace `CLITaskExecutor` with `PoolTaskExecutor`
4. Integrate with agent/team factories

**Deliverable**: Workflows validated as DAGs, executed via executor pool

### Sprint 4: Morphism Transformations (Optional, 3-5 days)
**Goal**: Formal mathematical correctness

Tasks:
1. Implement `MorphismWorkflowExecutor`
2. Add composition law verification
3. Create property-based tests (hypothesis)

**Deliverable**: Type-safe workflow execution with formal verification

## Example: Unified Workflow

**Before** (Current):
```bash
# Separate commands, limited integration
python -m src.main run-dsl workflow.ct
```

**After** (Proposed):
```bash
# Unified interface with full integration
python -m src.main \
  --workflow ci_pipeline.ct \
  --provider grok \
  --routing team \
  --agents scaled \
  --collect-metrics \
  --verbose

Output:
✓ PLAN: Compiled workflow to HTN (depth=3, 12 tasks)
✓ VERIFY: Passed 15 validation checks
  - DAG validation (no cycles)
  - Executor availability (all tasks covered)
  - Resource constraints (within limits)
✓ DECOMPOSE: 12 executable tasks in dependency order
✓ EXECUTE: Running via Team-based routing
  [Category Theory Team] Analyzing architecture...
  [Backend Team] Building API endpoints...
  [Testing Team] Running integration tests...
  [DevOps Team] Deploying to production...
✓ COMPLETED: 12/12 tasks successful (47s elapsed)

Metrics saved to: data/metrics/session_20251005_120000.json
```

## Benefits Summary

**For Users**:
- ✅ Single, consistent interface
- ✅ Better error messages (lifecycle context)
- ✅ Workflow validation before execution
- ✅ Retry logic on failures

**For Developers**:
- ✅ Clean Architecture: Entities layer reused
- ✅ SOLID: Open/Closed (extensible without modification)
- ✅ Testable: Each phase independently testable
- ✅ Maintainable: Clear separation of concerns

**For System**:
- ✅ Hierarchical decomposition (HTN)
- ✅ Dependency tracking (Graph)
- ✅ Formal verification (Lifecycle + Morphisms)
- ✅ Dynamic execution (Executor Pool)

## Migration Strategy

1. **Preserve Backward Compatibility**: Keep `run-dsl` command working during transition
2. **Incremental Rollout**: Add `--workflow` flag first, migrate internals later
3. **Feature Flags**: Use config to enable new lifecycle/HTN features
4. **Testing**: Add integration tests for each sprint
5. **Documentation**: Update examples and user guide

## Next Steps

1. **Create feature branch**: `feature/dsl-cli-unification`
2. **Implement Sprint 1**: Unified entry + lifecycle
3. **Gather feedback**: Test with real workflows
4. **Iterate**: Refine based on usage patterns
5. **Document**: Update DSL guide with new capabilities
