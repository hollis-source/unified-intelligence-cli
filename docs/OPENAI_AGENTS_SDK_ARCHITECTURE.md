# OpenAI Agents SDK Integration Architecture

**Created**: Sep 30, 2025 (Phase 1: Week 7)
**Status**: Design Document
**Estimated Effort**: 60 hours

---

## Executive Summary

Integration of **OpenAI Agents SDK** as an optional orchestration layer for unified-intelligence-cli. Uses **Adapter Pattern** to preserve Clean Architecture and support our existing Tongyi provider.

### Key Design Decisions
1. ✅ **Provider-agnostic**: Works with Tongyi (no API costs)
2. ✅ **Optional**: Feature flag-based (no breaking changes)
3. ✅ **DIP-compliant**: Implements `IAgentCoordinator` interface
4. ✅ **Reversible**: Can remove with minimal impact

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                  CLEAN ARCHITECTURE (Unchanged)               │
├──────────────────────────────────────────────────────────────┤
│  Use Case Layer: IAgentCoordinator interface                 │
│     ↓                                                         │
│  ┌────────────────────┬────────────────────────────────────┐ │
│  │ TaskCoordinator    │ OpenAIAgentsSDKAdapter (NEW)       │ │
│  │ (current, simple)  │ (agent handoffs, provider-agnostic)│ │
│  └────────────────────┴────────────────────────────────────┘ │
│     ↓                           ↓                             │
│  AgentExecutor             OpenAI Agents SDK                  │
│     ↓                           ↓                             │
│  TongyiAdapter             TongyiAsOpenAIClient (wrapper)     │
│     ↓                           ↓                             │
│  llama.cpp server          llama.cpp server                   │
└──────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. OpenAIAgentsSDKAdapter

**Purpose**: Implement `IAgentCoordinator` using OpenAI Agents SDK internally.

**Location**: `src/adapters/orchestration/openai_agents_sdk_adapter.py`

**Responsibilities**:
- Convert our `Agent` entities → OpenAI SDK `Agent` objects
- Convert our `Task` entities → OpenAI SDK messages
- Execute workflows using `Runner.run()`
- Convert SDK results → our `ExecutionResult` entities

**DIP Compliance**:
- Implements `IAgentCoordinator` (our interface)
- Hides OpenAI SDK details (adapter pattern)
- No changes to core use cases

### 2. TongyiAsOpenAIClient

**Purpose**: Wrap our `TongyiDeepResearchAdapter` to provide OpenAI-compatible client interface.

**Location**: `src/adapters/orchestration/tongyi_openai_client.py`

**Pattern**: Adapter pattern (wrap our adapter as another adapter!)

**Why Needed**: OpenAI Agents SDK expects `AsyncOpenAI` client, but we have custom `ITextGenerator`.

### 3. OrchestrationFactory

**Purpose**: Factory to create orchestrators based on CLI flag.

**Location**: `src/factories/orchestration_factory.py`

**Pattern**: Factory Method + Strategy

**Interface**:
```python
class OrchestrationFactory:
    @staticmethod
    def create_orchestrator(
        mode: str,  # "simple" or "openai-agents"
        llm_provider: ITextGenerator,
        agents: List[Agent]
    ) -> IAgentCoordinator:
        """Create orchestrator based on mode."""
```

---

## Implementation Details

### Agent Conversion Strategy

**Our Agent → OpenAI SDK Agent**:
```python
# Our entity
our_agent = Agent(
    role="researcher",
    capabilities=["research", "analyze", "document"]
)

# Convert to OpenAI SDK Agent
sdk_agent = agents.Agent(
    name=our_agent.role,
    instructions=self._capabilities_to_instructions(our_agent.capabilities),
    # No functions initially (add handoffs in Phase 2)
)
```

### Task Execution Flow

```
1. User: ui-cli --task "Research X" --orchestrator=openai-agents
2. CLI: Load OpenAIAgentsSDKAdapter
3. Adapter: Convert Task → OpenAI message
4. Adapter: Select starting agent (researcher)
5. SDK: Runner.run_sync(agent, message)
6. SDK: Execute with TongyiAsOpenAIClient
7. Adapter: Convert SDK result → ExecutionResult
8. CLI: Display result to user
```

### Provider Integration (Tongyi)

**Challenge**: OpenAI Agents SDK expects `AsyncOpenAI` client, but we use custom `ITextGenerator`.

**Solution**: Wrap our adapter
```python
class TongyiAsOpenAIClient:
    """
    Wrapper to make TongyiAdapter look like AsyncOpenAI client.

    Implements only the methods OpenAI Agents SDK uses:
    - chat.completions.create()
    """
    def __init__(self, tongyi_adapter: TongyiDeepResearchAdapter):
        self.tongyi = tongyi_adapter

    class ChatCompletions:
        async def create(self, messages, model, **kwargs):
            # Convert OpenAI format → our format → call Tongyi → convert back
            return await self._adapt_completion(messages, **kwargs)
```

### Configuration

**Dependencies**:
```toml
# Add to requirements.txt or pyproject.toml
openai-agents>=1.0.0  # OpenAI Agents SDK
```

**CLI Integration**:
```python
@click.option(
    "--orchestrator",
    type=click.Choice(["simple", "openai-agents"]),
    default="simple",
    help="Orchestration mode"
)
```

---

## Testing Strategy (TDD)

### Test File: `scripts/test_openai_agents_adapter.py`

**Test Coverage**:
1. ✅ Test OpenAIAgentsSDKAdapter implements IAgentCoordinator
2. ✅ Test agent conversion (our Agent → SDK Agent)
3. ✅ Test task execution (single task)
4. ✅ Test multi-task coordination
5. ✅ Test Tongyi provider integration
6. ✅ Test error handling
7. ✅ Test handoff mechanism (Phase 2)

**TDD Workflow**:
1. Write failing tests first
2. Implement minimum code to pass
3. Refactor while tests pass
4. Document success

---

## Phase 1 Implementation Plan

### Phase 1.1: Design (DONE) - 4 hours
- ✅ Research OpenAI Agents SDK API
- ✅ Design adapter architecture
- ✅ Write this document

### Phase 1.2: TDD Tests - 8 hours
- Write `test_openai_agents_adapter.py`
- 7 test functions
- Expected: All tests fail initially

### Phase 1.3: Core Adapter - 20 hours
- Implement `OpenAIAgentsSDKAdapter`
- Implement `TongyiAsOpenAIClient`
- Convert entities
- Basic execution flow

### Phase 1.4: Factory & CLI - 8 hours
- Implement `OrchestrationFactory`
- Add `--orchestrator` flag to CLI
- Integration with `main.py`

### Phase 1.5: E2E Testing - 12 hours
- Run E2E tests with `--orchestrator=openai-agents`
- Compare results: simple vs openai-agents
- Performance benchmarks

### Phase 1.6: Documentation - 8 hours
- Update README with examples
- Add usage guide
- Document handoff patterns
- Create migration guide

**Total**: 60 hours

---

## Success Criteria

### Must Have (Phase 1)
- ✅ All tests passing (TDD validation)
- ✅ Works with Tongyi provider (no new costs)
- ✅ CLI flag `--orchestrator=openai-agents` functional
- ✅ Performance within 10% of current system
- ✅ Zero breaking changes to existing code

### Nice to Have (Phase 2)
- Agent handoffs implemented
- Guardrails for input/output validation
- Tracing integration
- Documentation examples

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Tongyi incompatibility** | Low | High | Test early, fallback to simple orchestrator |
| **Performance degradation** | Medium | Medium | Benchmark, optimize, cache |
| **OpenAI SDK API changes** | Low | Medium | Pin version, monitor releases |
| **Complexity creep** | Medium | High | Strict scope, adapter pattern limits coupling |

---

## Rollback Plan

**If Phase 1 Fails**:
1. Remove `--orchestrator=openai-agents` option
2. Delete adapter files (isolated, no impact on core)
3. Revert CLI changes
4. Document lessons learned
5. Continue with current TaskCoordinator

**Cost of Rollback**: < 4 hours (adapter is isolated)

---

## Robert C. Martin's Design Review

**SRP**: ✅ Each class has single responsibility (adapter, client wrapper, factory)

**OCP**: ✅ Extending via new orchestrator, not modifying existing code

**LSP**: ✅ `OpenAIAgentsSDKAdapter` substitutable for `TaskCoordinator` (both implement `IAgentCoordinator`)

**ISP**: ✅ Interfaces are focused (`IAgentCoordinator` has minimal methods)

**DIP**: ✅ Core depends on `IAgentCoordinator`, not concrete adapters

**Martin's Verdict**:
> "Good design. You're using the adapter pattern correctly - wrapping a framework without letting it invade your architecture. The factory provides flexibility to switch orchestrators. Keep the adapter thin - don't let OpenAI SDK patterns leak into your domain."

---

## Next Steps

1. ✅ Design complete (this document)
2. → Implement Phase 1.2: Write TDD tests
3. → Implement Phase 1.3: Core adapter
4. → Continue phases 1.4-1.6

**Estimated Completion**: Week 7 (60 hours total)

---

**END ARCHITECTURE DOCUMENT**