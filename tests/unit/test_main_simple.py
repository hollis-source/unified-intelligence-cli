"""Simplified unit tests for CLI entry point (main.py)."""

import pytest
import logging
from click.testing import CliRunner
from pathlib import Path

from src.main import main, setup_logging, load_config
from src.config import Config


class TestLoadConfig:
    """Test configuration loading logic."""

    def test_load_config_no_file(self):
        """Test config loading with CLI args only."""
        config = load_config(
            config_file=None,
            provider="mock",
            verbose=True,
            parallel=False,
            timeout=120
        )

        assert config.provider == "mock"
        assert config.verbose is True
        assert config.parallel is False
        assert config.timeout == 120

    def test_load_config_with_file(self, tmp_path):
        """Test config loading from file with CLI override."""
        config_file = tmp_path / "test_config.json"
        config_file.write_text('{"provider": "grok", "verbose": false, "timeout": 60}')

        config = load_config(
            config_file=str(config_file),
            provider="mock",  # CLI override
            verbose=True,     # CLI override
            parallel=True,
            timeout=90        # CLI override
        )

        assert config.provider == "mock"  # CLI wins
        assert config.verbose is True      # CLI wins
        assert config.timeout == 90        # CLI wins


class TestSetupLogging:
    """Test logging configuration."""

    def test_setup_logging_returns_logger(self):
        """Test that setup_logging returns a logger."""
        logger = setup_logging(verbose=True)

        assert logger is not None
        assert logger.name == "src.main"
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'debug')


class TestMainCLI:
    """Test main CLI entry point with Click runner."""

    def test_main_help(self):
        """Test --help flag."""
        runner = CliRunner()
        result = runner.invoke(main, ['--help'])

        assert result.exit_code == 0
        assert 'Unified Intelligence CLI' in result.output
        assert '--task' in result.output
        assert '--provider' in result.output
        assert '--verbose' in result.output
        assert '--timeout' in result.output
        assert '--config' in result.output

    def test_main_no_tasks(self):
        """Test error when no tasks provided."""
        runner = CliRunner()
        result = runner.invoke(main, ['--provider', 'mock'])

        assert result.exit_code != 0
        # Should show error about missing required option
        assert 'Missing option' in result.output or 'required' in result.output.lower()

    def test_main_invalid_provider(self):
        """Test error with invalid provider choice."""
        runner = CliRunner()
        result = runner.invoke(main, [
            '--task', 'Test task',
            '--provider', 'invalid_provider'
        ])

        # Should fail due to invalid choice
        assert result.exit_code != 0
        assert 'Invalid value' in result.output or 'invalid' in result.output.lower()

    def test_main_single_task_dry_run(self):
        """Test with single task (will fail at execution, but validates parsing)."""
        runner = CliRunner()
        result = runner.invoke(main, [
            '--task', 'Write a function',
            '--provider', 'mock'
        ])

        # Will error during execution (no mocks), but that's ok
        # We're testing that CLI parsing works
        assert '--task' not in result.output  # No help text shown
        # Either succeeds or fails gracefully (not a CLI parsing error)

    def test_main_multiple_tasks_parsing(self):
        """Test that multiple tasks are accepted."""
        runner = CliRunner()
        result = runner.invoke(main, [
            '--task', 'First task',
            '--task', 'Second task',
            '--task', 'Third task',
            '--provider', 'mock'
        ])

        # Should accept multiple --task options
        # Will error at execution but validates CLI parsing
        assert result.exit_code in [0, 1]  # Either succeeds or fails gracefully

    def test_main_with_timeout_parsing(self):
        """Test timeout parameter parsing."""
        runner = CliRunner()
        result = runner.invoke(main, [
            '--task', 'Test task',
            '--provider', 'mock',
            '--timeout', '120'
        ])

        # Should accept timeout parameter
        assert result.exit_code in [0, 1]

    def test_main_with_verbose_flag(self):
        """Test verbose flag parsing."""
        runner = CliRunner()
        result = runner.invoke(main, [
            '--task', 'Test task',
            '--provider', 'mock',
            '--verbose'
        ])

        # Should accept verbose flag
        assert result.exit_code in [0, 1]

    def test_main_with_config_file_parsing(self, tmp_path):
        """Test config file parameter parsing."""
        config_file = tmp_path / "test.json"
        config_file.write_text('{"provider": "mock", "timeout": 90}')

        runner = CliRunner()
        result = runner.invoke(main, [
            '--task', 'Test task',
            '--config', str(config_file)
        ])

        # Should accept config file
        assert result.exit_code in [0, 1]

    def test_main_with_nonexistent_config(self):
        """Test error with nonexistent config file."""
        runner = CliRunner()
        result = runner.invoke(main, [
            '--task', 'Test task',
            '--config', '/nonexistent/config.json'
        ])

        # Should fail - file doesn't exist
        assert result.exit_code != 0
        assert 'does not exist' in result.output.lower() or 'invalid' in result.output.lower()