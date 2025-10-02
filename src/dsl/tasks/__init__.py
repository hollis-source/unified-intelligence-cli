"""DSL Task Implementations - Real business logic for workflows.

This module contains actual task implementations that the DSL executor
can invoke. Tasks are organized by domain (gpu_integration, data_pipeline, etc.).

Clean Architecture: Use Cases layer.
"""

from . import gpu_integration_tasks
from . import git_operations_tasks

__all__ = ['gpu_integration_tasks', 'git_operations_tasks']
