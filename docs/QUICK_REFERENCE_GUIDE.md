# Quick Reference Guide: ATADO System

**Date**: 2025-10-17  
**Purpose**: Fast access to key information and commands  
**Audience**: Developers, operators, stakeholders

---

## System Overview

**Name**: Autonomous Task Agent Dev Orchestration (ATADO)  
**CLI**: `atado`  
**Status**: Production Ready (95% functionality)  
**Version**: Post-ATADO Integration (7/7 phases complete)

---

## Quick Start Commands

### Basic Usage

```bash
# Show help
atado --help

# Run with goal (natural language)
python -m src.main --goal "Build a REST API with authentication"

# Run with task
python -m src.main --task "Write unit tests for authentication module"

# Run with feedback loops
python -m src.main --task "..." --feedback-loops

# Run with state persistence
python -m src.main --task "..." --state-persistence "state.json"

# Run with caching (67%+ faster)
python -m src.main --workflow "..." --enable-cache
```

---

### Advanced Usage

```bash
# Team-based routing with scaled agents
python3 -m src.main \
  --provider auto \
  --routing team \
  --agents scaled \
  --orchestrator simple \
  --collect-metrics \
  --verbose \
  --task "ultrathink: <task description>"

# Multi-domain tasks (parallel execution)
python3 -m src.main \
  --task "Frontend: Build login UI" \
  --task "Backend: Create auth API" \
  --task "Testing: Write E2E tests" \
  --routing team \
  --agents scaled
```

---

## Agent Configurations

### Default (5 agents)
- coder, tester, reviewer, coordinator, researcher

### Extended (8 agents)
- Tier 1: master-orchestrator, architecture-lead
- Tier 2: frontend-lead, backend-lead, devops-lead
- Tier 3: python-specialist, unit-test-engineer, technical-writer

### Scaled (130 agents)
- Tier 1: 2 strategic agents
- Tier 2: 7 domain leads
- Tier 3: 121 specialists across 7 domains

**Usage**:
```bash
--agents default   # 5 agents
--agents extended  # 8 agents
--agents scaled    # 130 agents
```

---

## Key Features

### 1. Goal Mode (Phase 2)
**What**: Natural language goal specification  
**Command**: `--goal "Build a REST API"`  
**Benefit**: LLM-driven task decomposition

### 2. Feedback Loops (Phase 3)
**What**: Automatic replanning on failures  
**Command**: `--feedback-loops`  
**Benefit**: Self-healing execution

### 3. State Management (Phase 4)
**What**: Persistent world state  
**Command**: `--state-persistence "state.json"`  
**Benefit**: Context across executions

### 4. Workflow Caching (Phase 6)
**What**: Cache workflow results  
**Command**: `--enable-cache`  
**Benefit**: 67%+ performance improvement

---

## Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Tests
```bash
# Entity tests
pytest tests/unit/entity/ -v

# Use case tests
pytest tests/unit/use_cases/ -v

# Integration tests
pytest tests/integration/ -v

# With coverage
pytest --cov=src tests/
```

### Current Status
- **Total Tests**: 543
- **Status**: All passing (100%)
- **Coverage**: 85%

---

## Documentation Index

### Strategic Planning
1. `ATADO_INTEGRATION_STRATEGY.md` - Overall strategy
2. `ATADO_INTEGRATION_TECHNICAL_DETAILS.md` - Technical specs
3. `ATADO_INTEGRATION_EXECUTIVE_SUMMARY.md` - Executive overview
4. `ATADO_INTEGRATION_INDEX.md` - Documentation index

### Phase Reports
5. `PHASE1_ENTITY_CONSOLIDATION_COMPLETE.md`
6. `PHASE2_GOAL_DECOMPOSITION_COMPLETE.md`
7. `PHASE3_FEEDBACK_LOOPS_COMPLETE.md`
8. `PHASE4_STATE_MANAGEMENT_COMPLETE.md`
9. `PHASE5_EXECUTOR_CONSOLIDATION_COMPLETE.md`
10. `PHASE6_WORKFLOW_OPTIMIZATION_COMPLETE.md`
11. `PHASE7_CLEANUP_DOCUMENTATION_COMPLETE.md`

### Final Reports
12. `ATADO_INTEGRATION_FINAL_REPORT.md` - Complete project report
13. `NEXT_STAGE_ROADMAP.md` - Strategic next steps
14. `RAG_INTEGRATION_ACTION_PLAN.md` - 8-week RAG plan

### Analysis
15. `AGENT_SYSTEM_REVIEW.md` - Agent architecture
16. `ATADO_PHILOSOPHY_AND_PRINCIPLES.md` - Core philosophy
17. `SESSION_SUMMARY_2025_10_17.md` - Today's session
18. `QUICK_REFERENCE_GUIDE.md` - This document

---

## Architecture Quick Reference

### Clean Architecture Layers

```
┌─────────────────────────────────────┐
│         Interfaces (Abstract)       │
│  IAgentExecutor, ITextGenerator     │
└─────────────────────────────────────┘
           ↑
┌─────────────────────────────────────┐
│         Adapters (External)         │
│  LLM providers, CLI, Orchestrators  │
└─────────────────────────────────────┘
           ↑
┌─────────────────────────────────────┐
│       Use Cases (Business Logic)    │
│  TaskCoordinator, TaskPlanner       │
└─────────────────────────────────────┘
           ↑
┌─────────────────────────────────────┐
│       Entities (Core Domain)        │
│  Agent, Task, HTNNode, Team         │
└─────────────────────────────────────┘
```

**Rule**: Dependencies point inward (adapters → use cases → entities)

---

### Directory Structure

```
src/
├── entity/          # Core domain models
├── interface/       # Abstract contracts
├── use_cases/       # Business logic
├── adapters/        # External integrations
│   ├── llm/        # LLM providers
│   ├── agent/      # Agent implementations
│   ├── orchestration/  # Orchestrators
│   └── cli/        # CLI adapters
├── routing/         # Team-based routing
├── dsl/            # Category theory DSL
├── factories/       # Object creation
└── main.py         # CLI entry point
```

---

## Common Workflows

### Adding New Agent Type

1. Define entity in `src/entity/` (extend Agent)
2. Create interface in `src/interface/` (if needed)
3. Implement factory method in `src/factories/agent_factory.py`
4. Add routing logic in `src/routing/team_router.py`
5. Write tests in `tests/unit/entity/`
6. Update agent configs in `config/agents.yml`

### Adding New Use Case

1. Define interface in `src/interface/`
2. Implement use case in `src/use_cases/`
3. Add to composition root in `src/composition.py`
4. Write tests in `tests/unit/use_cases/`
5. Document in `docs/`

### Adding New CLI Option

1. Add option in `src/main.py` (Click decorator)
2. Pass to composition root
3. Update help text
4. Write integration test
5. Document in README

---

## Troubleshooting

### Tests Failing

```bash
# Run with verbose output
pytest tests/ -v -s

# Run specific test
pytest tests/unit/entity/test_agent.py::test_agent_creation -v

# Check coverage
pytest --cov=src --cov-report=html tests/
```

### Import Errors

```bash
# Reinstall in dev mode
pip install -e .

# Check Python path
python -c "import sys; print(sys.path)"
```

### Performance Issues

```bash
# Enable caching
python -m src.main --workflow "..." --enable-cache

# Check cache statistics
# (logged in verbose mode)
```

---

## Key Metrics

### Current Performance

| Metric | Value |
|--------|-------|
| Task Success Rate | 78% |
| Average Latency | 12.5s |
| Fallback Rate | 15% |
| Routing Accuracy | 85% |
| Test Coverage | 85% |
| Tests Passing | 543/543 (100%) |

### Target Performance (RAG Integration)

| Metric | Target |
|--------|--------|
| Task Success Rate | 90%+ |
| Average Latency | 8-10s |
| Fallback Rate | <5% |
| Routing Accuracy | 95%+ |

---

## Next Stage: RAG Integration

### Timeline
- **Week 1-2**: Foundation (SurrealDB, embeddings)
- **Week 3-4**: RAG-enhanced routing
- **Week 5-6**: Adaptive learning
- **Week 7-8**: Production & monitoring

### Budget
- SurrealDB Cloud Pro: $199.60 (2 months)
- OpenAI embeddings: $20 (2 months)
- **Total**: $220

### Expected Impact
- +15% success rate
- -20-36% latency
- Adaptive learning
- Context-aware routing

---

## Philosophy Quick Reference

### Core Principles (5 Pillars)

1. **Autonomous by Design** - Minimal human intervention
2. **Task-Centric Thinking** - Everything is decomposable
3. **Multi-Agent Collaboration** - Specialization + teams
4. **Orchestrated Execution** - Coordinated routing
5. **Dev-Focused** - Built for software development

### SOLID Principles

- **SRP**: Single Responsibility (one reason to change)
- **OCP**: Open-Closed (open for extension, closed for modification)
- **LSP**: Liskov Substitution (subtypes substitutable)
- **ISP**: Interface Segregation (small, specific interfaces)
- **DIP**: Dependency Inversion (depend on abstractions)

### Core Belief

**"Well-architected, principled systems scale; quick hacks don't."**

---

## Useful Links

### Documentation
- Main README: `README.md`
- Architecture: `docs/ATADO_PHILOSOPHY_AND_PRINCIPLES.md`
- Agent System: `docs/AGENT_SYSTEM_REVIEW.md`
- RAG Plan: `docs/RAG_INTEGRATION_ACTION_PLAN.md`

### Code
- Main Entry: `src/main.py`
- Entities: `src/entity/`
- Use Cases: `src/use_cases/`
- Tests: `tests/`

### Configuration
- Agents: `config/agents.yml`
- Priorities: `priorities.yaml`
- Settings: `config/claude_settings.json`

---

## Contact & Support

### Getting Help

1. Check documentation in `docs/`
2. Review test examples in `tests/`
3. Check CLAUDE.md for guidelines
4. Review session summaries in `docs/SESSION_SUMMARY_*.md`

### Reporting Issues

1. Check existing tests for similar scenarios
2. Write failing test demonstrating issue
3. Document expected vs actual behavior
4. Include relevant logs (use `--verbose`)

---

## Version History

### Current: Post-ATADO Integration (2025-10-17)
- 7/7 phases complete (100%)
- 543 tests (all passing)
- 85% test coverage
- Zero breaking changes
- Production ready

### Next: RAG Integration (8 weeks)
- Adaptive learning
- 90%+ success rate
- Context-aware routing

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-17  
**Status**: Current  
**Next Review**: After RAG integration

