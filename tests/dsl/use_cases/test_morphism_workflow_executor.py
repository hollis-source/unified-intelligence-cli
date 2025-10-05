"""Tests for MorphismWorkflowExecutor - HTN executor with morphism transformations.

Tests verify:
- Morphism transformation application during workflow execution
- Semantic preservation verification
- Lifecycle phase tracking with transformations
- Error handling for invalid transformations
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from pathlib import Path

from src.dsl.use_cases.morphism_workflow_executor import MorphismWorkflowExecutor
from src.entities.category_theory.workflow_morphism import WorkflowMorphism
from src.entities.htn import HTNNode
from src.dsl.adapters.parser import Parser


@pytest.fixture
def mock_task_executor():
    """Create mock task executor."""
    executor = Mock()
    executor.execute_task = AsyncMock(return_value={"status": "success"})
    return executor


@pytest.fixture
def morphism_executor(mock_task_executor):
    """Create MorphismWorkflowExecutor with mock dependencies."""
    parser = Parser()
    return MorphismWorkflowExecutor(
        task_executor=mock_task_executor,
        parser=parser
    )


@pytest.fixture
def morphism_executor_with_transformations(mock_task_executor):
    """Create MorphismWorkflowExecutor with transformations."""
    parser = Parser()
    return MorphismWorkflowExecutor(
        task_executor=mock_task_executor,
        parser=parser,
        transformations=[
            WorkflowMorphism.htn_flatten(),
            WorkflowMorphism.htn_remove_identity(),
            WorkflowMorphism.htn_simplify()
        ]
    )


@pytest.fixture
def simple_workflow_file(tmp_path):
    """Create a simple workflow file."""
    workflow = tmp_path / "simple.ct"
    workflow.write_text("""
        functor build = python_specialist
        functor test = unit_test_engineer
        functor main = test o build
    """)
    return str(workflow)


@pytest.fixture
def nested_workflow_file(tmp_path):
    """Create a workflow with nested composition."""
    workflow = tmp_path / "nested.ct"
    workflow.write_text("""
        functor a = task_a
        functor b = task_b
        functor c = task_c
        functor comp1 = b o a
        functor comp2 = c o comp1
        functor main = comp2
    """)
    return str(workflow)


@pytest.fixture
def workflow_with_identity(tmp_path):
    """Create workflow with identity nodes."""
    workflow = tmp_path / "with_identity.ct"
    workflow.write_text("""
        functor task = real_task
        functor id_1 = identity
        functor main = task o id_1
    """)
    return str(workflow)


class TestMorphismWorkflowExecutorInit:
    """Test executor initialization."""

    def test_init_without_transformations(self, mock_task_executor):
        """Executor initializes with empty transformations list."""
        executor = MorphismWorkflowExecutor(task_executor=mock_task_executor)

        assert executor.transformations == []
        assert executor.task_executor == mock_task_executor

    def test_init_with_transformations(self, mock_task_executor):
        """Executor initializes with provided transformations."""
        transformations = [
            WorkflowMorphism.htn_flatten(),
            WorkflowMorphism.htn_simplify()
        ]
        executor = MorphismWorkflowExecutor(
            task_executor=mock_task_executor,
            transformations=transformations
        )

        assert len(executor.transformations) == 2
        assert executor.transformations == transformations


class TestTransformationApplication:
    """Test morphism transformation application."""

    @pytest.mark.asyncio
    async def test_execute_without_transformations(self, morphism_executor, simple_workflow_file):
        """Workflow executes without transformations (backward compatible)."""
        result = await morphism_executor.execute_workflow(simple_workflow_file)

        assert result.success is True
        assert "PLAN" in result.phases_completed
        assert "VERIFY" in result.phases_completed
        assert "DECOMPOSE" in result.phases_completed
        assert "EXECUTE" in result.phases_completed

    @pytest.mark.asyncio
    async def test_execute_with_transformations(
        self,
        morphism_executor_with_transformations,
        nested_workflow_file
    ):
        """Workflow executes with morphism transformations applied."""
        result = await morphism_executor_with_transformations.execute_workflow(
            nested_workflow_file
        )

        assert result.success is True
        assert "DECOMPOSE" in result.phases_completed

        # Check lifecycle tracking
        from src.entities.lifecycle.lifecycle import LifecycleState
        decompose_data = result.lifecycle.state_data.get(LifecycleState.DECOMPOSE, {})
        assert decompose_data.get("transformations_applied") == 3

    @pytest.mark.asyncio
    async def test_transformation_preserves_tasks(
        self,
        morphism_executor_with_transformations,
        nested_workflow_file
    ):
        """Transformations preserve task structure."""
        result = await morphism_executor_with_transformations.execute_workflow(
            nested_workflow_file
        )

        assert result.success is True
        from src.entities.lifecycle.lifecycle import LifecycleState
        decompose_data = result.lifecycle.state_data.get(LifecycleState.DECOMPOSE, {})

        # HTN should be decomposed successfully
        assert "htn_decomposed" in decompose_data
        assert decompose_data["task_count"] > 0

    @pytest.mark.asyncio
    async def test_verbose_output_shows_transformations(
        self,
        morphism_executor_with_transformations,
        nested_workflow_file,
        capsys
    ):
        """Verbose mode shows transformation application."""
        result = await morphism_executor_with_transformations.execute_workflow(
            nested_workflow_file,
            verbose=True
        )

        captured = capsys.readouterr()

        # Should show morphism application
        assert "Morphisms" in captured.out or "transformation" in captured.out.lower()


class TestTransformationMethods:
    """Test internal transformation methods."""

    def test_apply_single_transformation(self, morphism_executor):
        """Apply single transformation correctly."""
        htn = HTNNode(
            task_id="comp",
            description="nested",
            subtasks=[
                HTNNode(
                    task_id="inner",
                    description="inner comp",
                    subtasks=[
                        HTNNode(task_id="a", description="task_a"),
                        HTNNode(task_id="b", description="task_b")
                    ],
                    metadata={"operator": "∘"}
                ),
                HTNNode(task_id="c", description="task_c")
            ],
            metadata={"operator": "∘"}
        )

        morphism_executor.transformations = [WorkflowMorphism.htn_flatten()]
        result = morphism_executor._apply_transformations(htn)

        # Should be flattened
        assert result.metadata.get("flattened") is True

    def test_apply_multiple_transformations(self, morphism_executor):
        """Apply multiple transformations via composition."""
        htn = HTNNode(
            task_id="comp",
            description="complex",
            subtasks=[
                HTNNode(task_id="a", description="task_a"),
                HTNNode(task_id="id_x", description="identity"),
                HTNNode(task_id="b", description="task_b")
            ],
            metadata={"operator": "∘"}
        )

        morphism_executor.transformations = [
            WorkflowMorphism.htn_flatten(),
            WorkflowMorphism.htn_remove_identity()
        ]

        result = morphism_executor._apply_transformations(htn)

        # Identity should be removed
        task_ids = morphism_executor._extract_task_ids(result)
        assert "id_x" not in task_ids or len([t for t in task_ids if t.startswith("id_")]) == 0

    def test_apply_no_transformations(self, morphism_executor):
        """No transformations returns original HTN."""
        htn = HTNNode(task_id="task", description="unchanged")

        morphism_executor.transformations = []
        result = morphism_executor._apply_transformations(htn)

        assert result.task_id == "task"
        assert result.description == "unchanged"


class TestSemanticPreservation:
    """Test semantic preservation verification."""

    def test_verify_identical_htns(self, morphism_executor):
        """Identical HTNs pass verification."""
        htn = HTNNode(
            task_id="task",
            description="same",
            subtasks=[
                HTNNode(task_id="a", description="task_a"),
                HTNNode(task_id="b", description="task_b")
            ]
        )

        assert morphism_executor._verify_transformation(htn, htn) is True

    def test_verify_flattened_htn(self, morphism_executor):
        """Flattened HTN preserves semantics."""
        original = HTNNode(
            task_id="comp",
            description="nested",
            subtasks=[
                HTNNode(
                    task_id="inner",
                    description="inner",
                    subtasks=[
                        HTNNode(task_id="a", description="task_a"),
                        HTNNode(task_id="b", description="task_b")
                    ],
                    metadata={"operator": "∘"}
                ),
                HTNNode(task_id="c", description="task_c")
            ],
            metadata={"operator": "∘"}
        )

        # Flatten
        flattened = HTNNode(
            task_id="comp",
            description="nested",
            subtasks=[
                HTNNode(task_id="a", description="task_a"),
                HTNNode(task_id="b", description="task_b"),
                HTNNode(task_id="c", description="task_c")
            ],
            metadata={"operator": "∘", "flattened": True}
        )

        assert morphism_executor._verify_transformation(original, flattened) is True

    def test_verify_identity_removed(self, morphism_executor):
        """Identity removal preserves semantics."""
        original = HTNNode(
            task_id="comp",
            description="with id",
            subtasks=[
                HTNNode(task_id="a", description="task_a"),
                HTNNode(task_id="id_x", description="identity")
            ],
            metadata={"operator": "∘"}
        )

        transformed = HTNNode(
            task_id="comp",
            description="without id",
            subtasks=[
                HTNNode(task_id="a", description="task_a")
            ],
            metadata={"operator": "∘"}
        )

        # Should pass - identity removed is valid
        assert morphism_executor._verify_transformation(original, transformed) is True

    def test_verify_tasks_removed_fails(self, morphism_executor):
        """Removing real tasks fails verification."""
        original = HTNNode(
            task_id="comp",
            description="original",
            subtasks=[
                HTNNode(task_id="a", description="task_a"),
                HTNNode(task_id="b", description="task_b")
            ]
        )

        transformed = HTNNode(
            task_id="comp",
            description="missing task",
            subtasks=[
                HTNNode(task_id="a", description="task_a")
            ]
        )

        # Should fail - task b removed
        assert morphism_executor._verify_transformation(original, transformed) is False


class TestUtilityMethods:
    """Test utility methods."""

    def test_count_primitive_tasks(self, morphism_executor):
        """Count primitive tasks correctly."""
        htn = HTNNode(
            task_id="comp",
            description="compound",
            subtasks=[
                HTNNode(task_id="a", description="task_a"),  # Primitive
                HTNNode(task_id="b", description="task_b"),  # Primitive
                HTNNode(
                    task_id="inner",
                    description="inner",
                    subtasks=[
                        HTNNode(task_id="c", description="task_c")  # Primitive
                    ]
                )
            ]
        )

        count = morphism_executor._count_primitive_tasks(htn)
        assert count == 3

    def test_count_excludes_identity(self, morphism_executor):
        """Identity tasks not counted as primitives."""
        htn = HTNNode(
            task_id="comp",
            description="with id",
            subtasks=[
                HTNNode(task_id="a", description="task_a"),
                HTNNode(task_id="id_x", description="identity")  # Not counted
            ]
        )

        count = morphism_executor._count_primitive_tasks(htn)
        assert count == 1

    def test_extract_task_ids(self, morphism_executor):
        """Extract all task IDs recursively."""
        htn = HTNNode(
            task_id="root",
            description="root",
            subtasks=[
                HTNNode(task_id="a", description="task_a"),
                HTNNode(
                    task_id="inner",
                    description="inner",
                    subtasks=[
                        HTNNode(task_id="b", description="task_b")
                    ]
                )
            ]
        )

        ids = morphism_executor._extract_task_ids(htn)
        assert ids == {"root", "a", "inner", "b"}


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_invalid_workflow_fails(self, morphism_executor_with_transformations, tmp_path):
        """Invalid workflow fails before transformation."""
        workflow = tmp_path / "invalid.ct"
        workflow.write_text("functor invalid")  # Missing assignment

        result = await morphism_executor_with_transformations.execute_workflow(
            str(workflow)
        )

        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_transformation_failure_tracked(
        self,
        morphism_executor_with_transformations,
        simple_workflow_file,
        monkeypatch
    ):
        """Transformation failure tracked in lifecycle."""
        # Mock verify to always fail
        def mock_verify(self, original, transformed):
            return False

        monkeypatch.setattr(
            MorphismWorkflowExecutor,
            "_verify_transformation",
            mock_verify
        )

        result = await morphism_executor_with_transformations.execute_workflow(
            simple_workflow_file
        )

        assert result.success is False
        assert "semantic" in result.error.lower() or "transformation" in result.error.lower()
        assert "DECOMPOSE" in result.phases_completed


class TestIntegration:
    """Integration tests with real transformations."""

    @pytest.mark.asyncio
    async def test_full_optimization_pipeline(
        self,
        mock_task_executor,
        tmp_path
    ):
        """Full optimization pipeline (flatten + remove_id + simplify)."""
        workflow = tmp_path / "optimize.ct"
        workflow.write_text("""
            functor a = task_a
            functor b = task_b
            functor c = task_c
            functor comp1 = b o a
            functor comp2 = c o comp1
            functor main = comp2
        """)

        executor = MorphismWorkflowExecutor(
            task_executor=mock_task_executor,
            transformations=[WorkflowMorphism.workflow_optimize()]
        )

        result = await executor.execute_workflow(str(workflow))

        assert result.success is True
        from src.entities.lifecycle.lifecycle import LifecycleState
        decompose_data = result.lifecycle.state_data.get(LifecycleState.DECOMPOSE, {})
        assert decompose_data.get("transformations_applied") == 1

    @pytest.mark.asyncio
    async def test_custom_transformation_pipeline(
        self,
        mock_task_executor,
        tmp_path
    ):
        """Custom transformation pipeline."""
        from src.entities.category_theory.workflow_morphism import create_transformation_pipeline

        workflow = tmp_path / "custom.ct"
        workflow.write_text("""
            functor build = python_specialist
            functor test = unit_test_engineer
            functor main = test o build
        """)

        pipeline = create_transformation_pipeline([
            "htn_flatten",
            "htn_simplify"
        ])

        executor = MorphismWorkflowExecutor(
            task_executor=mock_task_executor,
            transformations=[pipeline]
        )

        result = await executor.execute_workflow(str(workflow))

        assert result.success is True
