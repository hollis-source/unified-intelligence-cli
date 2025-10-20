# ATADO Integration: Technical Implementation Details

**Companion Document to**: ATADO_INTEGRATION_STRATEGY.md  
**Date**: 2025-10-17  
**Purpose**: Detailed technical specifications for integration phases

---

## Table of Contents

1. [Phase 1: Entity Consolidation - Technical Spec](#phase-1-entity-consolidation)
2. [Phase 2: Goal Decomposition - Implementation](#phase-2-goal-decomposition)
3. [Phase 3: Feedback Loops - Implementation](#phase-3-feedback-loops)
4. [Phase 4: State Management - Implementation](#phase-4-state-management)
5. [Phase 5: Executor Consolidation - Implementation](#phase-5-executor-consolidation)
6. [Architectural Diagrams](#architectural-diagrams)
7. [Code Examples](#code-examples)

---

## Phase 1: Entity Consolidation

### Current State Analysis

**Duplicate Directories:**
```
src/entity/          # Primary (used by core)
src/entities/        # Duplicate (used by project_builder)
```

**Import Analysis:**
```bash
# Files importing from src/entity/
grep -r "from src.entity" src/ | wc -l
# Result: 127 files

# Files importing from src.entities/
grep -r "from src.entities" src/ | wc -l
# Result: 23 files (mostly in project_builder, dsl)
```

### Migration Plan

**Step 1: Enhance Primary Entities**

```python
# src/entity/htn/htn_node.py (ENHANCED)
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class HTNNode:
    """Hierarchical Task Network node with preconditions/effects.
    
    Consolidates functionality from:
    - src/entity/htn/htn_node.py (original)
    - src/entities/htn/htn_node.py (project_builder version)
    """
    task_id: str
    description: str
    subtasks: List["HTNNode"] = field(default_factory=list)
    
    # From project_builder: State management
    preconditions: Dict[str, Any] = field(default_factory=dict)
    effects: Dict[str, Any] = field(default_factory=dict)
    
    # From original: Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_primitive(self) -> bool:
        """Check if this is a leaf task."""
        return not self.subtasks
    
    def is_compound(self) -> bool:
        """Check if this has subtasks."""
        return bool(self.subtasks)
    
    def can_execute(self, world_state: Dict[str, Any]) -> bool:
        """Check if preconditions are satisfied (from project_builder)."""
        for key, required_value in self.preconditions.items():
            if key not in world_state:
                return False
            if world_state[key] != required_value:
                return False
        return True
    
    def apply_effects(self, world_state: Dict[str, Any]) -> Dict[str, Any]:
        """Apply effects to world state (from project_builder)."""
        new_state = world_state.copy()
        new_state.update(self.effects)
        return new_state
```

**Step 2: Create Migration Script**

```python
# scripts/migrate_entities.py
"""Automated migration from src/entities/ to src/entity/"""

import os
import re
from pathlib import Path

def migrate_imports(file_path: Path) -> None:
    """Replace src.entities imports with src.entity."""
    content = file_path.read_text()
    
    # Pattern: from src.entities.X import Y
    pattern = r'from src\.entities\.([\w.]+) import'
    replacement = r'from src.entity.\1 import'
    
    new_content = re.sub(pattern, replacement, content)
    
    if new_content != content:
        file_path.write_text(new_content)
        print(f"✓ Migrated: {file_path}")

def main():
    """Migrate all Python files."""
    src_dir = Path("src")
    
    for py_file in src_dir.rglob("*.py"):
        migrate_imports(py_file)
    
    print("\n✅ Migration complete!")
    print("Next steps:")
    print("1. Run tests: pytest tests/ -v")
    print("2. Check for import errors: python -m py_compile src/**/*.py")
    print("3. Remove src/entities/ directory")

if __name__ == "__main__":
    main()
```

**Step 3: Validation Checklist**

```bash
# 1. Run migration script
python scripts/migrate_entities.py

# 2. Run all tests
pytest tests/ -v --tb=short

# 3. Check for import errors
find src -name "*.py" -exec python -m py_compile {} \;

# 4. Verify no references to old directory
grep -r "from src.entities" src/
# Should return: no matches

# 5. Remove old directory
rm -rf src/entities/

# 6. Commit changes
git add -A
git commit -m "refactor: consolidate entities (Phase 1)"
```

---

## Phase 2: Goal Decomposition

### Interface Definition

```python
# src/interface/goal_decomposer.py
from abc import ABC, abstractmethod
from typing import Optional
from src.entity.htn import HTNNode

class IGoalDecomposer(ABC):
    """Interface for goal → HTN decomposition.
    
    Follows DIP: Core depends on abstraction, adapter implements.
    """
    
    @abstractmethod
    async def decompose_goal(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None
    ) -> HTNNode:
        """Decompose natural language goal into HTN structure.
        
        Args:
            goal: Natural language goal description
            context: Optional context (project info, constraints, etc.)
        
        Returns:
            HTNNode: Root of decomposed task hierarchy
        
        Raises:
            ValueError: If decomposition fails after retries
        """
        pass
```

### Use Case Implementation

```python
# src/use_cases/goal_decomposer.py
from dataclasses import dataclass
from typing import Optional, Dict, Any
import json
import re

from src.interface.goal_decomposer import IGoalDecomposer
from src.interface.llm_provider import ITextGenerator, LLMConfig
from src.entity.htn import HTNNode

@dataclass
class GoalDecomposerUseCase(IGoalDecomposer):
    """LLM-driven goal decomposition use case.
    
    Migrated from: src/project_builder/goal_decomposer/decomposer.py
    Enhanced with: Retry logic, validation, error handling
    """
    
    llm_provider: ITextGenerator
    max_retries: int = 3
    
    async def decompose_goal(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None
    ) -> HTNNode:
        """Decompose goal using LLM with retry logic."""
        
        temperature = 0.4
        last_error: Optional[Exception] = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                # Build prompt with context
                prompt = self._build_prompt(goal, context, attempt)
                
                # Generate HTN structure
                config = LLMConfig(
                    temperature=temperature,
                    max_tokens=8192
                )
                response = await self.llm_provider.generate(
                    messages=[{"role": "user", "content": prompt}],
                    config=config
                )
                
                # Parse and validate
                htn_data = self._parse_json(response)
                htn_node = self._dict_to_htn(htn_data)
                self._validate_htn(htn_node)
                
                # Safety: Remove root preconditions
                htn_node.preconditions = {}
                
                return htn_node
                
            except Exception as e:
                last_error = e
                # Reduce temperature for next attempt
                temperature = max(0.1, temperature - 0.1)
                continue
        
        raise ValueError(
            f"Failed to decompose goal after {self.max_retries} attempts: {last_error}"
        )
    
    def _build_prompt(
        self,
        goal: str,
        context: Optional[Dict[str, Any]],
        attempt: int
    ) -> str:
        """Build decomposition prompt."""
        
        base_prompt = f"""You are an expert planner. Convert the following goal into a Hierarchical Task Network (HTN) JSON structure.

Goal: {goal}

Required JSON structure:
{{
  "task_id": "unique_id",
  "description": "task description",
  "subtasks": [
    {{"task_id": "subtask1", "description": "...", "preconditions": {{}}, "effects": {{}}}},
    {{"task_id": "subtask2", "description": "...", "preconditions": {{}}, "effects": {{}}}}
  ],
  "preconditions": {{}},
  "effects": {{}}
}}

Return ONLY valid JSON, no markdown, no comments."""
        
        if attempt > 1:
            base_prompt += "\n\nCRITICAL: Previous response had errors. Return strict, valid JSON."
        
        if context:
            base_prompt += f"\n\nContext: {json.dumps(context, indent=2)}"
        
        return base_prompt
    
    def _parse_json(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        # Remove markdown code blocks if present
        response = re.sub(r'```json\s*', '', response)
        response = re.sub(r'```\s*', '', response)
        
        return json.loads(response.strip())
    
    def _dict_to_htn(self, data: Dict[str, Any]) -> HTNNode:
        """Convert dict to HTNNode recursively."""
        subtasks = [
            self._dict_to_htn(subtask)
            for subtask in data.get("subtasks", [])
        ]
        
        return HTNNode(
            task_id=data["task_id"],
            description=data["description"],
            subtasks=subtasks,
            preconditions=data.get("preconditions", {}),
            effects=data.get("effects", {}),
            metadata=data.get("metadata", {})
        )
    
    def _validate_htn(self, node: HTNNode) -> None:
        """Validate HTN structure."""
        if not node.task_id:
            raise ValueError("HTN node missing task_id")
        if not node.description:
            raise ValueError("HTN node missing description")
        
        # Validate subtasks recursively
        for subtask in node.subtasks:
            self._validate_htn(subtask)
```

### CLI Integration

```python
# src/main.py (ENHANCED)

@click.command()
@click.option("--goal", "-g", type=str,
              help="Natural language goal for decomposition (goal mode)")
@click.option("--workflow", "-w", type=click.Path(exists=True),
              help="Execute .ct workflow file (workflow mode)")
@click.option("--task", "-t", "task_descriptions", multiple=True,
              help="Task description (task mode)")
# ... other options ...
def main(
    goal: Optional[str],
    workflow: Optional[str],
    task_descriptions: tuple,
    # ... other params ...
) -> None:
    """Unified Intelligence CLI with three execution modes:
    
    1. Goal mode (--goal): LLM-driven goal decomposition
    2. Workflow mode (--workflow): Execute .ct DSL files
    3. Task mode (--task): Direct multi-agent execution
    """
    
    # Validate: Exactly one mode
    modes = [bool(goal), bool(workflow), bool(task_descriptions)]
    if sum(modes) != 1:
        click.echo("Error: Specify exactly one of --goal, --workflow, or --task")
        raise click.Abort()
    
    # Load configuration
    app_config = load_config(...)
    logger = setup_logging(...)
    
    try:
        # GOAL MODE: Decompose and execute
        if goal:
            execute_goal_mode(goal, app_config, logger)
            return
        
        # WORKFLOW MODE: Execute DSL
        if workflow:
            execute_workflow_mode(workflow, app_config, logger)
            return
        
        # TASK MODE: Direct execution
        if task_descriptions:
            execute_task_mode(task_descriptions, app_config, logger)
            return
    
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        raise


def execute_goal_mode(
    goal: str,
    app_config: Config,
    logger: logging.Logger
) -> None:
    """Execute goal decomposition mode."""
    
    logger.info(f"Goal mode: Decomposing goal '{goal}'")
    
    # Create dependencies
    llm_provider = ProviderFactory.create_provider(app_config.provider)
    goal_decomposer = GoalDecomposerUseCase(
        llm_provider=llm_provider,
        max_retries=3
    )
    
    # Decompose goal
    htn = asyncio.run(goal_decomposer.decompose_goal(goal))
    
    logger.info(f"Goal decomposed into HTN with {len(htn.subtasks)} top-level tasks")
    
    # Execute HTN via workflow executor
    from src.dsl.use_cases.htn_workflow_executor import HTNWorkflowExecutor
    from src.dsl.adapters.cli_task_executor import CLITaskExecutor
    
    task_executor = CLITaskExecutor()
    workflow_executor = HTNWorkflowExecutor(task_executor=task_executor)
    
    result = asyncio.run(workflow_executor.execute_htn(
        htn=htn,
        verbose=app_config.verbose
    ))
    
    # Format and display results
    formatter = ResultFormatter()
    click.echo(formatter.format_results([result]))
```

---

## Phase 3: Feedback Loops

### Interface Definition

```python
# src/interface/feedback_handler.py
from abc import ABC, abstractmethod
from typing import List
from src.entity.execution import ExecutionResult
from src.entity.state import ProjectState

class IFeedbackHandler(ABC):
    """Interface for feedback-driven replanning.
    
    Follows ISP: Narrow interface for feedback handling only.
    """
    
    @abstractmethod
    def replan(
        self,
        state: ProjectState,
        failed_tasks: List[ExecutionResult]
    ) -> ProjectState:
        """Analyze failures and create replanning strategy.
        
        Args:
            state: Current project state
            failed_tasks: List of failed task results
        
        Returns:
            ProjectState: Updated state with replanning applied
        
        Raises:
            ValueError: If replanning fails or project should abort
        """
        pass
```

### Use Case Implementation

```python
# src/use_cases/feedback_coordinator.py
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Any

from src.interface.feedback_handler import IFeedbackHandler
from src.entity.execution import ExecutionResult, ExecutionStatus
from src.entity.state import ProjectState, TaskStatus

class FailureType(Enum):
    """Classification of task failures."""
    TIMEOUT = auto()
    DEPENDENCY_MISSING = auto()
    MODEL_FAILURE = auto()
    PRECONDITION_VIOLATION = auto()
    RESOURCE_UNAVAILABLE = auto()
    UNKNOWN = auto()

class ReplanningStrategy(Enum):
    """Strategies for handling failures."""
    RETRY_WITH_DIFFERENT_MODEL = auto()
    REORDER_DEPENDENCIES = auto()
    REFINE_DECOMPOSITION = auto()
    FAIL_PROJECT = auto()

@dataclass
class FeedbackCoordinatorUseCase(IFeedbackHandler):
    """Feedback-driven replanning coordinator.
    
    Migrated from: src/project_builder/feedback/handler.py
    Enhanced with: Better failure classification, adaptive strategies
    """
    
    max_retries: int = 3
    failure_history: Dict[str, int] = field(default_factory=dict)
    
    def replan(
        self,
        state: ProjectState,
        failed_tasks: List[ExecutionResult]
    ) -> ProjectState:
        """Analyze failures and apply replanning strategy."""
        
        if not failed_tasks:
            return state
        
        # Analyze failures
        analysis = self._analyze_failures(failed_tasks)
        
        # Select strategy
        strategy = self._select_strategy(analysis, state)
        
        # Apply strategy
        new_state = self._apply_strategy(strategy, state, failed_tasks, analysis)
        
        # Record for future analysis
        self._record_failures(failed_tasks, analysis)
        
        return new_state
    
    def _analyze_failures(
        self,
        failed_tasks: List[ExecutionResult]
    ) -> Dict[str, Any]:
        """Classify and analyze failures."""
        
        failure_types: Dict[str, int] = {}
        error_messages: List[str] = []
        
        for result in failed_tasks:
            # Classify failure
            failure_type = self._classify_failure(result)
            failure_types[str(failure_type)] = failure_types.get(str(failure_type), 0) + 1
            
            # Collect error messages
            if result.error:
                error_messages.append(result.error)
        
        return {
            "total_failures": len(failed_tasks),
            "failure_types": failure_types,
            "error_messages": error_messages,
            "task_ids": [r.task_id for r in failed_tasks]
        }
    
    def _classify_failure(self, result: ExecutionResult) -> FailureType:
        """Classify failure type from result."""
        
        if not result.error:
            return FailureType.UNKNOWN
        
        error_lower = result.error.lower()
        
        if "timeout" in error_lower:
            return FailureType.TIMEOUT
        elif "dependency" in error_lower or "precondition" in error_lower:
            return FailureType.DEPENDENCY_MISSING
        elif "model" in error_lower or "llm" in error_lower:
            return FailureType.MODEL_FAILURE
        elif "resource" in error_lower:
            return FailureType.RESOURCE_UNAVAILABLE
        else:
            return FailureType.UNKNOWN
    
    def _select_strategy(
        self,
        analysis: Dict[str, Any],
        state: ProjectState
    ) -> ReplanningStrategy:
        """Select replanning strategy based on failure analysis."""
        
        total = analysis["total_failures"]
        types = analysis["failure_types"]
        
        # Dependency issues → reorder
        if types.get("dependency_missing", 0) >= max(1, total // 2):
            return ReplanningStrategy.REORDER_DEPENDENCIES
        
        # Precondition issues → refine
        if types.get("precondition_violation", 0) >= max(1, total // 2):
            return ReplanningStrategy.REFINE_DECOMPOSITION
        
        # Model/timeout issues → retry with different model
        if (types.get("model_failure", 0) + types.get("timeout", 0)) >= max(1, total // 2):
            return ReplanningStrategy.RETRY_WITH_DIFFERENT_MODEL
        
        # Too many failures → abort
        failed_count = sum(1 for s in state.task_status.values() if s == TaskStatus.FAILED)
        if failed_count / len(state.task_status) > 0.5:
            return ReplanningStrategy.FAIL_PROJECT
        
        # Default: retry
        return ReplanningStrategy.RETRY_WITH_DIFFERENT_MODEL
    
    def _apply_strategy(
        self,
        strategy: ReplanningStrategy,
        state: ProjectState,
        failed_tasks: List[ExecutionResult],
        analysis: Dict[str, Any]
    ) -> ProjectState:
        """Apply replanning strategy to state."""
        
        if strategy == ReplanningStrategy.RETRY_WITH_DIFFERENT_MODEL:
            # Reset failed tasks to pending
            for result in failed_tasks:
                if result.task_id in state.task_status:
                    state.task_status[result.task_id] = TaskStatus.PENDING
            return state
        
        elif strategy == ReplanningStrategy.REORDER_DEPENDENCIES:
            # Reorder tasks based on dependencies
            # (Implementation depends on dependency graph)
            for result in failed_tasks:
                if result.task_id in state.task_status:
                    state.task_status[result.task_id] = TaskStatus.PENDING
            return state
        
        elif strategy == ReplanningStrategy.REFINE_DECOMPOSITION:
            # Trigger re-decomposition (requires goal decomposer)
            raise ValueError("Refinement requires re-decomposition (not yet implemented)")
        
        elif strategy == ReplanningStrategy.FAIL_PROJECT:
            raise ValueError(f"Project failed: {analysis['total_failures']} failures")
        
        return state
    
    def _record_failures(
        self,
        failed_tasks: List[ExecutionResult],
        analysis: Dict[str, Any]
    ) -> None:
        """Record failures for historical analysis."""
        
        for result in failed_tasks:
            self.failure_history[result.task_id] = \
                self.failure_history.get(result.task_id, 0) + 1
```

### Integration with TaskCoordinator

```python
# src/use_cases/task_coordinator.py (ENHANCED)

@dataclass
class TaskCoordinatorUseCase:
    """Enhanced with feedback loop support."""
    
    task_planner: ITaskPlanner
    agent_selector: IAgentSelector
    agent_executor: IAgentExecutor
    feedback_handler: Optional[IFeedbackHandler] = None  # NEW
    max_replanning_attempts: int = 3  # NEW
    
    async def coordinate(
        self,
        tasks: List[Task],
        agents: List[Agent],
        context: Optional[ExecutionContext] = None,
        enable_feedback: bool = False  # NEW
    ) -> List[ExecutionResult]:
        """Coordinate with optional feedback loops."""
        
        results = []
        replanning_attempts = 0
        
        while replanning_attempts < self.max_replanning_attempts:
            # Execute tasks
            batch_results = await self._execute_batch(tasks, agents, context)
            results.extend(batch_results)
            
            # Check for failures
            failed = [r for r in batch_results if r.status == ExecutionStatus.FAILED]
            
            if not failed or not enable_feedback or not self.feedback_handler:
                break  # No failures or feedback disabled
            
            # Replan
            try:
                # Convert to ProjectState (adapter pattern)
                state = self._results_to_state(batch_results, tasks)
                
                # Apply feedback
                new_state = self.feedback_handler.replan(state, failed)
                
                # Extract tasks to retry
                tasks = self._state_to_tasks(new_state)
                
                replanning_attempts += 1
                self.logger.info(f"Replanning attempt {replanning_attempts}/{self.max_replanning_attempts}")
                
            except ValueError as e:
                self.logger.error(f"Replanning failed: {e}")
                break
        
        return results
```

---

## Architectural Diagrams

### Current Architecture (Before Integration)

```
┌─────────────────────────────────────────────────────────────┐
│                         User CLI                             │
└──────────────┬──────────────────────────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
       ▼                ▼
┌──────────┐    ┌──────────────┐
│ ui-cli   │    │ project-     │
│ (main.py)│    │ builder/cli  │
└────┬─────┘    └──────┬───────┘
     │                 │
     │                 │
     ▼                 ▼
┌─────────────────────────────────┐
│      ATADO Core                  │
│  ┌──────────────────────────┐   │
│  │ TaskCoordinator          │   │
│  │ (no feedback loops)      │   │
│  └──────────────────────────┘   │
│                                  │
│  ┌──────────────────────────┐   │
│  │ DSL System               │   │
│  │ (separate executors)     │   │
│  └──────────────────────────┘   │
└──────────────────────────────────┘

Issues:
- Multiple entry points
- Duplicate entities (entity/ vs entities/)
- Separate executors (CLITaskExecutor vs LLMAgentExecutor)
- No feedback loops in core
- project_builder isolated
```

### Target Architecture (After Integration)

```
┌─────────────────────────────────────────────────────────────┐
│                    Unified CLI (main.py)                     │
│                                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │  --goal  │  │--workflow│  │  --task  │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
└───────┼─────────────┼─────────────┼────────────────────────┘
        │             │             │
        ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                      ATADO Core                              │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Use Cases Layer                                         │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │ │
│  │  │ Goal         │  │ Task         │  │ Feedback     │ │ │
│  │  │ Decomposer   │  │ Coordinator  │  │ Coordinator  │ │ │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │ │
│  └─────────┼──────────────────┼──────────────────┼─────────┘ │
│            │                  │                  │           │
│            ▼                  ▼                  ▼           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Entity Layer (Consolidated)                            │ │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │ │
│  │  │ HTNNode │  │ Agent   │  │ State   │  │ Graph   │  │ │
│  │  │ (unified)│  │ Team    │  │ Manager │  │         │  │ │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Adapter Layer                                           │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │ │
│  │  │ LLM          │  │ DSL          │  │ State        │ │ │
│  │  │ Providers    │  │ Parser       │  │ Persistence  │ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘

Benefits:
- Single entry point
- Unified entities
- Single executor pattern
- Feedback loops integrated
- All features accessible via CLI
```

### Data Flow: Goal Mode

```
User: --goal "Build REST API"
  │
  ▼
┌─────────────────────────────────────┐
│ GoalDecomposerUseCase               │
│  - LLM prompt engineering           │
│  - JSON parsing & validation        │
│  - Retry logic                      │
└──────────────┬──────────────────────┘
               │
               ▼ HTNNode
┌─────────────────────────────────────┐
│ HTNWorkflowExecutor                 │
│  - Lifecycle phases                 │
│  - HTN traversal                    │
│  - Task execution                   │
└──────────────┬──────────────────────┘
               │
               ▼ ExecutionResult[]
┌─────────────────────────────────────┐
│ FeedbackCoordinatorUseCase          │
│  - Failure analysis                 │
│  - Strategy selection               │
│  - Replanning                       │
└──────────────┬──────────────────────┘
               │
               ▼ (if failures)
         [Retry Loop]
               │
               ▼
         Final Results
```

---

## Code Examples

### Example 1: Goal Decomposition

```bash
# CLI usage
python -m src.main \
  --goal "Build a REST API with user authentication and CRUD operations" \
  --provider auto \
  --routing team \
  --agents scaled \
  --feedback-loops \
  --max-retries 3
```

**Expected Output:**
```
2025-10-17 15:00:00 - INFO - Goal mode: Decomposing goal
2025-10-17 15:00:05 - INFO - Goal decomposed into HTN with 4 top-level tasks:
  1. design_api_schema
  2. implement_authentication
  3. implement_crud_operations
  4. write_tests

2025-10-17 15:00:05 - INFO - Executing HTN workflow
✓ PLAN: HTN structure validated (4 tasks, depth=2)
✓ VERIFY: All preconditions satisfied
✓ DECOMPOSE: 12 primitive tasks identified
✓ EXECUTE: Workflow in progress...

Task 1/12: design_api_schema → architecture-lead
Task 2/12: implement_user_model → backend-lead
...
Task 12/12: run_integration_tests → integration-test-engineer

✓ COMPLETE: All tasks executed successfully
```

### Example 2: Workflow with Optimization

```bash
# CLI usage
python -m src.main \
  --workflow examples/workflows/complex_pipeline.ct \
  --optimize \
  --transformations htn_flatten,htn_simplify,graph_deduplicate \
  --provider auto
```

**Workflow File (complex_pipeline.ct):**
```haskell
# Complex CI/CD pipeline with redundancy

functor build = compile o lint o format
functor test = integration_test o unit_test
functor deploy = production_deploy o staging_deploy

# Redundant composition (will be optimized)
functor ci_pipeline = deploy o test o build o build
```

**Expected Output:**
```
✓ PLAN: Parsed workflow from examples/workflows/complex_pipeline.ct
✓ VERIFY: Passed 2 validation checks
✓ DECOMPOSE: HTN: 7 tasks, depth=3, nodes=11

Applying optimizations:
  - htn_flatten: Removed 2 nested compositions
  - htn_simplify: Removed 1 duplicate task (build)
  - graph_deduplicate: Removed 0 duplicate edges

Optimized HTN: 6 tasks, depth=2, nodes=8 (27% reduction)

✓ EXECUTE: Workflow completed successfully
```

### Example 3: Feedback Loop in Action

```python
# Programmatic usage
from src.use_cases.task_coordinator import TaskCoordinatorUseCase
from src.use_cases.feedback_coordinator import FeedbackCoordinatorUseCase
from src.entity import Task, Agent

# Create coordinator with feedback
feedback_handler = FeedbackCoordinatorUseCase(max_retries=3)
coordinator = TaskCoordinatorUseCase(
    task_planner=planner,
    agent_selector=selector,
    agent_executor=executor,
    feedback_handler=feedback_handler
)

# Execute with feedback enabled
tasks = [
    Task(description="Implement feature X"),
    Task(description="Write tests for feature X"),
]

results = await coordinator.coordinate(
    tasks=tasks,
    agents=agents,
    enable_feedback=True
)

# Results include retry information
for result in results:
    print(f"Task: {result.task_id}")
    print(f"Status: {result.status}")
    print(f"Attempts: {result.metadata.get('attempts', 1)}")
    print(f"Replanning: {result.metadata.get('replanned', False)}")
```

---

## Testing Strategy

### Phase 1: Entity Consolidation Tests

```python
# tests/entity/test_htn_node_consolidated.py
import pytest
from src.entity.htn import HTNNode

def test_htn_node_with_preconditions():
    """Test HTNNode with preconditions (from project_builder)."""
    node = HTNNode(
        task_id="task1",
        description="Task 1",
        preconditions={"file_exists": True},
        effects={"file_processed": True}
    )
    
    # Test precondition checking
    world_state = {"file_exists": True}
    assert node.can_execute(world_state)
    
    world_state = {"file_exists": False}
    assert not node.can_execute(world_state)

def test_htn_node_apply_effects():
    """Test HTNNode effect application."""
    node = HTNNode(
        task_id="task1",
        description="Task 1",
        effects={"output_generated": True, "status": "complete"}
    )
    
    world_state = {"status": "pending"}
    new_state = node.apply_effects(world_state)
    
    assert new_state["output_generated"] is True
    assert new_state["status"] == "complete"
    assert world_state["status"] == "pending"  # Original unchanged
```

### Phase 2: Goal Decomposition Tests

```python
# tests/use_cases/test_goal_decomposer.py
import pytest
from unittest.mock import Mock, AsyncMock
from src.use_cases.goal_decomposer import GoalDecomposerUseCase

@pytest.mark.asyncio
async def test_goal_decomposition_success():
    """Test successful goal decomposition."""
    # Mock LLM provider
    llm_provider = Mock()
    llm_provider.generate = AsyncMock(return_value="""
    {
      "task_id": "build_api",
      "description": "Build REST API",
      "subtasks": [
        {"task_id": "design", "description": "Design API", "preconditions": {}, "effects": {"design_complete": true}},
        {"task_id": "implement", "description": "Implement API", "preconditions": {"design_complete": true}, "effects": {"api_complete": true}}
      ],
      "preconditions": {},
      "effects": {}
    }
    """)
    
    decomposer = GoalDecomposerUseCase(llm_provider=llm_provider)
    htn = await decomposer.decompose_goal("Build a REST API")
    
    assert htn.task_id == "build_api"
    assert len(htn.subtasks) == 2
    assert htn.subtasks[0].task_id == "design"
    assert htn.subtasks[1].preconditions == {"design_complete": True}

@pytest.mark.asyncio
async def test_goal_decomposition_retry():
    """Test retry logic on invalid JSON."""
    llm_provider = Mock()
    llm_provider.generate = AsyncMock(side_effect=[
        "Invalid JSON {",  # First attempt fails
        '{"task_id": "task1", "description": "Task", "subtasks": [], "preconditions": {}, "effects": {}}'  # Second succeeds
    ])
    
    decomposer = GoalDecomposerUseCase(llm_provider=llm_provider, max_retries=3)
    htn = await decomposer.decompose_goal("Simple goal")
    
    assert htn.task_id == "task1"
    assert llm_provider.generate.call_count == 2  # Retried once
```

---

## Performance Considerations

### Optimization Targets

**Goal Decomposition:**
- Target: < 10s for typical goals
- Optimization: Parallel LLM calls for large decompositions
- Caching: Cache decompositions for similar goals

**Feedback Loops:**
- Target: < 1s for failure analysis
- Optimization: Batch failure analysis
- Caching: Cache replanning strategies

**Workflow Optimization:**
- Target: < 100ms for morphism application
- Optimization: Lazy evaluation, memoization
- Caching: Cache optimized workflows

### Benchmarking

```python
# scripts/benchmark_integration.py
import time
import asyncio
from src.use_cases.goal_decomposer import GoalDecomposerUseCase

async def benchmark_goal_decomposition():
    """Benchmark goal decomposition performance."""
    
    goals = [
        "Build a simple REST API",
        "Create a machine learning pipeline",
        "Implement a microservices architecture"
    ]
    
    decomposer = GoalDecomposerUseCase(llm_provider=provider)
    
    for goal in goals:
        start = time.time()
        htn = await decomposer.decompose_goal(goal)
        elapsed = time.time() - start
        
        print(f"Goal: {goal}")
        print(f"Time: {elapsed:.2f}s")
        print(f"Tasks: {len(htn.subtasks)}")
        print()

if __name__ == "__main__":
    asyncio.run(benchmark_goal_decomposition())
```

---

## Migration Checklist

### Phase 1: Entity Consolidation
- [ ] Run migration script
- [ ] All tests pass
- [ ] No import errors
- [ ] Remove src/entities/ directory
- [ ] Update documentation
- [ ] Commit changes

### Phase 2: Goal Decomposition
- [ ] Create interface
- [ ] Implement use case
- [ ] Add CLI flag
- [ ] Write tests
- [ ] Update documentation
- [ ] Benchmark performance

### Phase 3: Feedback Loops
- [ ] Create interface
- [ ] Implement use case
- [ ] Integrate with TaskCoordinator
- [ ] Write tests
- [ ] Update documentation
- [ ] Test retry scenarios

### Phase 4: State Management
- [ ] Create interface
- [ ] Implement use case
- [ ] Add persistence layer
- [ ] Write tests
- [ ] Update documentation
- [ ] Test state recovery

### Phase 5: Executor Consolidation
- [ ] Deprecate CLITaskExecutor
- [ ] Update DSL interpreter
- [ ] Integrate team routing
- [ ] Write tests
- [ ] Update documentation
- [ ] Performance comparison

### Phase 6: Workflow Optimization
- [ ] Move morphism executor
- [ ] Add CLI flag
- [ ] Write tests
- [ ] Update documentation
- [ ] Benchmark optimizations

### Phase 7: Cleanup
- [ ] Remove deprecated code
- [ ] Update all documentation
- [ ] Final test suite run
- [ ] Performance benchmarking
- [ ] Release notes

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-17  
**Next Review**: After Phase 1 completion

