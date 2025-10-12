# Architectural Query for Agentic Project Builder

## Context
I have provided comprehensive documentation of our unified-intelligence-cli system in PROJECT_BUILDER_CONTEXT.md. Please review it thoroughly before proceeding.

## Your Task

Design a **production-ready architecture blueprint** for an **Agentic Assisted Project Builder** that integrates all our existing capabilities into a unified system.

## Requirements

### Core Integration
The architecture MUST integrate these existing production-ready components:

1. **HTN (Hierarchical Task Network)** - Recursive task decomposition with preconditions/effects
2. **Category Theory DSL** - Workflow composition with ∘ (composition), × (product), functors
3. **Adaptive Learning** - Task-aware model selection (23.5% latency improvement proven)
4. **Multi-Agent Teams** - 16 agents across 9 domains with team-based routing
5. **Premium Reasoning Model** - Qwen3-Next-80B-Thinking for complex architectural decisions
6. **CLI Interface** - Unified command-line entry point

### Exclusions
- ❌ **Resource Pool**: Do NOT include resource management components (keep architecture simple)

### Use Case
**Primary**: User provides project goal in natural language → System autonomously decomposes, plans, executes, and delivers completed project

**Example**:
```bash
$ ui-cli build-project "Create a REST API with user authentication"

# System should:
1. Decompose into HTN graph (Project → Tasks → Todos)
2. Generate DSL workflows for orchestration
3. Route tasks to appropriate agent teams
4. Use adaptive learning for optimal model selection
5. Employ thinking model for complex design decisions
6. Execute with parallel optimization where possible
7. Handle failures with replanning
8. Track progress and artifacts
9. Report completion with deliverables
```

## Deliverables Required

Please provide a comprehensive blueprint with these sections:

### 1. **System Overview** (2-3 paragraphs)
- High-level vision of the integrated system
- How components work together
- Key benefits and capabilities

### 2. **Architecture Diagram** (ASCII art + description)
- Clean Architecture layers
- Component interactions
- Data flow between modules

### 3. **Core Components** (detailed specifications)

#### 3.1 ProjectOrchestrator
- Coordinates Plan → Verify → Decompose → Execute lifecycle
- Manages state across decomposition levels
- Handles feedback loops for replanning

#### 3.2 HTN-DSL Translator
- Converts HTN graphs to DSL workflows
- Maps task dependencies to composition/product operators
- Optimizes for parallel execution

#### 3.3 Goal Decomposer
- Accepts natural language project goals
- Generates HTN graph structure
- Uses thinking model for complex decomposition

#### 3.4 Execution Coordinator
- Routes tasks to agent teams
- Uses adaptive learning for model selection
- Manages parallel execution via DSL
- Collects performance data for learning

#### 3.5 State Manager
- Tracks project state (pending/executing/complete)
- Manages preconditions and effects
- Supports resumption and rollback

#### 3.6 Feedback Loop Handler
- Detects failures during execution
- Triggers replanning when needed
- Updates HTN graph dynamically

### 4. **Interfaces and Protocols** (Python-like pseudocode)
- ProjectBuilder interface
- OrchestrationLifecycle protocol
- StateManager protocol
- Any other critical interfaces

### 5. **Data Flow Example** (end-to-end)
Walk through a complete project from goal to completion:
1. User input
2. HTN decomposition
3. DSL generation
4. Agent routing
5. Model selection
6. Execution
7. Result delivery

### 6. **Integration Strategy**
How to integrate with existing codebase:
- What files/modules to create
- What existing components to extend
- Migration path from current state

### 7. **Workflow Examples**
At least 2 realistic project scenarios showing:
- HTN graph structure
- Generated DSL workflows
- Agent assignments
- Model selections
- Execution flow

### 8. **Performance Estimates**
- Expected project completion times
- Parallel execution speedups
- Model usage distribution
- Cost projections

### 9. **Extension Points**
Areas you identify for future enhancement:
- What could be improved
- Where the architecture could evolve
- Optional advanced features

### 10. **Implementation Roadmap**
Phased development plan:
- Phase 1: Minimal viable integration
- Phase 2: Core orchestration
- Phase 3: Advanced features
- Phase 4: Production hardening

## Design Principles to Follow

### MUST
- ✅ Clean Architecture (strict layer separation)
- ✅ SOLID principles (SRP, OCP, LSP, ISP, DIP)
- ✅ Dependency Inversion (depend on abstractions)
- ✅ Immutable entities where possible
- ✅ Async/await for non-blocking operations
- ✅ Protocol-based interfaces (not concrete classes)
- ✅ Visitor pattern for AST traversal
- ✅ Repository pattern for data persistence
- ✅ Factory pattern for component creation

### AVOID
- ❌ Tight coupling between modules
- ❌ God classes or objects
- ❌ Hardcoded workflows
- ❌ Static configurations
- ❌ Synchronous blocking operations
- ❌ Direct dependencies on infrastructure

## Output Format

Structure your response as:
```
<think>
[Your reasoning process - analyze gaps, consider trade-offs, design decisions]
</think>

# Agentic Project Builder - Architectural Blueprint

[Your complete blueprint following the structure above]
```

## Quality Criteria

Your blueprint should be:
- **Production-ready**: Immediately implementable
- **Comprehensive**: Covers all integration points
- **Detailed**: Sufficient for developers to implement
- **Extensible**: Clear extension points for future work
- **Validated**: Reasoning process shows trade-off analysis

## Additional Guidance

Based on our proven patterns:
- Use visitor pattern (proven in DSL interpreter)
- Use repository pattern (proven in adaptive learning)
- Use factory pattern (proven in agent/provider creation)
- Use strategy pattern (proven in model selection)
- Use team-based routing (proven in agent coordination)

Consider these specific challenges:
1. How to translate arbitrary natural language goals to HTN graphs?
2. How to determine optimal DSL workflow from HTN structure?
3. How to handle circular dependencies in task graphs?
4. How to balance thinking model usage (expensive) vs fast models?
5. How to persist and resume interrupted projects?

## Context Size Note

The full context document (PROJECT_BUILDER_CONTEXT.md) is ~4,500 words. Please read it thoroughly before designing, as it contains critical implementation details, proven patterns, and existing interfaces you must work with.

## Begin

Please provide your comprehensive architectural blueprint now. Take your time to think through the design carefully, showing your reasoning in the <think> section before presenting the final blueprint.
