"""HTN to DSL workflow translator.

Converts Hierarchical Task Network graphs into Category Theory DSL workflows
for execution with automatic parallelization detection.
"""

from typing import List, Set

from src.entities.htn.htn_node import HTNNode
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition
from src.dsl.entities.product import Product
from src.dsl.entities.ast_node import ASTNode
from src.interfaces import IHTNDSLTranslator


class HTNDSLTranslator(IHTNDSLTranslator):
    """Translator for converting HTN graphs to DSL workflows.

    Implements the Visitor pattern to traverse HTN task graphs and generate
    corresponding DSL workflow expressions with automatic parallel execution
    detection.

    Phase 1: Sequential execution only (using Composition operator)
    Phase 2: Parallel execution detection (using Product operator)
    Phase 3: Advanced optimization and cost-based parallelization

    Attributes:
        enable_parallel: Whether to enable parallel execution detection
    """

    def __init__(self, enable_parallel: bool = True):
        """Initialize translator.

        Args:
            enable_parallel: Enable automatic parallel execution detection
        """
        self.enable_parallel = enable_parallel

    def translate(self, htn_graph: HTNNode) -> ASTNode:
        """Translate HTN task graph to DSL workflow.

        Recursively traverses HTN graph and generates DSL expressions:
        - Primitive tasks → Literal nodes
        - Compound tasks → Composition of subtasks (sequential)

        Args:
            htn_graph: HTN task graph to translate

        Returns:
            DSL workflow expression (ASTNode)

        Example:
            HTN: Project
                   ├── Design (primitive)
                   ├── Implement (compound)
                   │   ├── Backend (primitive)
                   │   └── Frontend (primitive)
                   └── Test (primitive)

            DSL: design ∘ (backend ∘ frontend) ∘ test
                 (Sequential execution: design → backend → frontend → test)
        """
        return self._visit_node(htn_graph)

    def _visit_node(self, node: HTNNode) -> ASTNode:
        """Visit a single HTN node and generate corresponding DSL expression.

        Phase 2: Detects parallelizable subtasks and uses Product operator.

        Args:
            node: HTN node to visit

        Returns:
            DSL expression for this node and its subtasks
        """
        # Base case: Primitive task becomes Literal
        if node.is_primitive():
            return Literal(node.task_id)

        # Recursive case: Analyze subtasks for parallelization opportunities
        if self.enable_parallel and len(node.subtasks) > 1:
            # Group subtasks into parallel batches
            parallel_groups = self._group_parallelizable_tasks(node.subtasks)

            # Convert each group to DSL expression
            group_expressions = []
            for group in parallel_groups:
                # Recursively visit tasks in group
                task_exprs = [self._visit_node(task) for task in group]

                # If group has multiple tasks, use Product for parallelism
                if len(task_exprs) > 1:
                    group_expressions.append(self._build_parallel_product(task_exprs))
                else:
                    group_expressions.append(task_exprs[0])

            # Compose groups sequentially (groups must execute in order)
            if len(group_expressions) == 1:
                return group_expressions[0]
            return self._build_sequential_composition(group_expressions)
        else:
            # No parallelization: fall back to sequential composition
            subtask_expressions = [
                self._visit_node(subtask)
                for subtask in node.subtasks
            ]
            return self._build_sequential_composition(subtask_expressions)

    def _build_sequential_composition(self, expressions: List[ASTNode]) -> ASTNode:
        """Build sequential composition from list of expressions.

        Creates nested Composition nodes following right-to-left composition order.
        This ensures execution proceeds left-to-right in the original list.

        Args:
            expressions: List of DSL expressions to compose

        Returns:
            Single Composition expression

        Raises:
            ValueError: If expressions list is empty

        Example:
            Input: [A, B, C]
            Output: (C ∘ (B ∘ A))
            Execution: A → B → C
        """
        if len(expressions) == 0:
            raise ValueError("Cannot compose empty expression list")

        if len(expressions) == 1:
            return expressions[0]

        # Build composition from right to left
        # This ensures left-to-right execution order
        result = expressions[0]
        for expr in expressions[1:]:
            result = Composition(left=expr, right=result)

        return result

    def _group_parallelizable_tasks(self, tasks: List[HTNNode]) -> List[List[HTNNode]]:
        """Group tasks into parallelizable batches.

        Groups tasks that have no state dependencies into parallel batches.
        Tasks with dependencies are placed in sequential groups.

        Args:
            tasks: List of HTN tasks to group

        Returns:
            List of task groups (each group can run in parallel)

        Algorithm:
            1. Build dependency graph between tasks
            2. Use topological ordering to identify independent tasks
            3. Group independent tasks into parallel batches
            4. Dependent tasks go in sequential groups

        Example:
            Tasks: [A, B, C] where B depends on A, C is independent
            Groups: [[A, C], [B]]  # A and C can run in parallel, then B
        """
        if len(tasks) <= 1:
            return [tasks]

        groups = []
        remaining = list(tasks)

        while remaining:
            # Find all tasks with no dependencies on remaining tasks
            current_batch = []
            for task in remaining:
                # Check if this task depends on any remaining task
                has_dependency = False
                for other in remaining:
                    if task is other:
                        continue
                    if self._has_state_dependency(other, task):
                        has_dependency = True
                        break

                if not has_dependency:
                    current_batch.append(task)

            # Remove batched tasks from remaining
            for task in current_batch:
                remaining.remove(task)

            if current_batch:
                groups.append(current_batch)
            else:
                # Circular dependency detected - put all remaining in sequence
                groups.extend([[task] for task in remaining])
                break

        return groups

    def _has_state_dependency(self, task1: HTNNode, task2: HTNNode) -> bool:
        """Check if task2 depends on task1's state changes.

        Args:
            task1: First task (potential dependency)
            task2: Second task (dependent)

        Returns:
            True if task2's preconditions overlap with task1's effects
        """
        # Check if task2's preconditions depend on task1's effects
        task1_effects = set(task1.effects.keys())
        task2_preconditions = set(task2.preconditions.keys())

        return bool(task1_effects & task2_preconditions)

    def _build_parallel_product(self, expressions: List[ASTNode]) -> ASTNode:
        """Build parallel product from list of expressions.

        Creates nested Product nodes for parallel execution.

        Args:
            expressions: List of DSL expressions to parallelize

        Returns:
            Single Product expression

        Raises:
            ValueError: If expressions list is empty

        Example:
            Input: [A, B, C]
            Output: ((A × B) × C)
            Execution: A, B, C all run in parallel
        """
        if len(expressions) == 0:
            raise ValueError("Cannot create product of empty expression list")

        if len(expressions) == 1:
            return expressions[0]

        # Build product left-to-right
        result = expressions[0]
        for expr in expressions[1:]:
            result = Product(left=result, right=expr)

        return result

    def get_task_execution_order(self, workflow: ASTNode) -> List[str]:
        """Extract execution order of tasks from DSL workflow.

        Utility method for debugging and visualization. Traverses DSL workflow
        and extracts task IDs in execution order.

        Args:
            workflow: DSL workflow expression

        Returns:
            List of task IDs in execution order

        Example:
            workflow: (C ∘ (B ∘ A))
            Returns: ['A', 'B', 'C']
        """
        if isinstance(workflow, Literal):
            return [workflow.value]

        if isinstance(workflow, Composition):
            # Composition is right-to-left, so reverse order
            right_order = self.get_task_execution_order(workflow.right)
            left_order = self.get_task_execution_order(workflow.left)
            return right_order + left_order

        if isinstance(workflow, Product):
            # Product allows parallel execution
            # Return left then right (order doesn't matter for parallel)
            left_order = self.get_task_execution_order(workflow.left)
            right_order = self.get_task_execution_order(workflow.right)
            return left_order + right_order

        # Unknown node type
        return []
