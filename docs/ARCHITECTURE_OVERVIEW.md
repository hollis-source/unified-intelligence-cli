# Architecture Overview

This document summarizes the unified-intelligence-cli architecture following Clean Architecture and SOLID principles. The system centers business logic in Entities and Use Cases, with Adapters and Interfaces isolating external concerns. Dependency Inversion ensures core logic depends on abstractions, enabling model/provider swaps and multi-agent orchestration.

## Layers and Responsibilities

- Entities (src/entities): Immutable domain objects and core rules; no framework or IO.
- Use Cases (src/use_cases): Application-specific orchestration of entities; pure functions/services coordinating tasks.
- Interfaces (src/interfaces): Protocols/ABCs defining contracts for providers, agents, storage, and orchestration.
- Adapters (src/adapters): Implement Interfaces for concrete systems (LLMs, storage, SSH/MCP, HTTP, etc.).
- Routing (src/routing): Task routing and capability selection; supports team-based routing and composition.
- DSL (src/dsl): Category-theory-inspired DSL for composing tasks (sequence ∘, parallel ×, choice +) and workflows.
- Core Composition (src/composition.py): Wiring between use cases, routing, and adapters via dependency injection.
- Observability (src/observability): Metrics/logging/tracing adapters; non-intrusive to business logic.

## Dependency Inversion and Boundaries

- Use Cases depend on Interfaces (src/interfaces), not concrete Adapters.
- Factories (src/factories) and Provider registry (src/tool_registry.py) inject implementations at the edge.
- Adapters import outward only; Entities/Use Cases never import Adapters.

## Execution Model and Routing

- Router selects an execution plan (single agent, multi-agent, or team) based on task description and capabilities.
- Planning/coordination lives in use cases; adapters execute side effects (model inference, network, file IO).
- Priority Queue (src/priority_queue) supports scheduling and backpressure for background work.

## DSL Composition

- Workflows defined using the DSL enable explicit composition:
  - Sequence (A ∘ B): enforce ordering with data handoff.
  - Parallel (A × B): independent branches merged by a coordinator.
  - Choice (A + B): select based on predicates/metrics.
- Interpreters bind DSL nodes to use cases and router decisions.

## Modularity and Extensibility (SOLID)

- SRP: Each module has one reason to change (e.g., adapters isolate provider changes).
- OCP: Add new providers/agents by implementing interfaces; no core modifications required.
- LSP: All adapters satisfy interface contracts and can be swapped transparently.
- ISP: Fine-grained interfaces prevent bloated dependencies.
- DIP: Core depends only on abstractions; wiring happens in composition/factories.

## Repo Map (Key Paths)

- src/entities
- src/use_cases
- src/adapters
- src/interfaces
- src/routing
- src/dsl
- src/observability
- src/factories
- src/main.py (CLI entry), ui-cli/ and bin/ui-cli (installed wrapper)
- tests/ (unit, integration, property tests)

## Testing Strategy

- Unit tests cover use cases and routers via interface mocks.
- Integration tests exercise adapters with sandboxed endpoints and fixtures.
- Property-based and performance tests validate orchestration invariants.

## Operational Concerns

- Config (src/config.py, config/*.yaml) for environment-specific wiring.
- Metrics (metrics/, observability) and health checks (test_health_endpoint.py).
- Docker and Compose files for deployment; docs/PRODUCTION_DEPLOYMENT.md for runbooks.

