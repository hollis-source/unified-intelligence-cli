"""
DSL Use Cases Module

Application-specific business logic that orchestrates entities and adapters
to fulfill user requirements. Independent of frameworks and external interfaces.

Key Use Cases:
- WorkflowValidator: Pre-execution type checking for .ct workflow files

Clean Architecture: Use Case layer (orchestrates domain logic)
Story: Sprint 2, Phase 2 - Workflow Validation
"""

from src.dsl.use_cases.workflow_validator import (
    WorkflowValidator,
    ValidationReport,
)

__all__ = [
    "WorkflowValidator",
    "ValidationReport",
]
