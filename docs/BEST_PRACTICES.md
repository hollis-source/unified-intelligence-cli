# Best Practices Guide

This repository follows Clean Architecture and SOLID principles to ensure maintainability, testability, and agility.

## Clean Architecture
- Entities (src/entities) contain core business rules; no IO or framework code
- Use Cases (src/use_cases) orchestrate entities; pure coordination logic
- Interfaces (src/interfaces) define contracts (providers, agents, storage)
- Adapters (src/adapters) implement Interfaces for concrete systems (LLMs, HTTP, DB, SSH/MCP)
- Dependency Inversion: core depends on abstractions; wiring via factories/composition

## SOLID
- SRP: One reason to change per module/class
- OCP: Extend via new adapters/providers; avoid modifying core
- LSP: Adapters satisfy interface contracts and can be swapped
- ISP: Prefer small, focused interfaces
- DIP: Depend on Interfaces, inject Adapters at boundaries

## TDD and Testing
- Write failing tests first; implement minimal code; refactor
- Unit tests for use cases and routers with interface mocks
- Integration tests for adapters with sandbox fixtures
- Keep tests deterministic and fast; isolate side-effects behind interfaces

## Code Quality
- Functions < 20 lines; prefer small, focused functions
- DRY: Abstract duplication; share utilities where appropriate
- Explicit error handling: raise domain-specific exceptions; no silent failures
- Type hints and docstrings required for public APIs
- Linting and formatting: black, flake8; mypy for types

## Documentation
- Keep docs in docs/ with architecture mapping to src/ structure
- Reference key paths: src/entities, src/use_cases, src/adapters, src/interfaces
- Update docs alongside code changes (same PR)

## Operational Notes
- Configuration via src/config.py and config/*.yaml
- Observability via src/observability; metrics and tracing adapters
- Avoid hardcoding secrets; use environment variables and .env (gitignored)

