"""Interfaces (Ports) for Claude Orchestrator.

Abstract interfaces defining contracts for external systems.
Implementations (Adapters) are swappable.

Clean Architecture: Interface/Port layer
SOLID: DIP - depend on abstractions, not concretions
"""

from src.claude_orchestrator.interfaces.worker_pool import (
    IWorkerPool,
    TaskOutput,
    TaskExecutionStatus,
    WorkerPoolError,
    WorkerPoolExhausted,
    WorkerExecutionError,
    WorkerNotFound,
    TaskTimeoutError,
    CancellationFailed,
)

from src.claude_orchestrator.interfaces.context_analyzer import (
    IGitAnalyzer,
    ITestAnalyzer,
    ICoverageAnalyzer,
    IGoalParser,
    GitInfo,
    TestResults,
    CoverageResults,
    ContextAnalysisError,
    GitAnalysisError,
    TestAnalysisError,
    CoverageAnalysisError,
    GoalParseError,
    GoalUpdateError,
)

__all__ = [
    # Worker Pool
    "IWorkerPool",
    "TaskOutput",
    "TaskExecutionStatus",
    "WorkerPoolError",
    "WorkerPoolExhausted",
    "WorkerExecutionError",
    "WorkerNotFound",
    "TaskTimeoutError",
    "CancellationFailed",
    # Context Analyzers
    "IGitAnalyzer",
    "ITestAnalyzer",
    "ICoverageAnalyzer",
    "IGoalParser",
    "GitInfo",
    "TestResults",
    "CoverageResults",
    "ContextAnalysisError",
    "GitAnalysisError",
    "TestAnalysisError",
    "CoverageAnalysisError",
    "GoalParseError",
    "GoalUpdateError",
]
