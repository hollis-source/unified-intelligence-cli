# Unified Intelligence CLI

![Tests](https://github.com/username/unified-intelligence-cli/workflows/Tests/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen)

**Production-ready multi-agent task orchestration framework** following Clean Architecture principles.

A CLI tool that intelligently distributes tasks to specialized agents (coder, tester, reviewer, researcher, coordinator) using LLM-powered execution with tool support. Inspired by *AI Agents in Action* and Robert C. Martin's Clean Code principles.

## Features

✅ **Multi-Task CLI**: Accept multiple tasks in a single command
✅ **Intelligent Agent Selection**: Fuzzy matching assigns tasks to best-fit agents
✅ **Tool Support**: Agents can execute shell commands, read/write files, run tests
✅ **LLM Providers**: Mock (testing) and Grok (production) with extensible architecture
✅ **Parallel Execution**: Concurrent task processing with dependency handling
✅ **Clean Architecture**: Entities → Use Cases → Interfaces → Adapters
✅ **85% Test Coverage**: 104 tests (73 unit + 31 integration)

## Quick Start

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure API key (for Grok provider)
echo "XAI_API_KEY=your_api_key_here" > .env

# Run with mock provider (no API needed)
python3 src/main.py \
  --task "Write a Python function for factorial" \
  --task "Write tests for factorial function" \
  --provider mock

# Run with live Grok (requires API key)
python3 src/main.py \
  --task "Implement FizzBuzz in Python" \
  --task "Create comprehensive tests" \
  --task "Run the tests and report results" \
  --provider grok \
  --verbose
```

## Usage Examples

### Single Task

```bash
python3 src/main.py --task "Review the codebase for security issues" --provider mock
```

### Multi-Task Workflow

```bash
python3 src/main.py \
  --task "Implement binary search function" \
  --task "Write unit tests with edge cases" \
  --task "Review code for optimization opportunities" \
  --provider grok \
  --verbose
```

### With Timeout and Parallel Execution

```bash
python3 src/main.py \
  --task "Analyze performance bottlenecks" \
  --task "Generate optimization report" \
  --provider grok \
  --timeout 120 \
  --parallel
```

### With Configuration File

```bash
# Create config file (see config.example.json)
python3 src/main.py \
  --task "Implement feature X" \
  --task "Write tests for feature X" \
  --config config.example.json \
  --verbose  # CLI args override config file
```

### End-to-End Demo

```bash
# Run complete dev workflow demo (requires API key)
python3 demo_full_workflow.py
```

## Architecture

```
src/
├── entities/          # Core business objects (Agent, Task, ExecutionResult)
├── use_cases/         # Business logic (TaskCoordinator, TaskPlanner)
├── interfaces/        # Abstractions (ITextGenerator, IAgentExecutor)
├── adapters/          # External integrations
│   ├── llm/          # LLM providers (GrokAdapter, MockProvider)
│   ├── agent/        # Agent implementations (LLMAgentExecutor)
│   └── cli/          # CLI adapters (ResultFormatter)
├── factories/         # Dependency Injection (AgentFactory, ProviderFactory)
├── composition.py     # Composition root
├── tools.py           # Dev tools (run_command, read_file, write_file, list_files)
└── main.py            # CLI entry point
```

### Clean Architecture Layers

1. **Entities** (innermost): Core business objects with no external dependencies
2. **Use Cases**: Business logic orchestrating entities
3. **Interfaces**: Abstractions following Dependency Inversion Principle
4. **Adapters** (outermost): External integrations (LLMs, CLI, tools)

**Dependency Rule**: Dependencies point inward only. Inner layers never depend on outer layers.

## Security

This CLI enables LLM agents to execute shell commands and file operations. See [SECURITY.md](SECURITY.md) for:
- Command execution security model
- File operation safety
- API key protection
- Best practices and threat model

**TL;DR**: The CLI is a power tool for trusted local development. Run in isolated workspaces, review agent actions, use version control, and see SECURITY.md for full details.

## Development

### Run Tests

```bash
source venv/bin/activate
PYTHONPATH=. pytest tests/ -v
```

### Check Coverage

```bash
PYTHONPATH=. pytest tests/ --cov=src --cov-report=term-missing
```

### Add New Agent Type

```python
# src/factories/agent_factory.py
Agent(
    role="your_role",
    capabilities=["capability1", "capability2"]
)
```

### Add New LLM Provider

1. Implement `ITextGenerator` interface in `src/adapters/llm/`
2. Register in `ProviderFactory.create_provider()`
3. Add tests in `tests/integration/test_provider_integration.py`

### Add New Tool

Use the extensible tool registry for easy registration:

```python
# In your module
from src.tool_registry import default_registry

@default_registry.register(
    name="your_tool",
    description="What your tool does",
    parameters={
        "param": {"type": "string", "description": "Parameter description"}
    },
    required=["param"]
)
def your_tool(param: str) -> str:
    """Tool implementation."""
    return result
```

Tools are automatically available to LLM providers via `DEV_TOOLS` and `TOOL_FUNCTIONS`.

### CI/CD

GitHub Actions workflows automatically run on push/PR:

- **Tests**: Run full test suite on Python 3.10, 3.11, 3.12
- **Coverage**: Generate and upload coverage reports
- **Linting**: Check code style with flake8
- **Security**: Scan with bandit and safety

See [.github/workflows/tests.yml](.github/workflows/tests.yml) for configuration.

## Project Structure

- `src/`: Production code (Clean Architecture layers)
- `tests/`: Unit and integration tests (TDD approach)
- `scripts/`: Utilities (GrokSession, API clients)
- `demo_full_workflow.py`: End-to-end workflow demonstration
- `REFACTORING_ASSESSMENT.md`: Code quality analysis

## Testing Strategy

- **Unit Tests** (73): Test entities, use cases, tools, and CLI logic in isolation
- **Integration Tests** (31): Test component interactions, end-to-end workflows, and real file operations
- **Coverage**: 85% (tools: 96%, composition: 100%, use cases: 87-89%)

## Configuration

### Environment Variables (`.env` file)

```bash
XAI_API_KEY=your_grok_api_key_here
```

### Configuration File (Optional)

Use `--config` flag to load settings from JSON file. CLI arguments override config file values.

Example `config.json`:
```json
{
  "provider": "grok",
  "provider_config": {
    "model": "grok-code-fast-1",
    "temperature": 0.7
  },
  "parallel": true,
  "timeout": 120,
  "verbose": true,
  "custom_agents": [
    {
      "role": "security_analyst",
      "capabilities": ["security", "audit", "vulnerability"]
    }
  ]
}
```

See `config.example.json` for complete example.

## Roadmap

**Completed (100% Core Functionality):**
- ✅ Multi-task CLI input
- ✅ Intelligent agent selection with fuzzy matching
- ✅ Tool-supported LLM execution
- ✅ Clean Architecture foundation
- ✅ End-to-end dev workflow demo

**Future Enhancements:**
- 🔄 Runtime provider switching via --config flag
- 🔄 Additional LLM providers (OpenAI, Anthropic)
- 🔄 Persistent task history and context
- 🔄 Web UI for task management
- 🔄 Plugin system for custom agents and tools

## Principles

This project follows:
- **Clean Code** (Robert C. Martin): Small functions, meaningful names, explicit error handling
- **Clean Architecture**: Dependency inversion, use case-driven design
- **SOLID Principles**: SRP, OCP, LSP, ISP, DIP
- **TDD**: Tests first, refactor later
- **Pragmatic**: Fact-based decisions, avoid premature optimization

See `CLAUDE.md` for development guidelines.