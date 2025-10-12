# Project Builder Bug Fix Plan

**Date**: 2025-10-11
**Status**: 🔴 **CRITICAL BUGS BLOCKING EXTERNAL USE**
**Source**: Meta-dogfooding test by Auggie (GPT-5)
**Related**: `docs/META_DOGFOODING_REPORT.md`

---

## Executive Summary

**Discovered via**: External AI agent (Auggie) attempting to use Project Builder for CI/CD generation

**Impact**: Project Builder is currently **UNUSABLE** by external agents

**Priority Order**:
1. **P0 - CRITICAL**: Fix LocalTongyiAdapter signature mismatch (Bug #2)
2. **P0 - CRITICAL**: Fix MockLLMProvider JSON output (Bug #1)
3. **P1 - HIGH**: Implement deterministic recipe system (Issue #6)
4. **P1 - HIGH**: Document Docker exec usage (Issue #5)
5. **P1 - HIGH**: Provider fallback chain (Bug #3)
6. **P2 - MEDIUM**: Interface conformance tests
7. **P3 - LOW**: Redis connectivity improvements (Issue #4)

**Estimated Total Time**: 15-20 hours for P0-P1 fixes

---

## Bug #1: MockLLMProvider Returns Non-JSON Text

### Priority: P0 - CRITICAL
### Estimated Time: 3 hours
### Blocks: Offline testing, dogfooding without external LLM

### Problem

**Current Behavior**:
```python
# src/adapters/llm/mock_provider.py
def generate(self, prompt: str, **kwargs) -> str:
    if "plan" in prompt.lower():
        return "Execute tasks in order: 1, 2, 3"  # Plain text!
```

**Expected Behavior**:
```python
def generate(self, prompt: str, **kwargs) -> str:
    if "plan" in prompt.lower():
        return json.dumps({
            "tasks": [
                {
                    "id": "task1",
                    "description": "Setup CI/CD infrastructure",
                    "subtasks": ["task1.1", "task1.2"]
                },
                {
                    "id": "task2",
                    "description": "Implement workflows",
                    "subtasks": ["task2.1", "task2.2"]
                }
            ]
        })
```

**Error**:
```
[GOAL_DECOMPOSER] Could not extract JSON from response:
Execute tasks in order: 1, 2, 3
```

### Root Cause

1. `MockLLMProvider` returns plain text strings
2. `GoalDecomposer` expects structured JSON: `{"tasks": [...]}`
3. No JSON mode or structured output in mock provider
4. Mock provider likely created for simple testing, not production dogfooding

### Fix Plan

#### Step 1: Read Current MockLLMProvider Implementation (15 min)

```bash
# Examine current implementation
cat src/adapters/llm/mock_provider.py

# Check how it's invoked
grep -r "MockLLMProvider" src/
```

**What to look for**:
- Current response formats
- How prompts are matched (keywords?)
- Interface contract with GoalDecomposer

#### Step 2: Create Mock Response Templates (45 min)

Create `src/adapters/llm/mock_responses.json`:

```json
{
  "ci_cd_pipeline": {
    "tasks": [
      {
        "id": "setup_git_hooks",
        "description": "Setup git hooks for pre-commit and post-commit automation",
        "priority": 1,
        "dependencies": [],
        "subtasks": [
          {
            "id": "setup_git_hooks.1",
            "description": "Create pre-commit hook for linting and testing",
            "file": ".git/hooks/pre-commit"
          },
          {
            "id": "setup_git_hooks.2",
            "description": "Create post-commit hook for optional auto-commit",
            "file": ".git/hooks/post-commit"
          }
        ]
      },
      {
        "id": "github_actions_ci",
        "description": "Create GitHub Actions workflow for CI",
        "priority": 2,
        "dependencies": [],
        "subtasks": [
          {
            "id": "github_actions_ci.1",
            "description": "Create CI workflow with lint, test, build",
            "file": ".github/workflows/ci.yml"
          }
        ]
      },
      {
        "id": "github_actions_cd",
        "description": "Create GitHub Actions workflow for CD",
        "priority": 3,
        "dependencies": ["github_actions_ci"],
        "subtasks": [
          {
            "id": "github_actions_cd.1",
            "description": "Create CD workflow for production deployment",
            "file": ".github/workflows/cd.yml"
          }
        ]
      },
      {
        "id": "github_actions_security",
        "description": "Create GitHub Actions workflow for security scanning",
        "priority": 4,
        "dependencies": [],
        "subtasks": [
          {
            "id": "github_actions_security.1",
            "description": "Add secret scanning and vulnerability checks",
            "file": ".github/workflows/security.yml"
          }
        ]
      }
    ]
  },
  "rest_api": {
    "tasks": [
      {
        "id": "setup_fastapi",
        "description": "Setup FastAPI application structure",
        "priority": 1,
        "dependencies": [],
        "subtasks": [...]
      }
    ]
  },
  "default": {
    "tasks": [
      {
        "id": "analyze_requirements",
        "description": "Analyze project requirements",
        "priority": 1,
        "dependencies": [],
        "subtasks": []
      },
      {
        "id": "implement_solution",
        "description": "Implement the solution",
        "priority": 2,
        "dependencies": ["analyze_requirements"],
        "subtasks": []
      }
    ]
  }
}
```

#### Step 3: Update MockLLMProvider to Use Templates (60 min)

```python
# src/adapters/llm/mock_provider.py
import json
from pathlib import Path
from typing import Dict, Any

class MockLLMProvider:
    def __init__(self):
        self.responses = self._load_responses()

    def _load_responses(self) -> Dict[str, Any]:
        """Load mock responses from JSON file."""
        responses_path = Path(__file__).parent / 'mock_responses.json'
        if responses_path.exists():
            with open(responses_path, 'r') as f:
                return json.load(f)
        return {}

    def _match_goal_to_template(self, goal: str) -> str:
        """Match goal description to appropriate template."""
        goal_lower = goal.lower()

        # Keyword matching for common patterns
        if any(kw in goal_lower for kw in ['ci/cd', 'ci cd', 'github actions', 'pipeline']):
            return 'ci_cd_pipeline'
        elif any(kw in goal_lower for kw in ['rest api', 'api', 'fastapi', 'flask']):
            return 'rest_api'
        elif any(kw in goal_lower for kw in ['docker', 'compose', 'container']):
            return 'docker_compose'
        else:
            return 'default'

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate mock response with proper JSON structure."""

        # Extract goal from prompt (GoalDecomposer likely includes it)
        # Look for "goal:" or "Goal:" in prompt
        goal = ""
        for line in prompt.split('\n'):
            if 'goal:' in line.lower():
                goal = line.split(':', 1)[1].strip()
                break

        # Match to template
        template_key = self._match_goal_to_template(goal)

        # Return JSON response
        if template_key in self.responses:
            return json.dumps(self.responses[template_key], indent=2)
        else:
            # Fallback to default
            return json.dumps(self.responses.get('default', {
                "tasks": [
                    {
                        "id": "task1",
                        "description": "Implement the requested functionality",
                        "priority": 1,
                        "dependencies": [],
                        "subtasks": []
                    }
                ]
            }), indent=2)
```

#### Step 4: Test MockLLMProvider JSON Output (30 min)

Create test file `tests/test_mock_provider_json.py`:

```python
import json
import pytest
from src.adapters.llm.mock_provider import MockLLMProvider

def test_mock_provider_returns_valid_json():
    """Test that mock provider returns valid JSON."""
    provider = MockLLMProvider()

    response = provider.generate("goal: Create CI/CD pipeline")

    # Should be valid JSON
    parsed = json.loads(response)

    # Should have tasks key
    assert 'tasks' in parsed
    assert isinstance(parsed['tasks'], list)
    assert len(parsed['tasks']) > 0

def test_mock_provider_ci_cd_template():
    """Test that CI/CD goals return appropriate template."""
    provider = MockLLMProvider()

    goals = [
        "goal: Create CI/CD pipeline",
        "goal: Automated CI/CD pipeline with git hooks",
        "goal: GitHub Actions workflows"
    ]

    for goal in goals:
        response = provider.generate(goal)
        parsed = json.loads(response)

        # Should have CI/CD specific tasks
        task_descriptions = [t['description'] for t in parsed['tasks']]
        assert any('git' in desc.lower() or 'github' in desc.lower()
                  for desc in task_descriptions)

def test_mock_provider_default_template():
    """Test that unknown goals return default template."""
    provider = MockLLMProvider()

    response = provider.generate("goal: Something completely random")
    parsed = json.loads(response)

    # Should still be valid JSON with tasks
    assert 'tasks' in parsed
    assert len(parsed['tasks']) > 0

def test_goal_decomposer_can_parse_mock_response():
    """Integration test: GoalDecomposer can parse mock response."""
    from src.project_builder.goal_decomposer import GoalDecomposer

    provider = MockLLMProvider()
    decomposer = GoalDecomposer(provider)

    # This should not raise an exception
    result = decomposer.decompose("Create CI/CD pipeline")

    assert result is not None
    assert len(result.tasks) > 0
```

Run tests:
```bash
pytest tests/test_mock_provider_json.py -v
```

#### Step 5: Verify with Auggie Re-test (30 min)

```bash
# Re-run Auggie's test with mock provider
docker exec -it project-builder python -m src.project_builder.cli.command \
  "goal: Automated CI/CD pipeline with git hooks and GitHub Actions workflows" \
  --project-id ci-cd-pipeline-fixed \
  --model mock \
  --parallel \
  --verbose

# Check if artifacts generated
ls -la /home/ui-cli_jake/unified-intelligence-cli/projects/ci-cd-pipeline-fixed/

# If successful, extract artifacts
docker cp project-builder:/app/projects/ci-cd-pipeline-fixed ./projects/
```

### Acceptance Criteria

- ✅ MockLLMProvider returns valid JSON
- ✅ JSON structure matches GoalDecomposer expectations
- ✅ CI/CD goals return CI/CD-specific template
- ✅ Unknown goals return default template
- ✅ Unit tests pass
- ✅ Integration test with GoalDecomposer passes
- ✅ Auggie re-test succeeds with mock provider
- ✅ Artifacts generated in expected location

### Files to Modify

- `src/adapters/llm/mock_provider.py` - Update generate() method
- `src/adapters/llm/mock_responses.json` - Create template file (new)
- `tests/test_mock_provider_json.py` - Add tests (new)

---

## Bug #2: LocalTongyiAdapter Signature Mismatch

### Priority: P0 - CRITICAL
### Estimated Time: 2 hours
### Blocks: Local LLM usage

### Problem

**Error**:
```
TypeError: LocalTongyiAdapter.generate() missing 1 required positional argument: 'prompt'
```

**Root Cause**: `LocalTongyiAdapter.generate()` method signature doesn't match `ITextGenerator` interface.

### Fix Plan

#### Step 1: Examine Interface Contract (15 min)

```bash
# Find ITextGenerator interface
find src/ -name "*text_generator*" -o -name "*interface*" | xargs grep -l "ITextGenerator"

# Read interface definition
cat src/interfaces/text_generator.py  # or wherever it's defined

# Check all adapter implementations
find src/adapters/llm/ -name "*.py" -exec echo "=== {} ===" \; -exec grep -A 10 "def generate" {} \;
```

**Expected Interface**:
```python
class ITextGenerator(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text response from prompt."""
        pass
```

#### Step 2: Read LocalTongyiAdapter Implementation (15 min)

```bash
cat src/adapters/llm/tongyi_local.py
```

**What to look for**:
- Current method signature
- What parameters it expects
- How it's called internally
- Any other methods that might need updating

#### Step 3: Fix Signature to Match Interface (30 min)

**Before** (hypothetical):
```python
class LocalTongyiAdapter:
    def generate(self, **kwargs) -> str:  # Missing prompt parameter!
        # Implementation
        pass
```

**After**:
```python
class LocalTongyiAdapter(ITextGenerator):
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response from local Tongyi model.

        Args:
            prompt: The text prompt to send to model
            **kwargs: Additional generation parameters
                - temperature: float (default 0.7)
                - max_tokens: int (default 2048)
                - top_p: float (default 0.9)

        Returns:
            str: Generated text response
        """
        # Validate prompt
        if not prompt or not isinstance(prompt, str):
            raise ValueError("prompt must be a non-empty string")

        # Extract generation parameters
        temperature = kwargs.get('temperature', 0.7)
        max_tokens = kwargs.get('max_tokens', 2048)
        top_p = kwargs.get('top_p', 0.9)

        # Call local model
        response = self._call_local_model(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p
        )

        return response

    def _call_local_model(self, prompt: str, **params) -> str:
        """Internal method to call local Tongyi model."""
        # Implementation depends on how local model is accessed
        # Could be via HTTP, subprocess, or direct Python binding
        pass
```

#### Step 4: Verify All Adapters Match Interface (30 min)

Check all adapters for consistency:

```bash
# List all adapter implementations
ls -la src/adapters/llm/

# Check each one
for adapter in src/adapters/llm/*_adapter.py; do
    echo "=== $adapter ==="
    grep -A 5 "def generate" "$adapter"
done
```

**Adapters to check**:
- `mock_provider.py` - Should already match after Bug #1 fix
- `tongyi_local.py` - Fixing now
- `openai_adapter.py` (if exists)
- `huggingface_adapter.py` (if exists)
- Any others

Ensure all have: `def generate(self, prompt: str, **kwargs) -> str:`

#### Step 5: Add Interface Conformance Test (30 min)

Create `tests/test_adapter_interfaces.py`:

```python
import pytest
from abc import ABC
from src.interfaces.text_generator import ITextGenerator
from src.adapters.llm.mock_provider import MockLLMProvider
from src.adapters.llm.tongyi_local import LocalTongyiAdapter

def test_adapter_has_generate_method():
    """Test that all adapters have generate method."""
    adapters = [MockLLMProvider(), LocalTongyiAdapter()]

    for adapter in adapters:
        assert hasattr(adapter, 'generate'), \
            f"{adapter.__class__.__name__} missing generate method"

def test_adapter_generate_signature():
    """Test that generate method accepts prompt parameter."""
    adapters = [MockLLMProvider(), LocalTongyiAdapter()]

    for adapter in adapters:
        # Should accept prompt as first positional argument
        try:
            result = adapter.generate("test prompt")
            assert isinstance(result, str), \
                f"{adapter.__class__.__name__}.generate() should return str"
        except TypeError as e:
            pytest.fail(
                f"{adapter.__class__.__name__}.generate() signature error: {e}"
            )

def test_adapter_implements_interface():
    """Test that all adapters implement ITextGenerator."""
    adapters = [MockLLMProvider, LocalTongyiAdapter]

    for adapter_class in adapters:
        assert issubclass(adapter_class, ITextGenerator), \
            f"{adapter_class.__name__} should implement ITextGenerator"

def test_adapter_generate_returns_string():
    """Test that generate returns string."""
    adapters = [MockLLMProvider(), LocalTongyiAdapter()]

    for adapter in adapters:
        result = adapter.generate("test prompt")
        assert isinstance(result, str), \
            f"{adapter.__class__.__name__}.generate() returned {type(result)}, expected str"
        assert len(result) > 0, \
            f"{adapter.__class__.__name__}.generate() returned empty string"
```

Run tests:
```bash
pytest tests/test_adapter_interfaces.py -v
```

#### Step 6: Test with Auggie Re-test (15 min)

```bash
# Re-run Auggie's test with tongyi-local provider
docker exec -it project-builder python -m src.project_builder.cli.command \
  "goal: Automated CI/CD pipeline with git hooks and GitHub Actions workflows" \
  --project-id ci-cd-pipeline-tongyi \
  --model tongyi-local \
  --verbose

# Should not raise TypeError anymore
```

### Acceptance Criteria

- ✅ LocalTongyiAdapter.generate() has correct signature: `def generate(self, prompt: str, **kwargs) -> str`
- ✅ All adapters implement ITextGenerator interface
- ✅ Interface conformance tests pass
- ✅ No TypeError when calling generate()
- ✅ Auggie re-test with tongyi-local proceeds past adapter initialization

### Files to Modify

- `src/adapters/llm/tongyi_local.py` - Fix generate() signature
- `tests/test_adapter_interfaces.py` - Add interface tests (new)

---

## Issue #6: No Offline Deterministic Path for Common Tasks

### Priority: P1 - HIGH
### Estimated Time: 4-6 hours
### Value: Enables fast, reliable dogfooding without LLM dependency

### Problem

Common tasks like "CI/CD pipeline" require LLM inference every time, even though the output should be deterministic and well-defined.

### Fix Plan: Implement Recipe System

#### Step 1: Design Recipe System Architecture (30 min)

**Concept**: Pre-defined templates for common project types that bypass LLM entirely.

**CLI Interface**:
```bash
# List available recipes
docker exec project-builder python -m src.project_builder.cli.command --list-recipes

# Use recipe
docker exec project-builder python -m src.project_builder.cli.command \
  --recipe ci-cd-standard \
  --project-id my-project \
  --output-dir /app/projects

# Customize recipe with variables
docker exec project-builder python -m src.project_builder.cli.command \
  --recipe ci-cd-standard \
  --project-id my-project \
  --var "python_version=3.11" \
  --var "test_framework=pytest"
```

**Architecture**:
```
src/project_builder/recipes/
  ├── __init__.py
  ├── base_recipe.py           # BaseRecipe abstract class
  ├── recipe_registry.py       # RecipeRegistry for discovery
  ├── ci_cd_standard.py        # CI/CD recipe implementation
  ├── rest_api_python.py       # REST API recipe
  └── templates/
      ├── ci_cd/
      │   ├── .github/workflows/ci.yml.j2
      │   ├── .github/workflows/cd.yml.j2
      │   ├── .git/hooks/pre-commit.j2
      │   └── README.md.j2
      └── rest_api/
          ├── main.py.j2
          ├── requirements.txt.j2
          └── ...
```

#### Step 2: Implement BaseRecipe Class (45 min)

Create `src/project_builder/recipes/base_recipe.py`:

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List
from jinja2 import Environment, FileSystemLoader

class BaseRecipe(ABC):
    """Base class for project recipes."""

    def __init__(self):
        self.templates_dir = Path(__file__).parent / 'templates' / self.recipe_name
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir))
        )

    @property
    @abstractmethod
    def recipe_name(self) -> str:
        """Unique recipe identifier."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        pass

    @property
    def default_variables(self) -> Dict[str, Any]:
        """Default template variables."""
        return {}

    @abstractmethod
    def get_file_list(self) -> List[str]:
        """List of files to generate (relative paths)."""
        pass

    def generate(self, output_dir: Path, variables: Dict[str, Any] = None) -> None:
        """Generate project from recipe.

        Args:
            output_dir: Directory to generate project in
            variables: Template variables (merged with defaults)
        """
        # Merge variables with defaults
        vars = {**self.default_variables, **(variables or {})}

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate each file
        for file_path in self.get_file_list():
            self._generate_file(file_path, output_dir, vars)

    def _generate_file(self, file_path: str, output_dir: Path, variables: Dict[str, Any]) -> None:
        """Generate single file from template."""
        # Load template
        template_name = file_path + '.j2'
        template = self.jinja_env.get_template(template_name)

        # Render content
        content = template.render(**variables)

        # Write to output
        output_file = output_dir / file_path
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(content)

        # Set executable for hooks and scripts
        if '.git/hooks/' in file_path or file_path.endswith('.sh'):
            output_file.chmod(0o755)
```

#### Step 3: Implement CI/CD Recipe (90 min)

Create `src/project_builder/recipes/ci_cd_standard.py`:

```python
from pathlib import Path
from typing import Dict, Any, List
from .base_recipe import BaseRecipe

class CICDStandardRecipe(BaseRecipe):
    """Standard CI/CD pipeline with GitHub Actions and git hooks."""

    @property
    def recipe_name(self) -> str:
        return "ci-cd-standard"

    @property
    def description(self) -> str:
        return "Standard CI/CD pipeline with GitHub Actions, git hooks, and Docker"

    @property
    def default_variables(self) -> Dict[str, Any]:
        return {
            'python_version': '3.11',
            'test_framework': 'pytest',
            'lint_tools': ['ruff', 'black', 'mypy'],
            'docker_enabled': True,
            'security_scanning': True,
            'deploy_environments': ['staging', 'production']
        }

    def get_file_list(self) -> List[str]:
        return [
            '.github/workflows/ci.yml',
            '.github/workflows/cd.yml',
            '.github/workflows/security.yml',
            '.git/hooks/pre-commit',
            '.git/hooks/post-commit',
            'scripts/run-tests.sh',
            'scripts/lint.sh',
            'scripts/deploy.sh',
            'README-CICD.md'
        ]
```

#### Step 4: Create Jinja2 Templates (90 min)

Create templates in `src/project_builder/recipes/templates/ci_cd/`:

**`.github/workflows/ci.yml.j2`**:
```yaml
name: CI Pipeline

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: {{ python_version }}
      {% for tool in lint_tools %}
      - name: Run {{ tool }}
        run: {{ tool }} .
      {% endfor %}

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: {{ python_version }}
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: {{ test_framework }} tests/ --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  {% if docker_enabled %}
  build:
    runs-on: ubuntu-latest
    needs: [lint, test]
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker image
        run: docker build -t ${{ "{{" }} github.repository }}:${{ "{{" }} github.sha }} .
      - name: Test Docker image
        run: docker run ${{ "{{" }} github.repository }}:${{ "{{" }} github.sha }} --version
  {% endif %}
```

**`.github/workflows/cd.yml.j2`**:
```yaml
name: CD Pipeline

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  deploy:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        environment: {{ deploy_environments }}
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to ${{ "{{" }} matrix.environment }}
        run: ./scripts/deploy.sh ${{ "{{" }} matrix.environment }}
        env:
          DEPLOY_KEY: ${{ "{{" }} secrets.DEPLOY_KEY }}
```

**`.github/workflows/security.yml.j2`**:
```yaml
{% if security_scanning %}
name: Security Scanning

on:
  push:
    branches: [main, develop]
  schedule:
    - cron: '0 0 * * 0'  # Weekly

jobs:
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Gitleaks scan
        uses: gitleaks/gitleaks-action@v2

  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Safety check
        run: |
          pip install safety
          safety check --json
{% endif %}
```

**`.git/hooks/pre-commit.j2`**:
```bash
#!/bin/bash
set -e

echo "Running pre-commit hooks..."

# Lint
{% for tool in lint_tools %}
{{ tool }} .
{% endfor %}

# Test
{{ test_framework }} tests/

echo "✅ Pre-commit checks passed"
```

**`README-CICD.md.j2`**:
```markdown
# CI/CD Pipeline Documentation

Generated by Project Builder recipe: {{ recipe_name }}

## Overview

This project uses automated CI/CD with:
- GitHub Actions for CI/CD workflows
- Git hooks for local validation
- {% if docker_enabled %}Docker for containerization{% endif %}
- {% if security_scanning %}Automated security scanning{% endif %}

## Workflows

### CI Pipeline (`.github/workflows/ci.yml`)
Runs on every PR and push:
1. Lint with: {{ lint_tools | join(', ') }}
2. Test with: {{ test_framework }}
{% if docker_enabled %}3. Build and test Docker image{% endif %}

### CD Pipeline (`.github/workflows/cd.yml`)
Deploys on push to main:
- Environments: {{ deploy_environments | join(', ') }}
- Requires: `DEPLOY_KEY` secret

{% if security_scanning %}
### Security Scanning (`.github/workflows/security.yml`)
Runs weekly and on push:
- Secret scanning with Gitleaks
- Dependency vulnerability scanning with Safety
{% endif %}

## Git Hooks

### Pre-commit (`.git/hooks/pre-commit`)
Runs before every commit:
- Linting
- Unit tests

### Post-commit (`.git/hooks/post-commit`)
Optional automated commit messages

## Configuration

Python version: {{ python_version }}
Test framework: {{ test_framework }}
Lint tools: {{ lint_tools | join(', ') }}

## Customization

Edit workflow files in `.github/workflows/` to customize behavior.
```

#### Step 5: Implement RecipeRegistry (45 min)

Create `src/project_builder/recipes/recipe_registry.py`:

```python
from typing import Dict, Type
from .base_recipe import BaseRecipe
from .ci_cd_standard import CICDStandardRecipe
# Import other recipes as they're added

class RecipeRegistry:
    """Registry of available project recipes."""

    def __init__(self):
        self._recipes: Dict[str, Type[BaseRecipe]] = {}
        self._register_builtin_recipes()

    def _register_builtin_recipes(self):
        """Register built-in recipes."""
        self.register(CICDStandardRecipe)
        # Register others here

    def register(self, recipe_class: Type[BaseRecipe]) -> None:
        """Register a recipe class."""
        recipe = recipe_class()
        self._recipes[recipe.recipe_name] = recipe_class

    def get(self, name: str) -> BaseRecipe:
        """Get recipe instance by name."""
        if name not in self._recipes:
            raise ValueError(f"Recipe '{name}' not found. Available: {self.list_names()}")
        return self._recipes[name]()

    def list_names(self) -> list:
        """List all recipe names."""
        return list(self._recipes.keys())

    def list_recipes(self) -> Dict[str, str]:
        """List all recipes with descriptions."""
        return {
            name: cls().description
            for name, cls in self._recipes.items()
        }

# Global registry instance
registry = RecipeRegistry()
```

#### Step 6: Update CLI to Support Recipes (45 min)

Modify `src/project_builder/cli/command.py`:

```python
import click
from pathlib import Path
from ..recipes.recipe_registry import registry

@click.command(name="build-project")
@click.argument("goal", required=False, default="")
@click.option("--project-id", help="Custom project ID")
@click.option("--model", default="grok", help="LLM model to use")
@click.option("--recipe", help="Use pre-built recipe instead of LLM (e.g., ci-cd-standard)")
@click.option("--list-recipes", is_flag=True, help="List available recipes and exit")
@click.option("--var", multiple=True, help="Recipe variable (key=value)")
@click.option("--parallel/--sequential", default=True)
@click.option("--output-dir", default="projects")
@click.option("-v", "--verbose", is_flag=True)
def build_project(goal, project_id, model, recipe, list_recipes, var, parallel, output_dir, verbose):
    """Build a project from goal or recipe."""

    # List recipes and exit
    if list_recipes:
        recipes = registry.list_recipes()
        click.echo("\nAvailable Recipes:\n")
        for name, description in recipes.items():
            click.echo(f"  {name:20s} - {description}")
        click.echo("\nUsage: --recipe RECIPE_NAME --project-id PROJECT_ID")
        return

    # Recipe path (deterministic, no LLM)
    if recipe:
        if not project_id:
            click.echo("Error: --project-id required when using --recipe", err=True)
            raise click.Abort()

        # Parse variables
        variables = {}
        for var_str in var:
            if '=' not in var_str:
                click.echo(f"Error: Invalid --var format: {var_str} (expected key=value)", err=True)
                raise click.Abort()
            key, value = var_str.split('=', 1)
            variables[key] = value

        # Get recipe
        try:
            recipe_obj = registry.get(recipe)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            raise click.Abort()

        # Generate project
        output_path = Path(output_dir) / project_id
        click.echo(f"Generating project from recipe '{recipe}'...")
        click.echo(f"Output: {output_path}")
        if variables:
            click.echo(f"Variables: {variables}")

        recipe_obj.generate(output_path, variables)

        click.echo(f"✅ Project generated successfully at {output_path}")
        return

    # LLM path (existing implementation)
    if not goal:
        click.echo("Error: Either --recipe or GOAL required", err=True)
        raise click.Abort()

    # ... existing LLM-based generation code ...
```

#### Step 7: Test Recipe System (45 min)

```bash
# List recipes
docker exec project-builder python -m src.project_builder.cli.command --list-recipes

# Generate CI/CD project with defaults
docker exec project-builder python -m src.project_builder.cli.command \
  --recipe ci-cd-standard \
  --project-id test-cicd \
  --verbose

# Check output
docker exec project-builder ls -la /app/projects/test-cicd/
docker exec project-builder cat /app/projects/test-cicd/.github/workflows/ci.yml

# Generate with custom variables
docker exec project-builder python -m src.project_builder.cli.command \
  --recipe ci-cd-standard \
  --project-id test-cicd-custom \
  --var "python_version=3.12" \
  --var "test_framework=unittest" \
  --verbose

# Time comparison
time docker exec project-builder python -m src.project_builder.cli.command \
  --recipe ci-cd-standard --project-id recipe-test
# Should be < 1 second

time docker exec project-builder python -m src.project_builder.cli.command \
  "goal: CI/CD pipeline" --project-id llm-test --model mock
# Will be slower (if mock provider fixed)
```

#### Step 8: Auggie Re-test with Recipe (15 min)

Use Auggie to test recipe system:

```bash
# Task for Auggie:
docker exec project-builder python -m src.project_builder.cli.command --list-recipes
docker exec project-builder python -m src.project_builder.cli.command \
  --recipe ci-cd-standard \
  --project-id cicd-final \
  --output-dir /app/projects

# Extract artifacts
docker cp project-builder:/app/projects/cicd-final ./projects/

# Verify artifacts
ls -la ./projects/cicd-final/.github/workflows/
cat ./projects/cicd-final/README-CICD.md
```

### Acceptance Criteria

- ✅ CLI supports --list-recipes flag
- ✅ CLI supports --recipe flag
- ✅ CI/CD recipe generates all expected files
- ✅ Generated files are valid and usable
- ✅ Recipe generation completes in < 1 second
- ✅ Works offline (no network required)
- ✅ No LLM calls made (deterministic output)
- ✅ Auggie can successfully use recipe system
- ✅ Variables can customize output

### Files to Create

- `src/project_builder/recipes/__init__.py`
- `src/project_builder/recipes/base_recipe.py`
- `src/project_builder/recipes/recipe_registry.py`
- `src/project_builder/recipes/ci_cd_standard.py`
- `src/project_builder/recipes/templates/ci_cd/*.j2` (8 files)

### Files to Modify

- `src/project_builder/cli/command.py` - Add recipe support

---

## Summary of Immediate Actions

### Week 1: Critical Bugs (P0)

**Day 1-2: Bug #1 - MockLLMProvider JSON**
- [ ] Read current implementation
- [ ] Create mock_responses.json template file
- [ ] Update MockLLMProvider to use templates
- [ ] Add unit tests
- [ ] Verify with Auggie re-test

**Day 3: Bug #2 - LocalTongyiAdapter Signature**
- [ ] Examine interface contract
- [ ] Fix generate() signature
- [ ] Add interface conformance tests
- [ ] Verify all adapters match interface
- [ ] Test with Auggie re-test

### Week 2: High Priority (P1)

**Day 4-6: Issue #6 - Recipe System**
- [ ] Design recipe architecture
- [ ] Implement BaseRecipe class
- [ ] Implement CICDStandardRecipe
- [ ] Create Jinja2 templates
- [ ] Implement RecipeRegistry
- [ ] Update CLI with recipe support
- [ ] Test recipe system
- [ ] Auggie re-test with recipes

**Day 7: Documentation & Testing**
- [ ] Issue #5: Document Docker exec usage
- [ ] Create comprehensive test suite
- [ ] Update README with new features
- [ ] Final Auggie validation test

### Success Metrics

**After P0 Fixes**:
- ✅ Auggie can use Project Builder with mock provider
- ✅ Auggie can use Project Builder with tongyi-local provider
- ✅ All adapter interface tests pass

**After P1 Fixes**:
- ✅ Auggie can generate CI/CD pipeline in < 1 second using recipe
- ✅ Generated CI/CD artifacts are valid and usable
- ✅ Project Builder works offline without external LLM
- ✅ Documentation complete for all usage patterns

**Final Validation**:
- ✅ Run original meta-dogfooding task again
- ✅ Auggie successfully generates CI/CD automation
- ✅ Extract and integrate workflows into repository
- ✅ Document success in new dogfooding report

---

## Related Documentation

- **Meta-Dogfooding Report**: `docs/META_DOGFOODING_REPORT.md` (this bug fix plan's source)
- **Task Specification**: `.auggie_task_meta_dogfooding.txt`
- **Previous Dogfooding**: `docs/DOGFOODING_SUCCESS.md` (health check fix)
- **Security Incident**: `docs/REDIS_SECURITY_INCIDENT.md`

---

**Created**: 2025-10-11
**Status**: Ready for implementation
**Estimated Total Time**: 15-20 hours (P0-P1)
**Priority**: CRITICAL - Blocking external use of Project Builder
