# ATADO Philosophy and Principles

**Date**: 2025-10-17  
**Source**: CLAUDE.md  
**Purpose**: Core philosophy guiding ATADO development

---

## Project Identity

**Name**: Autonomous Task Agent Dev Orchestration (ATADO)  
**CLI**: `atado`  
**Mission**: Accelerate software development through autonomous multi-agent orchestration

---

## Core Philosophy

### 1. **Autonomous by Design**

**Principle**: Minimal human intervention, maximum self-direction

**Implementation**:
- Priority queue-driven execution
- Self-directed task decomposition
- Automatic replanning on failures
- Adaptive learning from patterns

**Why**: Humans should focus on high-level goals, not micro-management

---

### 2. **Task-Centric Thinking**

**Principle**: Everything is a task that can be decomposed

**Implementation**:
- Hierarchical Task Networks (HTN)
- Goal → HTN → Tasks → Execution
- Natural language goal specification
- Automatic task decomposition

**Why**: Tasks are the atomic unit of work, composable and parallelizable

---

### 3. **Multi-Agent Collaboration**

**Principle**: Specialized agents working together > generalist agents

**Implementation**:
- 5-130 agents across 7 domains
- 3-tier hierarchy (strategic, leads, specialists)
- Team-based routing (50% fewer decisions)
- Domain expertise (frontend, backend, testing, QA, research, devops, DSL)

**Why**: Specialization enables expertise, teams enable collaboration

---

### 4. **Orchestrated Execution**

**Principle**: Coordinated execution with intelligent routing

**Implementation**:
- Two-phase routing (domain → team → agent)
- Hybrid orchestration (simple, hybrid)
- Feedback loops for replanning
- State management for context

**Why**: Coordination prevents chaos, routing ensures right agent for right task

---

### 5. **Dev-Focused**

**Principle**: Built for software development workflows

**Implementation**:
- Refactoring, testing, code review
- Architecture decisions
- Performance analysis
- Documentation generation

**Why**: Generic tools lack domain expertise, specialized tools excel

---

## Robert C. Martin's Principles

### Clean Code

**Functions**:
- Small (under 20 lines)
- Meaningful names revealing intent
- Single responsibility
- Explicit error handling

**Example**:
```python
# Good: Small, clear, single responsibility
def calculate_success_rate(successful: int, total: int) -> float:
    """Calculate success rate as percentage."""
    if total == 0:
        return 0.0
    return (successful / total) * 100

# Bad: Too large, multiple responsibilities
def process_results(results):
    # 50 lines of mixed logic...
```

---

### Clean Architecture

**Layers**:
1. **Entities** (center): Agent, Task, HTNNode, Team
2. **Use Cases**: TaskCoordinator, TaskPlanner, GoalDecomposer
3. **Adapters**: LLM providers, CLI, orchestrators
4. **Interfaces**: IAgentExecutor, ITextGenerator, ITaskPlanner

**Dependency Rule**: Dependencies point inward (adapters → use cases → entities)

**Why**: Protects business logic from frameworks, enables testability

---

### Clean Agile

**Practices**:
- Small, frequent commits (30-60 min, 200-500 lines)
- Descriptive commit messages (what and why, not how)
- Incremental development (small, deliverable increments)
- Continuous refactoring (not a separate phase)
- Test-Driven Development (TDD)

**Example Commit**:
```
feat: Add RAG-enhanced routing for adaptive agent selection

Integrates SurrealDB GraphRAG with TeamRouter to enable learning
from execution patterns. Routes tasks based on historical success
rates and similar task patterns.

Benefits:
- +15% task success rate (78% → 90%+)
- -20-36% latency reduction
- Continuous learning and optimization
```

---

### SOLID Principles

**Single Responsibility (SRP)**:
- One reason to change per class
- Example: Separate routing from execution

**Open-Closed (OCP)**:
- Open for extension, closed for modification
- Example: Add new agent types without modifying router

**Liskov Substitution (LSP)**:
- Subtypes substitutable without breaking
- Example: All agents follow IAgentExecutor contract

**Interface Segregation (ISP)**:
- Small, specific interfaces
- Example: ITextGenerator, IAgentSelector, ITaskPlanner separate

**Dependency Inversion (DIP)**:
- Depend on abstractions, not concretions
- Example: Inject providers, executors, routers

---

## Key Design Goals

### 1. **Modularity**

**What**: Swappable components

**Implementation**:
- LLM providers (OpenAI, Anthropic, Grok, local)
- Orchestration strategies (simple, hybrid)
- Routing algorithms (keyword, team, RAG)

**Why**: Flexibility, experimentation, optimization

---

### 2. **Testability**

**What**: Easy to test, mock, verify

**Implementation**:
- Mock-friendly interfaces
- Dependency injection throughout
- 543 tests (85% coverage)

**Why**: Confidence in changes, regression prevention

---

### 3. **Autonomy**

**What**: Self-directed execution

**Implementation**:
- Priority queue-driven
- Automatic replanning
- Adaptive learning (RAG)

**Why**: Minimal human intervention, maximum throughput

---

### 4. **Extensibility**

**What**: Easy to add new capabilities

**Implementation**:
- Add new agent types (6 steps)
- Add new orchestration strategies (5 steps)
- Add new workflow patterns (DSL)

**Why**: Future-proof, adaptable to new requirements

---

### 5. **Observability**

**What**: Understand what's happening

**Implementation**:
- Metrics collection (success rate, latency, routing accuracy)
- Logging (verbose, debug modes)
- Error handling (comprehensive, actionable)
- Monitoring dashboard (Grafana)

**Why**: Data-driven optimization, debugging, accountability

---

## Dogfooding Directive

**Principle**: Use our own tools to validate and improve them

**When to Dogfood**:
- Research tasks requiring distributed analysis
- Complex debugging requiring multi-agent collaboration
- Code review across multiple domains
- Performance analysis and optimization
- Architecture and design decisions

**How to Dogfood**:
```bash
python3 -m src.main \
  --provider auto \
  --routing team \
  --agents scaled \
  --orchestrator simple \
  --collect-metrics \
  --verbose \
  --task "ultrathink: <task description>"
```

**Benefits**:
- Validates system architecture
- Discovers bugs and limitations
- Demonstrates distributed computing
- Proves team-based routing effectiveness

---

## Team-Based Architecture

**Core Concept**: Route to teams, not individual agents

**Architecture**:
```
Task → Router → Team (domain) → Team Internal Logic → Agent
```

**Benefits**:
- 50% fewer routing decisions (7 teams vs 12 agents)
- Encapsulated team logic (teams know nuanced differences)
- Solves capability overlap (unit vs integration testing)
- Natural scalability (add agents to teams, not router)
- Mirrors real organizations

**When to Use**:
- 8+ agents: Consider team-based routing
- 12+ agents: Strongly recommended
- 14+ agents: QA and Testing should be separate teams

---

## Critical Distinctions

### Testing Team vs QA Team

**Testing Team** (Technical Quality):
- Unit tests, integration tests, E2E tests
- Performance testing, security testing
- Keywords: "unit", "integration", "pytest", "mock", "selenium"

**QA Team** (User/Product Quality):
- Acceptance testing, BDD/Gherkin scenarios
- Exploratory testing, test planning
- Keywords: "acceptance", "bdd", "gherkin", "user journey", "exploratory"

**Why Separate**: Different mindsets, different tools, different goals

---

## Development Practices

### Think Step by Step

**Principle**: Plan extensively before acting

**Implementation**:
- Use "think" or "ultrathink" directives
- Break down problems into small steps
- Base plans on verifiable facts and data
- Challenge assumptions critically

**Why**: Prevents mistakes, ensures quality, enables learning

---

### Security and Best Practices

**Principles**:
- Operate as non-root user
- Use virtual environments
- Never commit secrets or untested code
- Store API keys in .env files
- Never hardcode sensitive data

**Why**: Security, reproducibility, professionalism

---

### Response Structure

**Format**:
- Use markdown for outputs
- Sections: Plan, Code, Tests, Critique
- Enclose code in fenced blocks
- Use XML tags for structured thinking
- Always critique against facts, data, principles

**Why**: Clarity, actionability, learning

---

## Code Style

**PEP 8 Compliance**:
- Black formatter (line length 100)
- Type hints (all function signatures)
- Google-style docstrings
- Descriptive naming (verb_noun for functions)
- Grouped imports (stdlib, third-party, local)

**Why**: Consistency, readability, maintainability

---

## Current State (October 2025)

**System Functionality**: 95%

**Agent Count**: 14 agents across 6 teams
- Tier 1: 2 strategic agents
- Tier 2: 6 domain leads
- Tier 3: 6 specialists

**Routing**: Domain → Team → Agent (weighted classifier)

**Recent Achievements**:
- ATADO integration complete (7/7 phases, 100%)
- 543 tests (all passing)
- 85% test coverage
- Zero breaking changes
- 67%+ performance improvement (caching)

**Next Stage**: RAG integration (8 weeks)
- Adaptive learning from execution patterns
- +15% success rate (78% → 90%+)
- -20-36% latency reduction

---

## Philosophy in Action

### Example: ATADO Integration

**Challenge**: Integrate 7 major features without breaking changes

**Approach**:
1. **Phased**: 7 phases over 7 hours
2. **Tested**: 86 new tests (all passing)
3. **Documented**: 4,500+ lines of documentation
4. **Clean**: Zero breaking changes
5. **Principled**: SOLID throughout

**Result**: 100% complete, production-ready

**Lesson**: Methodical, principled approach > quick hacks

---

## Conclusion

ATADO's philosophy is grounded in:
- **Autonomy**: Self-directed execution
- **Specialization**: Right agent for right task
- **Collaboration**: Teams working together
- **Quality**: Clean Code, Clean Architecture, Clean Agile
- **Principles**: SOLID, TDD, continuous refactoring
- **Pragmatism**: Dogfooding, data-driven decisions

**Core Belief**: Well-architected, principled systems scale; quick hacks don't.

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-17  
**Source**: CLAUDE.md  
**Status**: Living document (evolves with system)

