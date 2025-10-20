"""Graph entities for task dependency modeling.

This module provides graph-theoretic structures for representing task
dependencies, hierarchies, and execution flows in the unified architecture.
"""

from .graph import Graph, GraphNode

__all__ = ["Graph", "GraphNode"]
