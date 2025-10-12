# Contributing Guidelines

Development guidelines for the Unified Intelligence CLI project, based on Robert C. Martin's Clean Code, Clean Architecture, and Clean Agile principles.

## Core Development Principles

### Think Step by Step
- Break down problems into small, iterative steps
- Base plans on verifiable facts and data, not assumptions
- Document design decisions with rationale

### Security and Best Practices
- Use virtual environments for dependencies (`python3 -m venv venv`)
- Never commit secrets or untested code
- Store API keys in `.env` files (load via `python-dotenv`)
- Add `.env` to `.gitignore`
- Never hardcode sensitive data

### Code Review Standards
- Critique against facts, data, and principles
- Point out risks and suggest better alternatives
- Challenge assumptions constructively
- Prioritize maintainability over quick fixes

## Clean Code Principles (Robert C. Martin)

### Functions
- **Small**: Aim for <20 lines (guideline, not absolute rule)
- **Meaningful names**: Reveal intent (`calculate_match_score` not `calc`)
- **Single responsibility**: One reason to change
- **Explicit error handling**: No silent failures

### Duplication
- Eliminate duplication via abstraction
- Use inheritance, composition, or generics appropriately

### Testing
- **TDD**: Write tests first, implement to pass
- Minimum 70% code coverage
- Test behavior, not implementation

## Clean Architecture Principles

### Layer Structure
```
┌─────────────────────────────────────┐
│         Adapters (outermost)        │  CLI, LLM providers, external APIs
│  ┌───────────────────────────────┐  │
│  │      Interfaces & Factories   │  │  Abstractions, DIP boundaries
│  │  ┌─────────────────────────┐  │  │
│  │  │      Use Cases          │  │  │  Business logic
│  │  │  ┌───────────────────┐  │  │  │
│  │  │  │    Entities       │  │  │  │  Core business objects
│  │  │  │   (innermost)     │  │  │  │
│  │  │  └───────────────────┘  │  │  │
│  │  └─────────────────────────┘  │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

### Dependency Rule
**Dependencies point inward only.** Inner layers never depend on outer layers.

- **Entities**: Core business objects (Agent, Task, ExecutionResult)
  - No external dependencies
  - Pure Python dataclasses

- **Use Cases**: Business logic (TaskCoordinator, TaskPlanner)
  - Depend on entities and interfaces
  - Orchestrate workflows

- **Interfaces**: Abstractions (ITextGenerator, IAgentExecutor)
  - Define contracts for adapters
  - Enable Dependency Inversion Principle

- **Adapters**: External integrations (GrokAdapter, CLI, tools)
  - Depend on interfaces
  - Implement external protocols

### Key Architectural Patterns

- **Composition Root** (`composition.py`): Wire dependencies
- **Factory Pattern**: Create objects without exposing instantiation logic
- **Adapter Pattern**: Translate external APIs to internal interfaces
- **Strategy Pattern**: Swap implementations at runtime (providers)

## SOLID Principles

### Single Responsibility (SRP)
One reason to change per class/module.
```python
# Good: Separate concerns
class TaskCoordinator:  # Orchestration only
class TaskPlanner:      # Planning only
class LLMAgentExecutor: # Execution only
```

### Open-Closed (OCP)
Open for extension, closed for modification.
```python
# Good: Add new providers without modifying factory
class ProviderFactory:
    def create_provider(self, provider_type: str):
        return self._creators[provider_type]()
```

### Liskov Substitution (LSP)
Subtypes must be substitutable for their base types.
```python
# Good: All providers implement ITextGenerator
def process(provider: ITextGenerator):
    result = provider.generate(messages)  # Works for any provider
```

### Interface Segregation (ISP)
Small, specific interfaces.
```python
# Good: Separate interfaces for different capabilities
class ITextGenerator(Protocol): ...
class IToolSupportedProvider(ITextGenerator): ...
```

### Dependency Inversion (DIP)
Depend on abstractions, not concretions.
```python
# Good: Inject abstraction
class LLMAgentExecutor:
    def __init__(self, llm_provider: ITextGenerator):
        self.llm_provider = llm_provider
```

## Development Workflow

### 1. Explore and Plan
- Analyze requirements thoroughly
- Search for existing implementations (GitHub, documentation)
- Create plan with clear steps
- Document design decisions

### 2. Code and Test (TDD)
```bash
# 1. Write failing test
pytest tests/unit/test_new_feature.py -v  # Fails

# 2. Implement minimum code to pass
# Edit src/...

# 3. Verify test passes
pytest tests/unit/test_new_feature.py -v  # Passes

# 4. Refactor
# Improve code quality while keeping tests green
```

### 3. Iterate and Commit
- **Small commits**: One logical change per commit
- **Descriptive messages**: Explain why, not just what
- **Run tests**: Ensure all tests pass before committing
```bash
PYTHONPATH=. pytest tests/ -v
git add <files>
git commit -m "Feat: Add fuzzy matching to agent selection

Implements difflib-based scoring to improve agent assignment.
Addresses issue where generic capabilities caused false matches.
Tests: Added 3 test cases for scoring algorithm."
```

### 4. Review and Refine
- Check coverage: `pytest --cov=src --cov-report=term-missing`
- Run analysis: `python analyze_functions.py`
- Update documentation as needed

## Project-Specific Guidelines

### Adding a New Agent
```python
# src/factories/agent_factory.py
Agent(
    role="researcher",
    capabilities=["research", "investigate", "analyze", "document"]
)
```

### Adding a New LLM Provider
1. Implement interface in `src/adapters/llm/your_provider.py`:
```python
from src.interfaces import ITextGenerator

class YourProvider(ITextGenerator):
    def generate(self, messages, config): ...
```

2. Register in `ProviderFactory`:
```python
"your_provider": lambda config: self._create_your_provider(config)
```

3. Add integration tests in `tests/integration/test_provider_integration.py`

### Adding a New Tool
```python
# src/tools.py

def your_tool(param: str) -> str:
    """Brief description."""
    try:
        # Implementation
        return result
    except Exception as e:
        return f"Error: {str(e)}"

# Add to DEV_TOOLS list (OpenAI function format)
# Add to TOOL_FUNCTIONS registry
```

## Testing Standards

### Test Structure
```
tests/
├── unit/              # Fast, isolated tests
│   ├── test_agent.py
│   └── test_coordinator_use_case.py
└── integration/       # Component interaction tests
    ├── test_provider_integration.py
    └── test_task_coordination_integration.py
```

### Coverage Targets
- **Unit tests**: 100% for entities and interfaces
- **Integration tests**: Cover all major workflows
- **Overall**: Minimum 70% (current: 70%)

### Running Tests
```bash
# All tests
PYTHONPATH=. pytest tests/ -v

# Specific test file
PYTHONPATH=. pytest tests/unit/test_agent.py -v

# With coverage
PYTHONPATH=. pytest tests/ --cov=src --cov-report=term-missing

# Parallel execution (faster)
PYTHONPATH=. pytest tests/ -n auto
```

## Code Style

### Python Standards
- **PEP 8**: Standard Python style guide
- **Type hints**: Use everywhere possible
- **Docstrings**: All public functions and classes
- **Imports**: Standard library → third party → local

### Example
```python
from typing import List, Optional
from src.entities import Agent, Task
from src.interfaces import ITextGenerator

class LLMAgentExecutor:
    """
    Execute agents using LLM for task completion.

    Args:
        llm_provider: LLM for agent intelligence
        default_config: Default LLM configuration
    """

    def __init__(
        self,
        llm_provider: ITextGenerator,
        default_config: Optional[LLMConfig] = None
    ) -> None:
        self.llm_provider = llm_provider
        self.default_config = default_config or LLMConfig()

    async def execute(
        self,
        agent: Agent,
        task: Task
    ) -> ExecutionResult:
        """Execute task using agent's capabilities."""
        messages = self._build_messages(agent, task)
        response = self.llm_provider.generate(messages)
        return ExecutionResult(status=ExecutionStatus.SUCCESS, output=response)
```

## Common Commands

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Development
PYTHONPATH=. pytest tests/ -v                    # Run tests
PYTHONPATH=. pytest tests/ --cov=src             # With coverage
python analyze_functions.py                       # Check function lengths

# Run CLI
python3 src/main.py --task "Your task" --provider mock -v

# Demo
python3 demo_full_workflow.py                     # End-to-end workflow
python3 test_tools_demo.py                        # Tool integration
```

## Philosophy

### Pragmatic Principles
- **Facts over opinions**: Base decisions on data, not preferences
- **Maintainability over metrics**: 70% coverage with good tests beats 100% with bad tests
- **Clarity over cleverness**: Readable code > clever code
- **Iteration over perfection**: Ship working code, refactor later

### When to Refactor
✅ **Refactor when:**
- Adding new features to existing code
- Tests are hard to write
- Code is duplicated in multiple places
- Clear SRP violations exist

❌ **Don't refactor when:**
- Code works and is well-tested
- Only metric (line count) is violated
- No maintenance pain exists
- Would reduce clarity

### Design Decision Criteria
1. Does it follow SOLID principles?
2. Is it testable?
3. Is it maintainable?
4. Does it solve a real problem?
5. Is there data/evidence supporting this approach?

## Resources

- **Clean Code** by Robert C. Martin
- **Clean Architecture** by Robert C. Martin
- **Clean Agile** by Robert C. Martin
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [The Twelve-Factor App](https://12factor.net/)

## Questions?

- Check `README.md` for quick start and usage
- Review `REFACTORING_ASSESSMENT.md` for code quality guidelines
- Examine existing code for patterns and examples