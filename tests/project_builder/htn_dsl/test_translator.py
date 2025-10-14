"""Tests for HTNDSLTranslator - HTN graph to DSL workflow conversion.

Tests cover translation of HTN task graphs to DSL workflows with automatic
parallelization detection via precondition/effect analysis.
"""

import pytest
from src.project_builder.htn_dsl.translator import HTNDSLTranslator
from src.entities.htn.htn_node import HTNNode
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition
from src.dsl.entities.product import Product
from src.dsl.entities.ast_node import ASTNode


@pytest.fixture
def translator():
    """Fixture providing HTNDSLTranslator instance with parallelization enabled."""
    return HTNDSLTranslator(enable_parallel=True)


@pytest.fixture
def translator_sequential():
    """Fixture providing HTNDSLTranslator with parallelization disabled."""
    return HTNDSLTranslator(enable_parallel=False)


class TestHTNDSLTranslatorBasic:
    """Tests for basic translation of primitive and simple HTN nodes."""

    def test_translate_primitive_node(self, translator):
        """Test translating primitive HTN node to Literal."""
        node = HTNNode(task_id="build", description="Build project")
        
        result = translator.translate(node)
        
        assert isinstance(result, Literal)
        assert result.value == "build"

    def test_translate_primitive_with_metadata(self, translator):
        """Test primitive node translation preserves task_id only."""
        node = HTNNode(
            task_id="test",
            description="Run tests",
            metadata={"priority": "high"}
        )
        
        result = translator.translate(node)
        
        assert isinstance(result, Literal)
        assert result.value == "test"

    @pytest.mark.parametrize("task_id", ["deploy", "lint", "format", "analyze"])
    def test_translate_various_primitive_tasks(self, translator, task_id):
        """Parametrized test for various primitive task IDs."""
        node = HTNNode(task_id=task_id, description=f"Execute {task_id}")
        
        result = translator.translate(node)
        
        assert isinstance(result, Literal)
        assert result.value == task_id

    def test_translate_single_subtask_compound(self, translator):
        """Test compound node with single subtask returns unwrapped subtask."""
        child = HTNNode(task_id="child", description="Child task")
        parent = HTNNode(
            task_id="parent",
            description="Parent task",
            subtasks=[child]
        )
        
        result = translator.translate(parent)
        
        # Single subtask should be unwrapped (no composition needed)
        assert isinstance(result, Literal)
        assert result.value == "child"


class TestCompositionGeneration:
    """Tests for sequential composition generation."""

    def test_translate_two_sequential_tasks(self, translator_sequential):
        """Test two sequential tasks create Composition."""
        task1 = HTNNode(task_id="A", description="Task A")
        task2 = HTNNode(task_id="B", description="Task B")
        parent = HTNNode(
            task_id="parent",
            description="Sequential tasks",
            subtasks=[task1, task2]
        )
        
        result = translator_sequential.translate(parent)
        
        assert isinstance(result, Composition)
        # Composition is right-to-left: B ∘ A (executes A then B)
        assert isinstance(result.left, Literal)
        assert result.left.value == "B"
        assert isinstance(result.right, Literal)
        assert result.right.value == "A"

    def test_translate_three_sequential_tasks(self, translator_sequential):
        """Test three sequential tasks create nested Composition."""
        task1 = HTNNode(task_id="A", description="Task A")
        task2 = HTNNode(task_id="B", description="Task B")
        task3 = HTNNode(task_id="C", description="Task C")
        parent = HTNNode(
            task_id="parent",
            description="Three tasks",
            subtasks=[task1, task2, task3]
        )
        
        result = translator_sequential.translate(parent)
        
        # Should be: C ∘ (B ∘ A) - executes A, B, C
        assert isinstance(result, Composition)
        assert isinstance(result.left, Literal)
        assert result.left.value == "C"
        assert isinstance(result.right, Composition)
        assert result.right.left.value == "B"
        assert result.right.right.value == "A"

    def test_execution_order_sequential(self, translator_sequential):
        """Test execution order extraction for sequential composition."""
        task1 = HTNNode(task_id="first", description="First")
        task2 = HTNNode(task_id="second", description="Second")
        task3 = HTNNode(task_id="third", description="Third")
        parent = HTNNode(
            task_id="parent",
            description="Ordered tasks",
            subtasks=[task1, task2, task3]
        )
        
        result = translator_sequential.translate(parent)
        order = translator_sequential.get_task_execution_order(result)
        
        assert order == ["first", "second", "third"]


class TestParallelizationDetection:
    """Tests for automatic parallel execution detection."""

    def test_detect_independent_tasks(self, translator):
        """Test independent tasks (no dependencies) are parallelized."""
        # Two tasks with no preconditions/effects - fully independent
        task1 = HTNNode(task_id="A", description="Task A")
        task2 = HTNNode(task_id="B", description="Task B")
        parent = HTNNode(
            task_id="parent",
            description="Independent tasks",
            subtasks=[task1, task2]
        )
        
        result = translator.translate(parent)
        
        # Should use Product for parallel execution
        assert isinstance(result, Product)
        assert isinstance(result.left, Literal)
        assert isinstance(result.right, Literal)

    def test_detect_dependent_tasks_via_effects(self, translator):
        """Test tasks with precondition/effect dependencies remain sequential."""
        # Task A produces "code_ready", Task B requires "code_ready"
        task1 = HTNNode(
            task_id="A",
            description="Write code",
            effects={"code_ready": True}
        )
        task2 = HTNNode(
            task_id="B",
            description="Test code",
            preconditions={"code_ready": True}
        )
        parent = HTNNode(
            task_id="parent",
            description="Dependent tasks",
            subtasks=[task1, task2]
        )
        
        result = translator.translate(parent)
        
        # Should use Composition for sequential execution
        assert isinstance(result, Composition)
        # B ∘ A (A executes first, then B)
        assert result.right.value == "A"
        assert result.left.value == "B"

    def test_mixed_parallel_and_sequential(self, translator):
        """Test mixed structure: some parallel, some sequential."""
        # A and B are independent, C depends on A
        task_a = HTNNode(
            task_id="A",
            description="Task A",
            effects={"a_done": True}
        )
        task_b = HTNNode(
            task_id="B",
            description="Task B (independent)"
        )
        task_c = HTNNode(
            task_id="C",
            description="Task C (depends on A)",
            preconditions={"a_done": True}
        )
        parent = HTNNode(
            task_id="parent",
            description="Mixed tasks",
            subtasks=[task_a, task_b, task_c]
        )
        
        result = translator.translate(parent)
        
        # Should be: C ∘ (A × B) - A and B parallel, then C
        assert isinstance(result, Composition)
        assert isinstance(result.right, Product)  # A × B
        assert isinstance(result.left, Literal)  # C
        assert result.left.value == "C"

    def test_three_independent_tasks_parallelized(self, translator):
        """Test three independent tasks all parallelized."""
        task1 = HTNNode(task_id="A", description="Task A")
        task2 = HTNNode(task_id="B", description="Task B")
        task3 = HTNNode(task_id="C", description="Task C")
        parent = HTNNode(
            task_id="parent",
            description="Three independent",
            subtasks=[task1, task2, task3]
        )
        
        result = translator.translate(parent)
        
        # Should be nested Product: (A × B) × C
        assert isinstance(result, Product)


class TestProductGeneration:
    """Tests for parallel product generation."""

    def test_build_parallel_product_two_tasks(self, translator):
        """Test building Product from two expressions."""
        expr1 = Literal("A")
        expr2 = Literal("B")
        
        result = translator._build_parallel_product([expr1, expr2])
        
        assert isinstance(result, Product)
        assert result.left == expr1
        assert result.right == expr2

    def test_build_parallel_product_three_tasks(self, translator):
        """Test building nested Product from three expressions."""
        expr1 = Literal("A")
        expr2 = Literal("B")
        expr3 = Literal("C")
        
        result = translator._build_parallel_product([expr1, expr2, expr3])
        
        # Should be: (A × B) × C
        assert isinstance(result, Product)
        assert isinstance(result.left, Product)
        assert result.left.left == expr1
        assert result.left.right == expr2
        assert result.right == expr3

    def test_build_parallel_product_single_expression(self, translator):
        """Test single expression returns unwrapped."""
        expr = Literal("A")
        
        result = translator._build_parallel_product([expr])
        
        assert result == expr

    def test_build_parallel_product_empty_raises_error(self, translator):
        """Test empty expression list raises ValueError."""
        with pytest.raises(ValueError, match="Cannot create product of empty expression list"):
            translator._build_parallel_product([])


class TestNestedStructures:
    """Tests for complex nested HTN hierarchies."""

    def test_nested_compound_tasks(self, translator_sequential):
        """Test nested compound tasks create nested compositions."""
        # Inner compound: B, C
        inner_b = HTNNode(task_id="B", description="Task B")
        inner_c = HTNNode(task_id="C", description="Task C")
        inner_compound = HTNNode(
            task_id="inner",
            description="Inner compound",
            subtasks=[inner_b, inner_c]
        )
        
        # Outer compound: A, inner, D
        task_a = HTNNode(task_id="A", description="Task A")
        task_d = HTNNode(task_id="D", description="Task D")
        outer_compound = HTNNode(
            task_id="outer",
            description="Outer compound",
            subtasks=[task_a, inner_compound, task_d]
        )
        
        result = translator_sequential.translate(outer_compound)
        
        # Should be: D ∘ ((C ∘ B) ∘ A)
        assert isinstance(result, Composition)
        order = translator_sequential.get_task_execution_order(result)
        assert order == ["A", "B", "C", "D"]

    def test_deeply_nested_hierarchy(self, translator_sequential):
        """Test deeply nested HTN hierarchy (3 levels)."""
        # Level 3: E, F
        level3_e = HTNNode(task_id="E", description="Task E")
        level3_f = HTNNode(task_id="F", description="Task F")
        level3 = HTNNode(
            task_id="level3",
            description="Level 3",
            subtasks=[level3_e, level3_f]
        )

        # Level 2: C, D, level3
        level2_c = HTNNode(task_id="C", description="Task C")
        level2_d = HTNNode(task_id="D", description="Task D")
        level2 = HTNNode(
            task_id="level2",
            description="Level 2",
            subtasks=[level2_c, level2_d, level3]
        )

        # Level 1: A, B, level2
        level1_a = HTNNode(task_id="A", description="Task A")
        level1_b = HTNNode(task_id="B", description="Task B")
        level1 = HTNNode(
            task_id="level1",
            description="Level 1",
            subtasks=[level1_a, level1_b, level2]
        )

        result = translator_sequential.translate(level1)
        order = translator_sequential.get_task_execution_order(result)

        assert order == ["A", "B", "C", "D", "E", "F"]

    def test_nested_with_parallelization(self, translator):
        """Test nested structure with parallel detection."""
        # Inner: two independent tasks
        inner_a = HTNNode(task_id="A", description="Task A")
        inner_b = HTNNode(task_id="B", description="Task B")
        inner = HTNNode(
            task_id="inner",
            description="Inner parallel",
            subtasks=[inner_a, inner_b]
        )

        # Outer: C depends on inner (sequential)
        outer_c = HTNNode(
            task_id="C",
            description="Task C",
            preconditions={"inner_done": True}
        )
        # Add effect to inner to create dependency
        inner.effects = {"inner_done": True}

        outer = HTNNode(
            task_id="outer",
            description="Outer sequential",
            subtasks=[inner, outer_c]
        )

        result = translator.translate(outer)

        # Should be: C ∘ (A × B)
        assert isinstance(result, Composition)
        assert isinstance(result.right, Product)  # A × B
        assert result.left.value == "C"


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_subtasks_list(self, translator):
        """Test compound node with empty subtasks list returns primitive."""
        parent = HTNNode(
            task_id="parent",
            description="Empty parent",
            subtasks=[]
        )

        # Empty subtasks means it's a primitive node
        result = translator.translate(parent)
        assert isinstance(result, Literal)
        assert result.value == "parent"

    def test_sequential_composition_empty_raises_error(self, translator):
        """Test building sequential composition with empty list raises error."""
        with pytest.raises(ValueError, match="Cannot compose empty expression list"):
            translator._build_sequential_composition([])

    def test_parallelization_disabled_forces_sequential(self, translator_sequential):
        """Test disabling parallelization forces sequential execution."""
        # Two independent tasks
        task1 = HTNNode(task_id="A", description="Task A")
        task2 = HTNNode(task_id="B", description="Task B")
        parent = HTNNode(
            task_id="parent",
            description="Should be sequential",
            subtasks=[task1, task2]
        )

        result = translator_sequential.translate(parent)

        # Should use Composition, not Product
        assert isinstance(result, Composition)
        assert not isinstance(result, Product)

    def test_circular_dependency_handling(self, translator):
        """Test circular dependencies fall back to sequential."""
        # A depends on B, B depends on A (circular)
        task_a = HTNNode(
            task_id="A",
            description="Task A",
            preconditions={"b_done": True},
            effects={"a_done": True}
        )
        task_b = HTNNode(
            task_id="B",
            description="Task B",
            preconditions={"a_done": True},
            effects={"b_done": True}
        )
        parent = HTNNode(
            task_id="parent",
            description="Circular deps",
            subtasks=[task_a, task_b]
        )

        # Should handle gracefully (sequential fallback)
        result = translator.translate(parent)
        assert isinstance(result, ASTNode)  # Should not crash

    def test_single_task_in_group(self, translator):
        """Test grouping single task returns single-element list."""
        task = HTNNode(task_id="A", description="Single task")

        groups = translator._group_parallelizable_tasks([task])

        assert len(groups) == 1
        assert len(groups[0]) == 1
        assert groups[0][0] == task

    def test_empty_task_list_grouping(self, translator):
        """Test grouping empty task list returns empty list."""
        groups = translator._group_parallelizable_tasks([])

        assert groups == [[]]


class TestPreconditionEffectAnalysis:
    """Tests for precondition/effect dependency analysis."""

    def test_has_state_dependency_true(self, translator):
        """Test detecting state dependency between tasks."""
        task1 = HTNNode(
            task_id="A",
            description="Produces state",
            effects={"state_x": True}
        )
        task2 = HTNNode(
            task_id="B",
            description="Requires state",
            preconditions={"state_x": True}
        )

        has_dep = translator._has_state_dependency(task1, task2)

        assert has_dep is True

    def test_has_state_dependency_false(self, translator):
        """Test no dependency when effects/preconditions don't overlap."""
        task1 = HTNNode(
            task_id="A",
            description="Produces state_x",
            effects={"state_x": True}
        )
        task2 = HTNNode(
            task_id="B",
            description="Requires state_y",
            preconditions={"state_y": True}
        )

        has_dep = translator._has_state_dependency(task1, task2)

        assert has_dep is False

    def test_has_state_dependency_no_preconditions(self, translator):
        """Test no dependency when task has no preconditions."""
        task1 = HTNNode(
            task_id="A",
            description="Produces state",
            effects={"state_x": True}
        )
        task2 = HTNNode(
            task_id="B",
            description="No preconditions"
        )

        has_dep = translator._has_state_dependency(task1, task2)

        assert has_dep is False

    def test_has_state_dependency_no_effects(self, translator):
        """Test no dependency when task has no effects."""
        task1 = HTNNode(
            task_id="A",
            description="No effects"
        )
        task2 = HTNNode(
            task_id="B",
            description="Has preconditions",
            preconditions={"state_x": True}
        )

        has_dep = translator._has_state_dependency(task1, task2)

        assert has_dep is False

    def test_multiple_overlapping_states(self, translator):
        """Test dependency with multiple overlapping states."""
        task1 = HTNNode(
            task_id="A",
            description="Produces multiple states",
            effects={"state_x": True, "state_y": True, "state_z": True}
        )
        task2 = HTNNode(
            task_id="B",
            description="Requires one overlapping state",
            preconditions={"state_y": True, "other_state": True}
        )

        has_dep = translator._has_state_dependency(task1, task2)

        assert has_dep is True

    def test_complex_dependency_chain(self, translator):
        """Test complex dependency chain: A → B → C."""
        task_a = HTNNode(
            task_id="A",
            description="First task",
            effects={"step1": True}
        )
        task_b = HTNNode(
            task_id="B",
            description="Second task",
            preconditions={"step1": True},
            effects={"step2": True}
        )
        task_c = HTNNode(
            task_id="C",
            description="Third task",
            preconditions={"step2": True}
        )
        parent = HTNNode(
            task_id="parent",
            description="Dependency chain",
            subtasks=[task_a, task_b, task_c]
        )

        result = translator.translate(parent)
        order = translator.get_task_execution_order(result)

        # Should execute in order: A, B, C
        assert order == ["A", "B", "C"]


class TestExecutionOrderExtraction:
    """Tests for execution order extraction utility."""

    def test_execution_order_literal(self, translator):
        """Test execution order for single Literal."""
        literal = Literal("task")

        order = translator.get_task_execution_order(literal)

        assert order == ["task"]

    def test_execution_order_composition(self, translator):
        """Test execution order for Composition."""
        comp = Composition(left=Literal("B"), right=Literal("A"))

        order = translator.get_task_execution_order(comp)

        # Composition is right-to-left: A then B
        assert order == ["A", "B"]

    def test_execution_order_product(self, translator):
        """Test execution order for Product (parallel)."""
        prod = Product(left=Literal("A"), right=Literal("B"))

        order = translator.get_task_execution_order(prod)

        # Product returns left then right (order doesn't matter for parallel)
        assert order == ["A", "B"]

    def test_execution_order_nested_composition(self, translator):
        """Test execution order for nested Composition."""
        inner = Composition(left=Literal("B"), right=Literal("A"))
        outer = Composition(left=Literal("C"), right=inner)

        order = translator.get_task_execution_order(outer)

        assert order == ["A", "B", "C"]

    def test_execution_order_mixed_structure(self, translator):
        """Test execution order for mixed Composition and Product."""
        prod = Product(left=Literal("A"), right=Literal("B"))
        comp = Composition(left=Literal("C"), right=prod)

        order = translator.get_task_execution_order(comp)

        # Product (A, B) then C
        assert order == ["A", "B", "C"]


class TestGroupParallelizableTasks:
    """Tests for task grouping algorithm."""

    def test_group_all_independent(self, translator):
        """Test grouping all independent tasks into single group."""
        task1 = HTNNode(task_id="A", description="Task A")
        task2 = HTNNode(task_id="B", description="Task B")
        task3 = HTNNode(task_id="C", description="Task C")

        groups = translator._group_parallelizable_tasks([task1, task2, task3])

        # All independent: single group
        assert len(groups) == 1
        assert len(groups[0]) == 3

    def test_group_sequential_dependencies(self, translator):
        """Test grouping tasks with sequential dependencies."""
        task1 = HTNNode(
            task_id="A",
            description="Task A",
            effects={"step1": True}
        )
        task2 = HTNNode(
            task_id="B",
            description="Task B",
            preconditions={"step1": True},
            effects={"step2": True}
        )
        task3 = HTNNode(
            task_id="C",
            description="Task C",
            preconditions={"step2": True}
        )

        groups = translator._group_parallelizable_tasks([task1, task2, task3])

        # Should be three sequential groups: [A], [B], [C]
        assert len(groups) == 3
        assert len(groups[0]) == 1
        assert groups[0][0].task_id == "A"
        assert groups[1][0].task_id == "B"
        assert groups[2][0].task_id == "C"

    def test_group_partial_parallelism(self, translator):
        """Test grouping with partial parallelism."""
        task_a = HTNNode(
            task_id="A",
            description="Task A",
            effects={"a_done": True}
        )
        task_b = HTNNode(task_id="B", description="Task B (independent)")
        task_c = HTNNode(
            task_id="C",
            description="Task C (depends on A)",
            preconditions={"a_done": True}
        )

        groups = translator._group_parallelizable_tasks([task_a, task_b, task_c])

        # Should be: [A, B] (parallel), then [C]
        assert len(groups) == 2
        assert len(groups[0]) == 2  # A and B
        assert len(groups[1]) == 1  # C
        assert groups[1][0].task_id == "C"

