"""
Unit tests for PromptBuilder (P2.3).

Tests interactive prompt creation workflow with validation integration.
"""

import pytest
import tempfile
import json
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.cli.prompt_builder import PromptBuilder
from src.entity.prompt_strategy import PromptStrategy


class TestPromptBuilderInit:
    """Test PromptBuilder initialization."""

    def test_init_default_min_score(self):
        """Test initialization with default min_score."""
        builder = PromptBuilder()
        assert builder.min_score == 60.0
        assert builder.validator is not None

    def test_init_custom_min_score(self):
        """Test initialization with custom min_score."""
        builder = PromptBuilder(min_score=70.0)
        assert builder.min_score == 70.0


class TestPromptBuilderDomains:
    """Test domain selection and configuration."""

    def test_domains_available(self):
        """Test that all expected domains are available."""
        builder = PromptBuilder()
        expected_domains = [
            "frontend", "backend", "testing", "qa", "research",
            "devops", "security", "performance", "documentation",
            "dsl", "category-theory", "general"
        ]
        for domain in expected_domains:
            assert domain in builder.DOMAINS

    def test_domain_descriptions(self):
        """Test that all domains have descriptions."""
        builder = PromptBuilder()
        for domain, description in builder.DOMAINS.items():
            assert isinstance(description, str)
            assert len(description) > 0


class TestPromptBuilderSuggestionGenerators:
    """Test suggestion generator methods."""

    def test_get_persona_examples_frontend(self):
        """Test persona examples for frontend domain."""
        builder = PromptBuilder()
        examples = builder.get_persona_examples("frontend")
        assert isinstance(examples, list)
        assert len(examples) > 0
        assert any("Frontend" in ex or "React" in ex for ex in examples)

    def test_get_persona_examples_backend(self):
        """Test persona examples for backend domain."""
        builder = PromptBuilder()
        examples = builder.get_persona_examples("backend")
        assert isinstance(examples, list)
        assert len(examples) > 0
        assert any("Backend" in ex or "Python" in ex for ex in examples)

    def test_get_persona_examples_unknown_domain(self):
        """Test persona examples for unknown domain returns generic examples."""
        builder = PromptBuilder()
        examples = builder.get_persona_examples("unknown_domain")
        assert isinstance(examples, list)
        assert len(examples) > 0

    def test_suggest_metrics_frontend(self):
        """Test metric suggestions for frontend domain."""
        builder = PromptBuilder()
        metrics = builder.suggest_metrics("frontend")
        assert isinstance(metrics, list)
        assert len(metrics) > 0
        assert any("Lighthouse" in m or "performance" in m for m in metrics)

    def test_suggest_metrics_backend(self):
        """Test metric suggestions for backend domain."""
        builder = PromptBuilder()
        metrics = builder.suggest_metrics("backend")
        assert isinstance(metrics, list)
        assert len(metrics) > 0
        assert any("API" in m or "response time" in m for m in metrics)

    def test_suggest_metrics_testing(self):
        """Test metric suggestions for testing domain."""
        builder = PromptBuilder()
        metrics = builder.suggest_metrics("testing")
        assert isinstance(metrics, list)
        assert len(metrics) > 0
        assert any("coverage" in m for m in metrics)

    def test_suggest_file_paths_frontend(self):
        """Test file path suggestions for frontend domain."""
        builder = PromptBuilder()
        paths = builder.suggest_file_paths("frontend")
        assert isinstance(paths, list)
        assert len(paths) > 0
        assert any(".tsx" in p or "components" in p for p in paths)

    def test_suggest_file_paths_backend(self):
        """Test file path suggestions for backend domain."""
        builder = PromptBuilder()
        paths = builder.suggest_file_paths("backend")
        assert isinstance(paths, list)
        assert len(paths) > 0
        assert any("src/" in p for p in paths)

    def test_suggest_tools_testing(self):
        """Test tool suggestions for testing domain."""
        builder = PromptBuilder()
        tools = builder.suggest_tools("testing")
        assert isinstance(tools, list)
        assert len(tools) > 0
        assert any("pytest" in t for t in tools)

    def test_suggest_tools_devops(self):
        """Test tool suggestions for devops domain."""
        builder = PromptBuilder()
        tools = builder.suggest_tools("devops")
        assert isinstance(tools, list)
        assert len(tools) > 0
        assert any("Docker" in t or "Kubernetes" in t for t in tools)

    def test_suggest_constraints(self):
        """Test constraint suggestions."""
        builder = PromptBuilder()
        constraints = builder.suggest_constraints("backend")
        assert isinstance(constraints, list)
        assert len(constraints) > 0
        assert any("Agent Tier" in c for c in constraints)
        assert any("ULTRATHINK" in c for c in constraints)


class TestPromptBuilderValidation:
    """Test validation integration."""

    def test_validate_and_review_high_quality_prompt(self):
        """Test validation with high-quality prompt."""
        builder = PromptBuilder(min_score=60.0)

        # Create high-quality prompt
        prompt = PromptStrategy(
            persona="Senior Backend Engineer with 5+ years Python and FastAPI experience, "
                    "specializing in API design and database optimization",
            goal="Reduce API response time p95 from 150ms to <50ms while maintaining "
                 "100% backward compatibility and >99.9% uptime",
            task="Profile src/adapters/agent/llm_executor.py execute() method using cProfile, "
                 "identify database query bottlenecks, implement connection pooling, "
                 "add Redis caching for frequently-accessed data with 5-minute TTL, "
                 "and create pytest benchmarks to verify <50ms p95 target",
            context="Agent Tier: 2 (Lead)\n"
                    "Previous interactions: 0\n"
                    "Available tools: cProfile, pytest-benchmark, Redis\n"
                    "Constraints: Must maintain backward compatibility, no breaking changes\n"
                    "Success criteria: p95 latency <50ms, all tests passing, zero downtime deployment\n"
                    "ULTRATHINK: Enabled - analyze caching vs complexity trade-offs",
            domain="backend",
            iteration=1
        )

        # Mock click prompts to auto-accept
        with patch('click.prompt', return_value='yes'):
            result = builder.validate_and_review(prompt)

        # Should pass validation
        assert result is not None
        assert result.quality_score is not None
        assert result.quality_score >= 60.0

    def test_validate_and_review_low_quality_prompt(self):
        """Test validation with low-quality prompt."""
        builder = PromptBuilder(min_score=60.0)

        # Create low-quality prompt
        prompt = PromptStrategy(
            persona="Developer",
            goal="Make it faster",
            task="Optimize the code",
            context="System is slow",
            domain="general",
            iteration=1
        )

        # Mock click prompts to reject
        with patch('click.prompt', return_value='no'):
            result = builder.validate_and_review(prompt)

        # Should fail validation or be rejected
        assert result is None or result.quality_score < 60.0


class TestPromptBuilderOutputFormats:
    """Test output file formatters."""

    def test_save_yaml_format(self):
        """Test saving prompt as YAML."""
        builder = PromptBuilder()
        prompt = PromptStrategy(
            persona="Test persona",
            goal="Test goal",
            task="Test task",
            context="Test context",
            domain="testing"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            file_path = tmppath / "test_prompt.yaml"

            # Save YAML
            builder._save_yaml(prompt, file_path)

            # Verify file exists and is valid YAML
            assert file_path.exists()
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)

            assert data["persona"] == "Test persona"
            assert data["goal"] == "Test goal"
            assert data["task"] == "Test task"
            assert data["context"] == "Test context"
            assert data["domain"] == "testing"

    def test_save_json_format(self):
        """Test saving prompt as JSON."""
        builder = PromptBuilder()
        prompt = PromptStrategy(
            persona="Test persona",
            goal="Test goal",
            task="Test task",
            context="Test context",
            domain="testing"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            file_path = tmppath / "test_prompt.json"

            # Save JSON
            builder._save_json(prompt, file_path)

            # Verify file exists and is valid JSON
            assert file_path.exists()
            with open(file_path, 'r') as f:
                data = json.load(f)

            assert data["persona"] == "Test persona"
            assert data["goal"] == "Test goal"
            assert data["task"] == "Test task"
            assert data["context"] == "Test context"
            assert data["domain"] == "testing"

    def test_save_python_format(self):
        """Test saving prompt as Python dict."""
        builder = PromptBuilder()
        prompt = PromptStrategy(
            persona="Test persona",
            goal="Test goal",
            task="Test task",
            context="Test context",
            domain="testing"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            file_path = tmppath / "test_prompt.py"

            # Save Python
            builder._save_python(prompt, file_path)

            # Verify file exists and is valid Python
            assert file_path.exists()
            with open(file_path, 'r') as f:
                content = f.read()

            assert "PROMPT_STRATEGY" in content
            assert "Test persona" in content
            assert "Test goal" in content


class TestPromptBuilderIntegration:
    """Integration tests for full workflow."""

    @patch('click.echo')
    @patch('click.prompt')
    def test_build_interactive_workflow_complete(self, mock_prompt, mock_echo):
        """Test complete interactive workflow with mocked inputs."""
        builder = PromptBuilder(min_score=60.0)

        # Mock all user inputs
        mock_prompt.side_effect = [
            "backend",  # domain selection
            "Senior Backend Engineer with Python expertise",  # persona
            "Reduce latency from 150ms to <50ms",  # goal
            "Profile src/adapters/agent/llm_executor.py using cProfile",  # task
            "Agent Tier: 2, Tools: cProfile, pytest-benchmark",  # context
            "yes"  # save prompt
        ]

        # Run interactive workflow
        result = builder.build_interactive()

        # Should create prompt
        assert result is not None
        assert isinstance(result, PromptStrategy)
        assert result.domain == "backend"
        assert "Senior Backend Engineer" in result.persona
        assert "latency" in result.goal.lower()

    @patch('click.echo')
    @patch('click.prompt')
    def test_build_interactive_workflow_cancelled(self, mock_prompt, mock_echo):
        """Test interactive workflow when user cancels."""
        builder = PromptBuilder(min_score=60.0)

        # Mock user cancelling at persona step
        mock_prompt.side_effect = [
            "backend",  # domain selection
            "",  # empty persona (cancel)
        ]

        # Run interactive workflow
        result = builder.build_interactive()

        # Should return None (cancelled)
        assert result is None


class TestPromptBuilderEdgeCases:
    """Test edge cases and error handling."""

    def test_unknown_domain_fallback(self):
        """Test that unknown domains fall back to generic suggestions."""
        builder = PromptBuilder()

        # Test with completely unknown domain
        examples = builder.get_persona_examples("nonexistent_domain")
        assert isinstance(examples, list)
        assert len(examples) > 0

        metrics = builder.suggest_metrics("nonexistent_domain")
        assert isinstance(metrics, list)

        paths = builder.suggest_file_paths("nonexistent_domain")
        assert isinstance(paths, list)

        tools = builder.suggest_tools("nonexistent_domain")
        assert isinstance(tools, list)

    def test_empty_domain(self):
        """Test handling of empty domain string."""
        builder = PromptBuilder()

        # Should handle empty domain gracefully
        examples = builder.get_persona_examples("")
        assert isinstance(examples, list)

    def test_save_prompt_invalid_format(self):
        """Test save_prompt with invalid format."""
        builder = PromptBuilder()
        prompt = PromptStrategy(
            persona="Test",
            goal="Test",
            task="Test",
            context="Test"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            file_path = tmppath / "test.invalid"

            # Mock prompts (need two: output dir and confirmation)
            with patch('click.prompt', side_effect=[str(tmppath), "yes"]):
                with patch('click.echo') as mock_echo:
                    result = builder.save_prompt(prompt, output_format="invalid_format")

                    # Should fail gracefully
                    assert result is None
                    # Should show error message
                    mock_echo.assert_any_call("Unsupported format: invalid_format")
