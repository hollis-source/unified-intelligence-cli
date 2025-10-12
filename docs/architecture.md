# Clean Architecture for Unified Intelligence CLI

## Dependency Rule
Source code dependencies point inward: Use cases → Entities. Adapters depend on interfaces, not vice versa. Protects core (agent orchestration) from externalities (LLMs, CLI).

## Layers
- **Entities**: Timeless models (e.g., `Agent`, `Task`) - invariants only.
- **Use Cases**: Orchestrate entities (e.g., `TaskCoordinatorUseCase`, `TaskPlannerUseCase`) - distributes tasks to specialized agents per AI Agents patterns.
- **Interfaces**: Abstractions (e.g., `IAgentExecutor`, `ITaskPlanner`) - ISP: narrow for roles like query vs. execution.
- **Adapters**: Externals (e.g., `GrokAdapter` implementing `ITextGenerator`) - DIP: injectable.

## SOLID Enforcement
- **SRP**: One change reason per module (e.g., TaskPlanner plans, TaskCoordinator executes).
- **OCP**: Extend agents via new use cases without modifying existing code.
- **LSP**: Specialized agents substitute base without breaking coordination.
- **ISP**: Role-specific interfaces (e.g., ITaskPlanner vs IAgentCoordinator).
- **DIP**: Inject via constructors (e.g., `coordinator = TaskCoordinatorUseCase(task_planner=planner)`).

## Architecture Diagram
```
Inner circle (Entities) → Use Cases → Interfaces → Adapters (CLI/LLM/Agent)
```

## Current Implementation
- **Entities**: `Agent`, `Task`, `ExecutionPlan`, `ExecutionResult`
- **Use Cases**: `TaskPlannerUseCase`, `TaskCoordinatorUseCase`
- **Interfaces**: `ITextGenerator`, `IAgentExecutor`, `ITaskPlanner`, `IAgentCoordinator`
- **Adapters**: `GrokAdapter`, `MockLLMProvider`, `LLMAgentExecutor`, `CapabilitySelector`
- **Factories**: `ProviderFactory`, `AgentFactory` (DIP: create instances via interfaces)
- **Composition Root**: `src/composition.py` - wires dependencies