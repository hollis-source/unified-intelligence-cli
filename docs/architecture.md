# Clean Architecture for Unified Intelligence CLI

## Dependency Rule
Source code dependencies point inward: Use cases ’ Entities. Adapters depend on interfaces, not vice versa. Protects core (agent orchestration) from externalities (LLMs, CLI).

## Layers
- **Entities**: Timeless models (e.g., `Agent`, `Task`invariants only).
- **Use Cases**: Orchestrate entities (e.g., `CoordinateAgentsUseCase`distributes tasks to specialized agents per AI Agents patterns).
- **Interfaces**: Abstractions (e.g., `IAgentExecutor`ISP: narrow for roles like query vs. execution).
- **Adapters**: Externals (e.g., `LLMAdapter` implementing `ILLMProvider`DIP: injectable).

## SOLID Enforcement
- SRP: One change reason per module.
- OCP: Extend agents via new use cases.
- LSP: Specialized agents substitute base without breaking coordination.
- ISP: Role-specific interfaces.
- DIP: Inject via constructors (e.g., `coordinator = Coordinator(llm_provider=OpenAIAdapter())`).

Diagram: Inner circle (Entities) ’ Use Cases ’ Interfaces ’ Adapters (CLI/LLM).