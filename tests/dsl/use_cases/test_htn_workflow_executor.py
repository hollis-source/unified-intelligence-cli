"""Tests for HTNWorkflowExecutor - Enhanced with graph validation.

Tests cover:
- Graph validation in DECOMPOSE phase
- Cycle detection and early failure
- Graph metadata in lifecycle
- Backward compatibility with Sprint 2
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
from src.dsl.use_cases.htn_workflow_executor import HTNWorkflowExecutor
from src.entity.htn import HTNNode
from src.entity.graph import Graph
from src.entity.lifecycle import LifecycleState


@pytest.fixture
def mock_task_executor():
    """Create mock task executor."""
    executor = Mock()
    executor.execute_task = AsyncMock(return_value="task completed")
    return executor


@pytest.fixture
def mock_parser():
    """Create mock parser."""
    parser = Mock()
    return parser


@pytest.fixture
def htn_executor(mock_task_executor, mock_parser):
    """Create HTNWorkflowExecutor with mocks."""
    return HTNWorkflowExecutor(task_executor=mock_task_executor, parser=mock_parser)


def mock_interpreter():
    """Create a properly mocked Interpreter with async execute."""
    interpreter = Mock()
    interpreter.execute = AsyncMock(return_value="execution result")
    interpreter.set_symbol_table = Mock()
    return interpreter


class TestGraphIntegration:
    """Tests for GraphWorkflowExecutor integration."""

    def test_initialization_creates_graph_executor(self, htn_executor):
        """Test HTNWorkflowExecutor initializes with GraphWorkflowExecutor."""
        assert hasattr(htn_executor, 'graph_executor')
        assert htn_executor.graph_executor is not None
        # Graph executor should use same task executor
        assert htn_executor.graph_executor.task_executor == htn_executor.task_executor

    def test_graph_executor_initialized_with_task_executor(self, mock_task_executor, mock_parser):
        """Test graph executor receives task executor."""
        executor = HTNWorkflowExecutor(task_executor=mock_task_executor, parser=mock_parser)
        assert executor.graph_executor.task_executor == mock_task_executor


class TestGraphValidationInDecompose:
    """Tests for graph validation in DECOMPOSE phase."""

    @pytest.mark.asyncio
    async def test_decompose_phase_creates_graph(self, htn_executor, tmp_path):
        """Test DECOMPOSE phase converts HTN to graph."""
        # Create simple workflow file
        workflow_file = tmp_path / "test.ct"
        workflow_file.write_text("task build: Execute build")

        # Mock dependencies
        with patch.object(htn_executor, '_read_workflow_file', return_value="task build: Execute build"):
            with patch.object(htn_executor, '_parse_workflow') as mock_parse:
                # Create mock AST
                mock_ast = Mock()
                mock_parse.return_value = mock_ast

                with patch.object(htn_executor, '_extract_symbol_table', return_value={}):
                    with patch.object(htn_executor, '_validate_workflow') as mock_validate:
                        mock_validation = Mock(is_valid=True, checks=[], issues=[])
                        mock_validate.return_value = mock_validation

                        with patch.object(htn_executor, '_get_main_node') as mock_get_main:
                            # Create mock HTN node
                            mock_htn = HTNNode(task_id="build", description="Execute build")

                            with patch.object(htn_executor.htn_compiler, 'compile', return_value=mock_htn):
                                with patch.object(htn_executor.graph_executor, 'htn_to_graph') as mock_htn_to_graph:
                                    # Create mock graph
                                    mock_graph = Graph()
                                    mock_graph.add_node("build")
                                    mock_htn_to_graph.return_value = mock_graph

                                    with patch.object(htn_executor.graph_executor, 'validate_dag', return_value=[]):
                                        with patch('src.dsl.use_cases.htn_workflow_executor.Interpreter', return_value=mock_interpreter()):
                                            # Execute workflow
                                            result = await htn_executor.execute_workflow(str(workflow_file))

                                            # Verify graph was created and validated
                                            assert mock_htn_to_graph.called
                                            assert htn_executor.graph_executor.validate_dag.called

                                            # Verify result success
                                            assert result.success == True

    @pytest.mark.asyncio
    async def test_decompose_stores_graph_in_lifecycle(self, htn_executor, tmp_path):
        """Test graph is stored in lifecycle decomposed_units."""
        workflow_file = tmp_path / "test.ct"
        workflow_file.write_text("task build: Execute build")

        # Mock dependencies
        with patch.object(htn_executor, '_read_workflow_file', return_value="task build: Execute build"):
            with patch.object(htn_executor, '_parse_workflow', return_value=Mock()):
                with patch.object(htn_executor, '_extract_symbol_table', return_value={}):
                    with patch.object(htn_executor, '_validate_workflow') as mock_validate:
                        mock_validation = Mock(is_valid=True, checks=[], issues=[])
                        mock_validate.return_value = mock_validation

                        with patch.object(htn_executor, '_get_main_node', return_value=Mock()):
                            mock_htn = HTNNode(task_id="build", description="Execute build")

                            with patch.object(htn_executor.htn_compiler, 'compile', return_value=mock_htn):
                                mock_graph = Graph()
                                mock_graph.add_node("build")

                                with patch.object(htn_executor.graph_executor, 'htn_to_graph', return_value=mock_graph):
                                    with patch.object(htn_executor.graph_executor, 'validate_dag', return_value=[]):
                                        with patch('src.dsl.use_cases.htn_workflow_executor.Interpreter', return_value=mock_interpreter()):
                                            # Execute workflow
                                            result = await htn_executor.execute_workflow(str(workflow_file))

                                            # Verify graph in lifecycle
                                            assert result.lifecycle is not None
                                            decomposed_units = result.lifecycle.get_state_data(LifecycleState.DECOMPOSE)
                                            assert decomposed_units is not None
                                            assert "graph" in decomposed_units
                                            assert decomposed_units["graph"] == mock_graph


class TestCycleDetection:
    """Tests for cycle detection and failure."""

    @pytest.mark.asyncio
    async def test_cycle_detection_fails_workflow(self, htn_executor, tmp_path):
        """Test workflow fails when graph contains cycles."""
        workflow_file = tmp_path / "cycle.ct"
        workflow_file.write_text("task cycle: Cyclic task")

        # Mock dependencies
        with patch.object(htn_executor, '_read_workflow_file', return_value="task cycle: Cyclic task"):
            with patch.object(htn_executor, '_parse_workflow', return_value=Mock()):
                with patch.object(htn_executor, '_extract_symbol_table', return_value={}):
                    with patch.object(htn_executor, '_validate_workflow') as mock_validate:
                        mock_validation = Mock(is_valid=True, checks=[], issues=[])
                        mock_validate.return_value = mock_validation

                        with patch.object(htn_executor, '_get_main_node', return_value=Mock()):
                            mock_htn = HTNNode(task_id="cycle", description="Cyclic task")

                            with patch.object(htn_executor.htn_compiler, 'compile', return_value=mock_htn):
                                # Create graph with cycle
                                mock_graph = Graph()
                                mock_graph.add_node("A")
                                mock_graph.add_node("B")
                                mock_graph.add_edge("A", "B")
                                mock_graph.add_edge("B", "A")  # Creates cycle

                                with patch.object(htn_executor.graph_executor, 'htn_to_graph', return_value=mock_graph):
                                    with patch.object(htn_executor.graph_executor, 'validate_dag') as mock_validate_dag:
                                        # Mock validation to return cycle issue
                                        mock_validate_dag.return_value = ["Workflow contains circular dependencies (cycle detected)"]

                                        # Execute workflow
                                        result = await htn_executor.execute_workflow(str(workflow_file))

                                        # Verify failure
                                        assert result.success == False
                                        assert "Graph validation failed" in result.error
                                        assert "circular" in result.error.lower()

                                        # Verify lifecycle failed
                                        assert result.lifecycle.current_state == LifecycleState.FAILED

    @pytest.mark.asyncio
    async def test_cycle_detection_includes_decompose_phase(self, htn_executor, tmp_path):
        """Test DECOMPOSE phase is marked complete even when cycle detected."""
        workflow_file = tmp_path / "cycle.ct"
        workflow_file.write_text("task cycle: Cyclic task")

        # Mock dependencies
        with patch.object(htn_executor, '_read_workflow_file', return_value="task cycle: Cyclic task"):
            with patch.object(htn_executor, '_parse_workflow', return_value=Mock()):
                with patch.object(htn_executor, '_extract_symbol_table', return_value={}):
                    with patch.object(htn_executor, '_validate_workflow') as mock_validate:
                        mock_validation = Mock(is_valid=True, checks=[], issues=[])
                        mock_validate.return_value = mock_validation

                        with patch.object(htn_executor, '_get_main_node', return_value=Mock()):
                            mock_htn = HTNNode(task_id="cycle", description="Cyclic task")

                            with patch.object(htn_executor.htn_compiler, 'compile', return_value=mock_htn):
                                mock_graph = Graph()
                                mock_graph.add_node("A")
                                mock_graph.add_node("B")
                                mock_graph.add_edge("A", "B")
                                mock_graph.add_edge("B", "A")

                                with patch.object(htn_executor.graph_executor, 'htn_to_graph', return_value=mock_graph):
                                    with patch.object(htn_executor.graph_executor, 'validate_dag') as mock_validate_dag:
                                        mock_validate_dag.return_value = ["Cycle detected"]

                                        # Execute workflow
                                        result = await htn_executor.execute_workflow(str(workflow_file))

                                        # Verify DECOMPOSE phase was completed
                                        assert "DECOMPOSE" in result.phases_completed


class TestVerboseOutput:
    """Tests for verbose graph output."""

    @pytest.mark.asyncio
    async def test_verbose_output_includes_graph_stats(self, htn_executor, tmp_path, capsys):
        """Test verbose mode prints graph statistics."""
        workflow_file = tmp_path / "test.ct"
        workflow_file.write_text("task build: Execute build")

        # Mock dependencies
        with patch.object(htn_executor, '_read_workflow_file', return_value="task build: Execute build"):
            with patch.object(htn_executor, '_parse_workflow', return_value=Mock()):
                with patch.object(htn_executor, '_extract_symbol_table', return_value={}):
                    with patch.object(htn_executor, '_validate_workflow') as mock_validate:
                        mock_validation = Mock(is_valid=True, checks=[], issues=[])
                        mock_validate.return_value = mock_validation

                        with patch.object(htn_executor, '_get_main_node', return_value=Mock()):
                            mock_htn = HTNNode(task_id="build", description="Execute build")

                            with patch.object(htn_executor.htn_compiler, 'compile', return_value=mock_htn):
                                # Create graph with 2 nodes and 1 edge
                                mock_graph = Graph()
                                mock_graph.add_node("build")
                                mock_graph.add_node("test")
                                mock_graph.add_edge("build", "test")

                                with patch.object(htn_executor.graph_executor, 'htn_to_graph', return_value=mock_graph):
                                    with patch.object(htn_executor.graph_executor, 'validate_dag', return_value=[]):
                                        with patch('src.dsl.use_cases.htn_workflow_executor.Interpreter', return_value=mock_interpreter()):
                                            # Execute workflow with verbose
                                            await htn_executor.execute_workflow(str(workflow_file), verbose=True)

                                            # Capture output
                                            captured = capsys.readouterr()

                                            # Verify graph stats in output
                                            assert "Graph:" in captured.out
                                            assert "nodes" in captured.out
                                            assert "edges" in captured.out
                                            assert "DAG validated" in captured.out


class TestBackwardCompatibility:
    """Tests for backward compatibility with Sprint 2."""

    @pytest.mark.asyncio
    async def test_htn_functionality_preserved(self, htn_executor, tmp_path):
        """Test HTN decomposition still works with graph validation."""
        workflow_file = tmp_path / "test.ct"
        workflow_file.write_text("task build: Execute build")

        # Mock dependencies
        with patch.object(htn_executor, '_read_workflow_file', return_value="task build: Execute build"):
            with patch.object(htn_executor, '_parse_workflow', return_value=Mock()):
                with patch.object(htn_executor, '_extract_symbol_table', return_value={}):
                    with patch.object(htn_executor, '_validate_workflow') as mock_validate:
                        mock_validation = Mock(is_valid=True, checks=[], issues=[])
                        mock_validate.return_value = mock_validation

                        with patch.object(htn_executor, '_get_main_node', return_value=Mock()):
                            mock_htn = HTNNode(task_id="build", description="Execute build")

                            with patch.object(htn_executor.htn_compiler, 'compile', return_value=mock_htn):
                                mock_graph = Graph()
                                mock_graph.add_node("build")

                                with patch.object(htn_executor.graph_executor, 'htn_to_graph', return_value=mock_graph):
                                    with patch.object(htn_executor.graph_executor, 'validate_dag', return_value=[]):
                                        with patch('src.dsl.use_cases.htn_workflow_executor.Interpreter', return_value=mock_interpreter()):
                                            # Execute workflow
                                            result = await htn_executor.execute_workflow(str(workflow_file))

                                            # Verify HTN data still present
                                            decomposed_units = result.lifecycle.get_state_data(LifecycleState.DECOMPOSE)
                                            assert "htn_root" in decomposed_units
                                            assert "htn_decomposed" in decomposed_units
                                            assert "htn_depth" in decomposed_units
                                            assert "task_count" in decomposed_units

    @pytest.mark.asyncio
    async def test_result_structure_unchanged(self, htn_executor, tmp_path):
        """Test WorkflowExecutionResult structure unchanged."""
        workflow_file = tmp_path / "test.ct"
        workflow_file.write_text("task build: Execute build")

        # Mock dependencies
        with patch.object(htn_executor, '_read_workflow_file', return_value="task build: Execute build"):
            with patch.object(htn_executor, '_parse_workflow', return_value=Mock()):
                with patch.object(htn_executor, '_extract_symbol_table', return_value={}):
                    with patch.object(htn_executor, '_validate_workflow') as mock_validate:
                        mock_validation = Mock(is_valid=True, checks=[], issues=[])
                        mock_validate.return_value = mock_validation

                        with patch.object(htn_executor, '_get_main_node', return_value=Mock()):
                            mock_htn = HTNNode(task_id="build", description="Execute build")

                            with patch.object(htn_executor.htn_compiler, 'compile', return_value=mock_htn):
                                mock_graph = Graph()
                                mock_graph.add_node("build")

                                with patch.object(htn_executor.graph_executor, 'htn_to_graph', return_value=mock_graph):
                                    with patch.object(htn_executor.graph_executor, 'validate_dag', return_value=[]):
                                        with patch('src.dsl.use_cases.htn_workflow_executor.Interpreter', return_value=mock_interpreter()):
                                            # Execute workflow
                                            result = await htn_executor.execute_workflow(str(workflow_file))

                                            # Verify result structure
                                            assert hasattr(result, 'success')
                                            assert hasattr(result, 'result')
                                            assert hasattr(result, 'lifecycle')
                                            assert hasattr(result, 'execution_time')
                                            assert hasattr(result, 'phases_completed')
                                            assert hasattr(result, 'error')
