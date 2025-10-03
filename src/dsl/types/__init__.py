"""
DSL Type System Module

Implements Hindley-Milner type inference with category-theoretic foundations
for type-safe distributed workflow composition.

Key Components:
- type_system.py: Core type classes and unification algorithm
- type_checker.py: Type inference engine for DSL workflows
- type_env.py: Type environment for scope management
- category_laws.py: Category theory law verification

Story: Story 1 - Type-Safe Distributed Workflow Composition
Sprint: Sprint 1, Phase 1 (Week 1-2)
"""

from src.dsl.types.type_system import (
    Type,
    TypeVariable,
    MonomorphicType,
    FunctionType,
    ProductType,
    Substitution,
    TypeMismatchError,
)

__all__ = [
    "Type",
    "TypeVariable",
    "MonomorphicType",
    "FunctionType",
    "ProductType",
    "Substitution",
    "TypeMismatchError",
]
