"""Priority Queue - Autonomous Priority Worker System

Clean Architecture implementation for parallel autonomous execution.

Layers:
- Entities: Core data models (Task, Metrics)
- Use Cases: Business logic (ClaimTask, ExecuteWorkflow, etc.)
- Adapters: External integrations (Redis, Git, CLI, Logger)
- Orchestrator: PriorityWorker daemon (scripts/priority_worker.py)

Generated via ULTRATHINK code generation.
"""

__version__ = "0.1.0"
