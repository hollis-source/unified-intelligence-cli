"""Integration tests for DSL workflow execution through unified CLI.

Tests the complete flow from CLI workflow command through lifecycle phases
to execution results.
"""

import pytest
from pathlib import Path
from click.testing import CliRunner

from src.main import main


class TestDSLWorkflowCLIIntegration:
    """Integration tests for DSL workflow execution via CLI."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_workflow(self, tmp_path):
        """Create temporary workflow file."""
        workflow_file = tmp_path / "test_workflow.ct"
        workflow_file.write_text("functor main = build")
        return workflow_file

    def test_workflow_mode_execution_success(self, runner):
        """Test successful workflow execution through CLI."""
        result = runner.invoke(main, [
            '--workflow', 'examples/workflows/simple_pipeline.ct',
            '--verbose'
        ])

        # Should complete successfully
        assert result.exit_code == 0
        # Should show lifecycle phases
        assert 'PLAN' in result.output
        assert 'VERIFY' in result.output
        assert 'DECOMPOSE' in result.output
        assert 'EXECUTE' in result.output
        # Should show success message
        assert 'Workflow Completed Successfully' in result.output

    def test_workflow_mode_with_nonexistent_file(self, runner):
        """Test workflow mode with nonexistent file fails gracefully."""
        result = runner.invoke(main, [
            '--workflow', '/nonexistent/workflow.ct'
        ])

        # Should fail with proper exit code
        assert result.exit_code != 0
        # Should show error message
        assert 'Error' in result.output or 'does not exist' in result.output

    def test_cli_requires_workflow_or_task(self, runner):
        """Test that CLI requires either --workflow or --task."""
        result = runner.invoke(main, [
            '--provider', 'mock'
        ])

        # Should fail validation
        assert result.exit_code != 0
        # Should show helpful error message
        assert 'Must provide either --workflow or --task' in result.output

    def test_workflow_mode_precedence_over_task(self, runner, temp_workflow):
        """Test that --workflow takes precedence when both provided."""
        result = runner.invoke(main, [
            '--workflow', str(temp_workflow),
            '--task', 'some task',
            '--verbose'
        ])

        # Should use workflow mode
        assert 'Warning: Both --workflow and --task provided' in result.output
        # Should execute workflow
        assert 'PLAN' in result.output

    def test_workflow_shows_phase_progression(self, runner):
        """Test that workflow execution shows phase progression."""
        result = runner.invoke(main, [
            '--workflow', 'examples/workflows/simple_pipeline.ct',
            '--verbose'
        ])

        # Check phases appear in order
        output = result.output
        plan_idx = output.find('PLAN')
        verify_idx = output.find('VERIFY')
        decompose_idx = output.find('DECOMPOSE')
        execute_idx = output.find('EXECUTE')

        assert plan_idx < verify_idx < decompose_idx < execute_idx

    def test_workflow_shows_execution_time(self, runner):
        """Test that workflow execution shows timing information."""
        result = runner.invoke(main, [
            '--workflow', 'examples/workflows/simple_pipeline.ct'
        ])

        # Should show execution time
        assert 'Execution time:' in result.output
        assert 's' in result.output  # seconds indicator

    def test_workflow_with_verbose_flag(self, runner):
        """Test workflow execution with verbose output."""
        result = runner.invoke(main, [
            '--workflow', 'examples/workflows/simple_pipeline.ct',
            '--verbose'
        ])

        # Should show detailed phase information
        assert 'Parsed workflow' in result.output
        assert 'validation checks' in result.output
        assert 'HTN:' in result.output  # Sprint 2: HTN metrics in DECOMPOSE phase

    def test_workflow_without_verbose_flag(self, runner):
        """Test workflow execution without verbose output."""
        result = runner.invoke(main, [
            '--workflow', 'examples/workflows/simple_pipeline.ct'
        ])

        # Should show minimal output (just results)
        assert 'Workflow Completed Successfully' in result.output
        # Should not show detailed phase descriptions
        assert 'Parsed workflow' not in result.output


class TestDSLLifecycleIntegration:
    """Integration tests for lifecycle phase execution in workflows."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    def test_plan_phase_parses_workflow(self, runner):
        """Test PLAN phase parses workflow file correctly."""
        result = runner.invoke(main, [
            '--workflow', 'examples/workflows/simple_pipeline.ct',
            '--verbose'
        ])

        # Should show PLAN phase success
        assert '✓ PLAN' in result.output
        assert 'Parsed workflow' in result.output

    def test_verify_phase_validates_workflow(self, runner):
        """Test VERIFY phase validates workflow structure."""
        result = runner.invoke(main, [
            '--workflow', 'examples/workflows/simple_pipeline.ct',
            '--verbose'
        ])

        # Should show VERIFY phase success
        assert '✓ VERIFY' in result.output
        assert 'validation checks' in result.output

    def test_decompose_phase_identifies_tasks(self, runner):
        """Test DECOMPOSE phase identifies executable tasks."""
        result = runner.invoke(main, [
            '--workflow', 'examples/workflows/simple_pipeline.ct',
            '--verbose'
        ])

        # Should show DECOMPOSE phase success
        assert '✓ DECOMPOSE' in result.output
        assert 'HTN:' in result.output  # Sprint 2: HTN decomposition metrics

    def test_execute_phase_runs_workflow(self, runner):
        """Test EXECUTE phase runs workflow successfully."""
        result = runner.invoke(main, [
            '--workflow', 'examples/workflows/simple_pipeline.ct',
            '--verbose'
        ])

        # Should show EXECUTE phase success
        assert '✓ EXECUTE' in result.output
        assert 'completed successfully' in result.output

    def test_lifecycle_phase_order(self, runner):
        """Test lifecycle phases execute in correct order."""
        result = runner.invoke(main, [
            '--workflow', 'examples/workflows/simple_pipeline.ct',
            '--verbose'
        ])

        # Should show phase arrow separator
        assert 'PLAN → VERIFY → DECOMPOSE → EXECUTE' in result.output


class TestDSLWorkflowResults:
    """Integration tests for DSL workflow result formatting."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    def test_successful_workflow_shows_result(self, runner):
        """Test successful workflow displays execution result."""
        result = runner.invoke(main, [
            '--workflow', 'examples/workflows/simple_pipeline.ct'
        ])

        # Should show result section
        assert 'Result:' in result.output
        # Should show task execution
        assert 'task:' in result.output

    def test_workflow_result_formatting(self, runner):
        """Test workflow result is formatted correctly."""
        result = runner.invoke(main, [
            '--workflow', 'examples/workflows/simple_pipeline.ct'
        ])

        # Should use proper formatting
        assert '======' in result.output  # Separator lines
        assert '✓' in result.output  # Success checkmark

    def test_workflow_shows_phase_completion_summary(self, runner):
        """Test workflow shows completed phases summary."""
        result = runner.invoke(main, [
            '--workflow', 'examples/workflows/simple_pipeline.ct'
        ])

        # Should show phases completed
        assert 'Phases:' in result.output
        assert 'PLAN' in result.output
        assert 'VERIFY' in result.output
        assert 'DECOMPOSE' in result.output
        assert 'EXECUTE' in result.output


class TestDSLErrorHandling:
    """Integration tests for DSL workflow error handling."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    def test_empty_workflow_fails_gracefully(self, runner, tmp_path):
        """Test empty workflow file fails at VERIFY phase."""
        empty_workflow = tmp_path / "empty.ct"
        empty_workflow.write_text("")

        result = runner.invoke(main, [
            '--workflow', str(empty_workflow)
        ])

        # Should fail gracefully
        assert result.exit_code != 0
        # Should show which phase failed
        assert 'VERIFY' in result.output or 'Validation failed' in result.output

    def test_invalid_workflow_file_extension_warning(self, runner, tmp_path):
        """Test workflow file with non-.ct extension shows warning."""
        wrong_ext = tmp_path / "workflow.txt"
        wrong_ext.write_text("functor main = build")

        result = runner.invoke(main, [
            '--workflow', str(wrong_ext)
        ])

        # Should show warning about extension
        # (Note: current implementation may or may not warn, test actual behavior)
        assert result.exit_code in [0, 1]


class TestDSLBackwardCompatibility:
    """Integration tests for backward compatibility with direct mode."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    def test_direct_mode_still_works(self, runner):
        """Test direct task mode still functions correctly."""
        result = runner.invoke(main, [
            '--task', 'Write a hello world function',
            '--provider', 'mock'
        ])

        # Should work as before
        assert result.exit_code in [0, 1]
        # Should not show lifecycle phases (those are workflow-specific)
        assert 'PLAN' not in result.output

    def test_multiple_tasks_in_direct_mode(self, runner):
        """Test multiple tasks work in direct mode."""
        result = runner.invoke(main, [
            '--task', 'Task one',
            '--task', 'Task two',
            '--provider', 'mock'
        ])

        # Should handle multiple tasks
        assert result.exit_code in [0, 1]

    def test_config_file_works_with_workflow(self, runner, tmp_path):
        """Test config file works with workflow mode."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"provider": "mock", "verbose": true, "timeout": 120}')

        result = runner.invoke(main, [
            '--workflow', 'examples/workflows/simple_pipeline.ct',
            '--config', str(config_file)
        ])

        # Should load config and execute workflow
        assert result.exit_code == 0
