"""Core business entities - Pure domain models with no external dependencies.

DEPRECATED: This module location (src.entities) is deprecated.
Use src.entity instead. This compatibility shim will be removed in a future version.
"""

import warnings
warnings.warn(
    "Module 'src.entities' is deprecated, use 'src.entity' instead",
    DeprecationWarning,
    stacklevel=2
)

from .agent import Agent, Task
from .execution import ExecutionResult, ExecutionContext, ExecutionStatus
from .agent_team import (
    AgentTeam,
    FrontendTeam,
    BackendTeam,
    TestingTeam,
    InfrastructureTeam,
    ResearchTeam,
    OrchestrationTeam,
    QualityAssuranceTeam,
    CategoryTheoryTeam,
    DSLTeam
)
from .metrics import (
    MetricsCollector,
    RoutingMetric,
    ModelSelectionMetric,
    TeamUtilizationMetric
)

__all__ = [
    "Agent",
    "Task",
    "ExecutionResult",
    "ExecutionContext",
    "ExecutionStatus",
    "AgentTeam",
    "FrontendTeam",
    "BackendTeam",
    "TestingTeam",
    "InfrastructureTeam",
    "ResearchTeam",
    "OrchestrationTeam",
    "QualityAssuranceTeam",
    "CategoryTheoryTeam",
    "DSLTeam",
    "MetricsCollector",
    "RoutingMetric",
    "ModelSelectionMetric",
    "TeamUtilizationMetric"
]