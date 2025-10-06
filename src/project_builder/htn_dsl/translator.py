"""HTN to DSL workflow translator.

Converts Hierarchical Task Network graphs into Category Theory DSL workflows
for execution. Phase 1 implements sequential translation only.
"""

from typing import List

from src.entities.htn.htn_node import HTNNode
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition
from src.dsl.entities.ast_node import ASTNode
from src.interfaces import IHTNDSLTranslator


class HTNDSLTranslator(IHTNDSLTranslator):
    """Translator for converting HTN graphs to DSL workflows.

    Implements the Visitor pattern to traverse HTN task graphs and generate
    corresponding DSL workflow expressions.

    Phase 1: Sequential execution only (using Composition operator)
    Phase 2: Will add parallel execution detection (using Product operator)

    Attributes:
        None (stateless translator)
    """

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

        Args:
            node: HTN node to visit

        Returns:
            DSL expression for this node and its subtasks
        """
        # Base case: Primitive task becomes Literal
        if node.is_primitive():
            return Literal(node.task_id)

        # Recursive case: Compound task becomes Composition of subtasks
        subtask_expressions = [
            self._visit_node(subtask)
            for subtask in node.subtasks
        ]

        # Build sequential composition (right-to-left evaluation)
        # Example: [A, B, C] → (C ∘ (B ∘ A))
        #   Execution order: A → B → C
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

        # Unknown node type
        return []
