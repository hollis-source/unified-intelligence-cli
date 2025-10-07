"""Execution coordinator for task routing and execution.

Coordinates task execution with agent teams and adaptive model selection,
integrating with existing routing and adaptive learning infrastructure.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any

import re
from src.core.entities.file_ref import FileRef

from src.interfaces import (
    IExecutionCoordinator,
    ProjectState,
    ExecutionResult,
    TaskStatus,
    ITextGenerator
)
from src.entities import Task, Agent, AgentTeam, ExecutionContext
from src.entities.htn.htn_node import HTNNode
from src.routing.team_router import TeamRouter
from src.routing.adaptive_selector import AdaptiveModelSelector
from src.routing.adaptive_interfaces import SelectionRequirements, SelectionStrategy
from src.dsl.entities.ast_node import ASTNode
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition
from src.dsl.entities.product import Product
from src.adapters.agent.llm_executor import LLMAgentExecutor
from src.adapters.mcp.ssh_mcp_client import IRemoteFileSystem
from src.project_builder.execution.resource_resolver import ResourceResolver


logger = logging.getLogger(__name__)


class ExecutionCoordinator(IExecutionCoordinator):
    """Coordinator for task execution with agent routing and model selection.

    Integrates with:
    - TeamRouter: Routes tasks to appropriate agent teams
    - AdaptiveModelSelector: Selects optimal models for tasks
    - AgentTeams: Execute tasks via specialized agents

    Phase 2: Full integration with existing infrastructure
    Phase 3: Will add parallel execution and advanced scheduling

    Attributes:
        team_router: Router for team selection
        model_selector: Adaptive model selector
        teams: Available agent teams
    """

    def __init__(
        self,
        team_router: TeamRouter,
        model_selector: AdaptiveModelSelector,
        teams: List[AgentTeam],
        llm_provider: Optional[ITextGenerator] = None,
        prompt_mode: str = "manual",
        remote_fs: Optional[IRemoteFileSystem] = None,
        resource_resolver: Optional[ResourceResolver] = None
    ):
        """Initialize execution coordinator.

        Args:
            team_router: Team routing component
            model_selector: Adaptive model selection component
            teams: Available agent teams
            llm_provider: LLM provider for real execution (if None, uses mock)
            prompt_mode: Prompt generation mode - "manual" or "dspy" (Sprint 1)
            remote_fs: Remote file system for accessing remote codebases (DIP boundary)
        """
        self.team_router = team_router
        self.model_selector = model_selector
        self.teams = teams
        self.remote_fs = remote_fs
        self.resource_resolver = resource_resolver

        # Log remote filesystem availability
        if remote_fs:
            logger.info("ExecutionCoordinator initialized with remote filesystem access")

        # Initialize LLM executor for real execution
        if llm_provider:
            self.llm_executor = LLMAgentExecutor(
                llm_provider=llm_provider,
                provider_name="project-builder",
                orchestrator="coordinator",
                enable_cache=True,
                prompt_mode=prompt_mode  # Sprint 1: DSPy support
            )
            logger.info(f"ExecutionCoordinator initialized with real LLM execution (prompt_mode={prompt_mode})")
        else:
            self.llm_executor = None
            logger.info("ExecutionCoordinator initialized with mock execution")

    async def execute_workflows(
        self,
        workflows: ASTNode,
        state: ProjectState
    ) -> List[ExecutionResult]:
        """Execute DSL workflows with agent teams and model selection.

        Traverses DSL workflow, routes tasks to teams, selects models,
        and executes tasks following composition/product semantics.

        Args:
            workflows: DSL workflow to execute
            state: Current project state

        Returns:
            List of execution results for each task

        Example:
            workflow: design ∘ (backend ∘ frontend) ∘ test
            executes: design → backend → frontend → test (sequential)
        """
        results: List[ExecutionResult] = []

        # Extract primitive tasks from workflow
        tasks = self._extract_tasks(workflows, state)

        # Execute tasks
        for task, htn_node in tasks:
            logger.info(f"Executing task: {task.description}")

            # Route task to agent team
            agent = self.team_router.route(task, self.teams)
            logger.debug(f"  Routed to agent: {agent.role}")

            # Select optimal model for task
            model_id = self._select_model_for_task(task, agent)
            logger.debug(f"  Selected model: {model_id}")

            # Execute task
            result = await self._execute_task(task, agent, model_id, htn_node, state)
            results.append(result)

            # Apply effects immediately if task succeeded
            # This allows subsequent tasks to see the updated state
            if result.success and result.effects:
                state.world_state.update(result.effects)
                logger.debug(f"  Applied effects: {list(result.effects.keys())}")

            logger.info(f"  Task {'✓ succeeded' if result.success else '✗ failed'}")

        # Apply parent task effects for completed composite tasks
        # This fixes the bug where parent effects aren't applied when all subtasks complete
        self._apply_parent_effects(state)

        return results

    def _extract_tasks(
        self,
        workflow: ASTNode,
        state: ProjectState
    ) -> List[tuple[Task, HTNNode]]:
        """Extract executable tasks from DSL workflow.

        Traverses DSL AST and creates Task entities for each Literal node,
        matching with corresponding HTNNode for preconditions/effects.

        Args:
            workflow: DSL workflow AST
            state: Current project state

        Returns:
            List of (Task, HTNNode) tuples in execution order
        """
        tasks = []

        # Get execution order from workflow
        task_ids = self._get_execution_order(workflow)

        # Create Task entities for each task_id
        for task_id in task_ids:
            # Find corresponding HTN node
            htn_node = self._find_htn_node(state.htn_graph, task_id)

            if htn_node is None:
                logger.warning(f"HTN node not found for task_id: {task_id}")
                continue

            # Create Task entity
            task = Task(
                description=htn_node.description,
                task_type=self._infer_task_type(htn_node),
                task_id=task_id,
                metadata={"task_id": task_id}
            )


            # Extract FileRef resources from the task description
            inputs, outputs = self._extract_file_refs(
                htn_node.description,
                getattr(self.remote_fs, 'host', None)
            )
            task.resource_inputs = inputs
            task.resource_outputs = outputs

            tasks.append((task, htn_node))

        return tasks
    def _extract_file_refs(self, description: str, remote_host: Optional[str]) -> tuple[list[FileRef], list[FileRef]]:
        """Extract FileRef inputs/outputs from a task description.

        Finds absolute file paths in the description and converts them to FileRef
        instances. If a remote_host is provided, paths are treated as ssh:// URIs;
        otherwise as file:// URIs.
        """
        if not description:
            return ([], [])

        paths = re.findall(r'(/[-\w/\.]+)', description)  # matches absolute paths

        refs: list[FileRef] = []
        seen: set[str] = set()
        for p in paths:
            if p in seen:
                continue
            seen.add(p)
            uri = f"ssh://{remote_host}{p}" if remote_host else f"file://{p}"
            try:
                ref = FileRef.parse(uri)
                refs.append(ref)
            except Exception:
                # Skip invalid refs silently; debug-level log for visibility
                logger.debug(f"Skipping invalid file ref from path: {p}")
                continue

        # Without explicit intent classification, use the same set for inputs/outputs
        return (refs, refs.copy())


    def _get_execution_order(self, workflow: ASTNode) -> List[str]:
        """Get task execution order from DSL workflow.

        Args:
            workflow: DSL workflow AST

        Returns:
            List of task IDs in execution order
        """
        if isinstance(workflow, Literal):
            return [workflow.value]

        if isinstance(workflow, Composition):
            # Composition is right-to-left, so execute right first
            right_order = self._get_execution_order(workflow.right)
            left_order = self._get_execution_order(workflow.left)
            return right_order + left_order

        if isinstance(workflow, Product):
            # Product allows parallel execution
            # Phase 2: Execute sequentially, Phase 3: Will parallelize
            left_order = self._get_execution_order(workflow.left)
            right_order = self._get_execution_order(workflow.right)
            return left_order + right_order

        # Unknown node type
        logger.warning(f"Unknown workflow node type: {type(workflow)}")
        return []

    def _find_htn_node(self, node: HTNNode, task_id: str) -> Optional[HTNNode]:
        """Recursively find HTN node by task_id.

        Args:
            node: HTN node to search
            task_id: Task ID to find

        Returns:
            HTN node with matching task_id, or None
        """
        if node.task_id == task_id:
            return node

        for subtask in node.subtasks:
            found = self._find_htn_node(subtask, task_id)
            if found is not None:
                return found

        return None

    def _infer_task_type(self, htn_node: HTNNode) -> str:
        """Infer task type from HTN node description.

        Uses keyword matching to determine task type for model selection.

        Args:
            htn_node: HTN node

        Returns:
            Task type string
        """
        desc = htn_node.description.lower()

        # Check more specific task types first (to avoid false matches with generic keywords)

        # Testing tasks (check before 'write'/'create' which are generic)
        if any(kw in desc for kw in ['test', 'verify', 'validate']):
            return 'testing'

        # Documentation tasks (check before 'write'/'generate')
        if any(kw in desc for kw in ['document', 'doc', 'readme']):
            return 'documentation'

        # Design/architecture tasks
        if any(kw in desc for kw in ['design', 'architect', 'plan', 'schema']):
            return 'design'

        # Research tasks
        if any(kw in desc for kw in ['research', 'analyze', 'investigate']):
            return 'research'

        # Deployment tasks
        if any(kw in desc for kw in ['deploy', 'release', 'publish']):
            return 'deployment'

        # Implementation tasks (checked last since keywords are generic)
        if any(kw in desc for kw in ['implement', 'write', 'code', 'create', 'define', 'setup', 'configure', 'build', 'generate', 'develop']):
            return 'implementation'

        return 'general'

    def _select_model_for_task(self, task: Task, agent: Agent) -> str:
        """Select optimal model for task using adaptive learning.

        Args:
            task: Task to execute
            agent: Agent executing the task

        Returns:
            Selected model ID
        """
        # Define selection strategy based on task type
        strategy = self._determine_selection_strategy(task)

        # Create selection requirements
        requirements = SelectionRequirements(
            strategy=strategy,
            max_latency_ms=self._get_latency_threshold(task),
            min_success_rate=0.9  # Require 90% success rate
        )

        # Select model using adaptive selector
        try:
            model_id = self.model_selector.select_model(
                task_type=task.task_type,
                requirements=requirements
            )
        except (ValueError, Exception) as e:
            # Fallback to default model if selection fails
            logger.warning(f"Model selection failed: {e}, using fallback")
            model_id = "qwen3-hf-inference"  # Default to fast model

        return model_id

    def _determine_selection_strategy(self, task: Task) -> SelectionStrategy:
        """Determine optimal selection strategy for task type.

        Args:
            task: Task to execute

        Returns:
            Selection strategy enum
        """
        task_type = task.task_type

        # Design/architecture tasks: Prioritize quality
        if task_type in ['design', 'research']:
            return SelectionStrategy.MAXIMIZE_QUALITY

        # Implementation tasks: Balance quality and latency
        if task_type in ['implementation', 'coding']:
            return SelectionStrategy.BALANCED

        # Testing/deployment: Prioritize speed
        if task_type in ['testing', 'deployment']:
            return SelectionStrategy.MINIMIZE_LATENCY

        # Documentation: Minimize cost
        if task_type == 'documentation':
            return SelectionStrategy.MINIMIZE_COST

        # Default: Balanced
        return SelectionStrategy.BALANCED

    def _get_latency_threshold(self, task: Task) -> Optional[int]:
        """Get latency threshold for task type.

        Args:
            task: Task to execute

        Returns:
            Latency threshold in milliseconds, or None for no limit
        """
        task_type = task.task_type

        # Design/research: No hard limit (allow thinking models)
        if task_type in ['design', 'research']:
            return None

        # Implementation: 5 seconds
        if task_type in ['implementation', 'coding']:
            return 5000

        # Testing: 2 seconds
        if task_type == 'testing':
            return 2000

        # Documentation: 3 seconds
        if task_type == 'documentation':
            return 3000

        # Default: 5 seconds
        return 5000

    async def _execute_task(
        self,
        task: Task,
        agent: Agent,
        model_id: str,
        htn_node: HTNNode,
        state: ProjectState
    ) -> ExecutionResult:
        """Execute a single task with specified agent and model.

        Phase 3: Real execution with LLMAgentExecutor

        Args:
            task: Task to execute
            agent: Agent executing the task
            model_id: Model to use for execution
            htn_node: HTN node for preconditions/effects
            state: Current project state

        Returns:
            Execution result
        """
        # Check preconditions
        if not htn_node.check_preconditions(state.world_state):
            return ExecutionResult(
                task_id=task.metadata.get("task_id", "unknown"),
                success=False,
                effects={},
                error=f"Preconditions not satisfied: {htn_node.preconditions}",
                metadata={
                    "agent": agent.role,
                    "model": model_id,
                    "task_type": task.task_type
                }
            )

        if self.resource_resolver: await self.resource_resolver.ensure_inputs(task, state.world_state)

        # Real execution with LLM
        if self.llm_executor:
            try:
                # Build execution context from project state
                context = ExecutionContext(
                    session_id=state.project_id,
                    history=[],
                    llm_state=state.world_state,
                    user_data={
                        "htn_node": htn_node.task_id,
                        "model_id": model_id,
                        "preconditions": htn_node.preconditions,
                        "effects": htn_node.effects
                    }
                )

                # Execute task with real LLM
                logger.info(f"Executing task {task.description} with agent {agent.role} using model {model_id}")
                result = await self.llm_executor.execute(agent, task, context)

                # Log LLM output for visibility
                logger.info(f"LLM Output: {result.output[:500]}..." if len(str(result.output)) > 500 else f"LLM Output: {result.output}")

                # Map ExecutionResult to coordinator's expected format
                # Enhance HTN effects with actual LLM output
                enhanced_effects = dict(htn_node.effects)  # Copy HTN effects

                # Add task completion status flag for precondition checking
                # Format: {task_id: 'completed'}
                enhanced_effects[htn_node.task_id] = 'completed'

                # Store the actual artifact content in artifact_* keys (overwrites HTN filename placeholder)
                # AND in task-specific keys for context passing
                artifact_key = self._get_artifact_key(task, htn_node)
                if artifact_key:
                    enhanced_effects[artifact_key] = result.output

                # Also overwrite any artifact_* keys from HTN with actual content
                for key in list(enhanced_effects.keys()):
                    if key.startswith('artifact_'):
                        # Replace filename placeholder with actual LLM-generated content
                        enhanced_effects[key] = result.output
                        logger.debug(f"  Stored artifact in {key}")

                if self.resource_resolver and result.status.value == "success":
                    await self.resource_resolver.persist_outputs(task, state.world_state)

                return ExecutionResult(
                    task_id=task.metadata.get("task_id", "unknown"),
                    success=result.status.value == "success",
                    effects=enhanced_effects,  # Enhanced effects with actual content
                    error=result.errors[0] if result.errors else "",
                    metadata={
                        "agent": agent.role,
                        "model": model_id,
                        "task_type": task.task_type,
                        "description": task.description,
                        "llm_output": result.output,
                        "real_execution": True,
                        "artifact_key": artifact_key
                    }
                )

            except Exception as e:
                logger.error(f"Real execution failed for task {task.description}: {e}")
                return ExecutionResult(
                    task_id=task.metadata.get("task_id", "unknown"),
                    success=False,
                    effects={},
                    error=f"Execution failed: {str(e)}",
                    metadata={
                        "agent": agent.role,
                        "model": model_id,
                        "task_type": task.task_type,
                        "real_execution": True,
                        "error_type": type(e).__name__
                    }
                )
        else:
            # Fallback to mock execution if no LLM executor
            await asyncio.sleep(0.1)  # Simulate work
            return ExecutionResult(
                task_id=task.metadata.get("task_id", "unknown"),
                success=True,
                effects=htn_node.effects,
                error="",
                metadata={
                    "agent": agent.role,
                    "model": model_id,
                    "task_type": task.task_type,
                    "description": task.description,
                    "real_execution": False
                }
            )

    def _apply_parent_effects(self, state: ProjectState) -> None:
        """Apply effects from parent tasks when all their subtasks are completed.

        Traverses the HTN tree bottom-up, applying parent task effects
        when all subtasks have completed successfully. This fixes the issue
        where composite tasks don't apply their effects automatically.

        Args:
            state: Current project state to update
        """
        if not state.htn_graph:
            return

        # Recursively apply parent effects from bottom-up
        self._apply_parent_effects_recursive(state.htn_graph, state)

    def _apply_parent_effects_recursive(self, node: HTNNode, state: ProjectState) -> bool:
        """Recursively apply parent effects for completed composite tasks.

        Args:
            node: Current HTN node to check
            state: Project state to update

        Returns:
            True if this node (and all its subtasks) are completed
        """
        # Base case: leaf node (no subtasks)
        if not node.subtasks:
            # Check if this task is completed
            task_status = state.task_status.get(node.task_id, TaskStatus.PENDING)
            return task_status == TaskStatus.COMPLETED

        # Recursive case: check all subtasks
        all_subtasks_completed = True
        for subtask in node.subtasks:
            subtask_completed = self._apply_parent_effects_recursive(subtask, state)
            if not subtask_completed:
                all_subtasks_completed = False

        # If all subtasks completed, apply this parent's effects
        if all_subtasks_completed and node.effects:
            # Check if effects not already applied
            effects_already_applied = all(
                state.world_state.get(key) == value
                for key, value in node.effects.items()
            )

            if not effects_already_applied:
                # Apply parent effects
                state.world_state.update(node.effects)
                logger.info(f"Applied parent task effects for '{node.task_id}': {list(node.effects.keys())}")

                # Mark parent task as completed if not already
                if node.task_id not in state.task_status:
                    state.task_status[node.task_id] = TaskStatus.COMPLETED

        return all_subtasks_completed

    def _get_artifact_key(self, task: Task, htn_node: HTNNode) -> str:
        """Determine the artifact key for storing LLM output in world state.

        Args:
            task: Task being executed
            htn_node: HTN node with task metadata

        Returns:
            Key string for storing artifact (e.g., "generated_code", "api_design")
        """
        desc = task.description.lower()
        task_id = htn_node.task_id

        # Infer artifact type from task description
        if any(keyword in desc for keyword in ['generate code', 'write code', 'implement', 'code for']):
            return f"{task_id}_code"
        elif any(keyword in desc for keyword in ['write function', 'create function', 'function that']):
            return f"{task_id}_function"
        elif any(keyword in desc for keyword in ['design', 'schema', 'api', 'architecture']):
            return f"{task_id}_design"
        elif any(keyword in desc for keyword in ['write test', 'test code', 'test for']):
            return f"{task_id}_test"
        elif any(keyword in desc for keyword in ['document', 'readme', 'docs']):
            return f"{task_id}_docs"
        elif any(keyword in desc for keyword in ['save', 'write file', 'create file']):
            return f"{task_id}_file"
        else:
            # Generic artifact key
            return f"{task_id}_output"
