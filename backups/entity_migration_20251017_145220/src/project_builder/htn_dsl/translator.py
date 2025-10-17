from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from src.entities.htn.htn_node import HTNNode
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition
from src.dsl.entities.product import Product
from src.dsl.entities.ast_node import ASTNode


@dataclass
class HTNDSLTranslator:
    enable_parallel: bool = True

    def translate(self, node: HTNNode) -> ASTNode:
        # Primitive
        if not node.subtasks:
            return Literal(node.task_id)
        # Single child -> unwrap
        if len(node.subtasks) == 1:
            return self.translate(node.subtasks[0])
        # Multiple
        tasks = node.subtasks
        if not self.enable_parallel:
            exprs = [self.translate(t) for t in tasks]
            return self._build_sequential_composition(exprs)
        # Group by parallelizable sets
        groups = self._group_parallelizable_tasks(tasks)
        # Convert groups into expressions
        group_exprs: List[ASTNode] = []
        for g in groups:
            exprs = [self.translate(t) for t in g]
            if len(exprs) == 1:
                group_exprs.append(exprs[0])
            else:
                group_exprs.append(self._build_parallel_product(exprs))
        return self._build_sequential_composition(group_exprs)

    # ---------- Builders ----------
    def _build_sequential_composition(self, exprs: List[ASTNode]) -> ASTNode:
        if not exprs:
            raise ValueError("Cannot compose empty expression list")
        acc = exprs[0]
        for e in exprs[1:]:
            acc = Composition(left=e, right=acc)  # right-to-left: e ∘ acc
        return acc

    def _build_parallel_product(self, exprs: List[ASTNode]) -> ASTNode:
        if not exprs:
            raise ValueError("Cannot create product of empty expression list")
        acc = exprs[0]
        for e in exprs[1:]:
            acc = Product(left=acc, right=e)
        return acc

    # ---------- Grouping / Dependency analysis ----------
    def _group_parallelizable_tasks(self, tasks: List[HTNNode]) -> List[List[HTNNode]]:
        if not tasks:
            return [[]]
        groups: List[List[HTNNode]] = []
        current: List[HTNNode] = []
        produced_keys: set = set()

        def effects_keys(t: HTNNode) -> set:
            return set((t.effects or {}).keys())

        def precond_keys(t: HTNNode) -> set:
            return set((t.preconditions or {}).keys())

        for t in tasks:
            if not current:
                current = [t]
                produced_keys |= effects_keys(t)
                continue
            # Check if t depends on any produced in current
            if self._has_state_dependency_any(current, t):
                groups.append(current)
                current = [t]
                produced_keys = set(effects_keys(t))
            else:
                current.append(t)
                produced_keys |= effects_keys(t)
        if current:
            groups.append(current)
        return groups

    def _has_state_dependency_any(self, sources: List[HTNNode], target: HTNNode) -> bool:
        return any(self._has_state_dependency(s, target) for s in sources)

    def _has_state_dependency(self, a: HTNNode, b: HTNNode) -> bool:
        # b depends on a if any effect key from a appears in preconditions of b
        a_keys = set((a.effects or {}).keys())
        b_need = set((b.preconditions or {}).keys())
        return len(a_keys & b_need) > 0

    # ---------- Utilities ----------
    def get_task_execution_order(self, expr: ASTNode) -> List[str]:
        order: List[str] = []

        def walk(e: ASTNode):
            # Import types at runtime to avoid circular issues
            if isinstance(e, Literal):
                order.append(e.value)
            elif isinstance(e, Composition):
                # execute right then left
                walk(e.right)
                walk(e.left)
            elif isinstance(e, Product):
                # parallel: return left then right for determinism
                walk(e.left)
                walk(e.right)

        walk(expr)
        return order

