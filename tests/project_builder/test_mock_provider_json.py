import json
import pytest
from src.adapters.llm.mock_provider import MockLLMProvider


def test_mock_provider_returns_valid_json():
    """Test that mock provider returns valid JSON."""
    provider = MockLLMProvider()
    response = provider.generate("goal: Create CI/CD pipeline")

    # Should be valid JSON
    parsed = json.loads(response)
    assert 'tasks' in parsed
    assert isinstance(parsed['tasks'], list)
    assert len(parsed['tasks']) > 0


def test_mock_provider_ci_cd_template():
    """Test CI/CD goals return appropriate template."""
    provider = MockLLMProvider()
    response = provider.generate("goal: Automated CI/CD pipeline with git hooks")
    parsed = json.loads(response)

    # Should have CI/CD specific tasks
    task_descriptions = [t['description'] for t in parsed['tasks']]
    assert any('git' in desc.lower() or 'github' in desc.lower() for desc in task_descriptions)


def test_mock_provider_rest_api_template():
    """Test REST API goals return appropriate template."""
    provider = MockLLMProvider()
    response = provider.generate("goal: Create REST API with FastAPI")
    parsed = json.loads(response)

    # Should have API specific tasks
    task_descriptions = [t['description'] for t in parsed['tasks']]
    assert any('api' in desc.lower() or 'endpoint' in desc.lower() for desc in task_descriptions)


def test_mock_provider_default_template():
    """Test unknown goals return default template."""
    provider = MockLLMProvider()
    response = provider.generate("goal: Something completely random")
    parsed = json.loads(response)

    # Should still be valid JSON with tasks
    assert 'tasks' in parsed
    assert len(parsed['tasks']) > 0

