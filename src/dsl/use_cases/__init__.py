"""
DSL Use Cases Module

Application-specific business logic that orchestrates entities and adapters
to fulfill user requirements. Independent of frameworks and external interfaces.

Key Use Cases:
- WorkflowValidator: Pre-execution type checking for .ct workflow files
- TypedInterpreter: Runtime type validation during workflow execution
- TypedData: Type-tagged data wrapper for runtime validation

Clean Architecture: Use Case layer (orchestrates domain logic)
Story: Sprint 2, Phases 2-3 - Workflow Validation & Runtime Integration
"""

from src.dsl.use_cases.workflow_validator import (
    WorkflowValidator,
    ValidationReport,
)
from src.dsl.use_cases.typed_interpreter import (
    TypedInterpreter,
    RuntimeTypeError,
)
from src.dsl.use_cases.typed_data import (
    TypedData,
    wrap_if_needed,
    unwrap_if_needed,
)

__all__ = [
    "WorkflowValidator",
    "ValidationReport",
    "TypedInterpreter",
    "RuntimeTypeError",
    "TypedData",
    "wrap_if_needed",
    "unwrap_if_needed",
]
