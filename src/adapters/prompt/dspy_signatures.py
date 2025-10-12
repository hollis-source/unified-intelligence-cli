"""
DSPy Signatures for Project Builder Tasks.

Each signature defines the input/output contract for a specific task type,
allowing DSPy to auto-generate and optimize prompts.

Sprint 1, US-1.1: DSPy signatures for task-specific prompt optimization.

Clean Architecture:
- Signatures define contracts (like interfaces in OOP)
- DSPy uses these to generate optimized prompts
- Decouples prompt engineering from business logic
"""

import dspy
from typing import Annotated


class ImplementationSignature(dspy.Signature):
    """
    Generate complete, working code for implementation tasks.

    This signature is used for tasks that require generating actual code:
    - Function implementations
    - API endpoint definitions
    - Data model definitions
    - Configuration file generation

    The signature guides DSPy to generate code without explanations or TODOs.
    """

    task_description: str = dspy.InputField(
        desc="Detailed description of what code to generate"
    )

    previous_outputs: str = dspy.InputField(
        desc="Context from previous tasks (API schemas, database models, etc.)"
    )

    code: str = dspy.OutputField(
        desc=(
            "Complete, working code with proper syntax and error handling. "
            "Must include all necessary imports and be fully functional. "
            "Do not include TODOs, placeholders, or 'similar to...' comments. "
            "Do not include explanatory text outside of code comments. "
            "Return only executable code."
        )
    )


class DesignSignature(dspy.Signature):
    """
    Generate design specifications and schemas for architecture/planning tasks.

    Used for:
    - API schema design
    - Database schema design
    - System architecture diagrams
    - Data flow specifications
    """

    task_description: str = dspy.InputField(
        desc="Description of what needs to be designed"
    )

    context: str = dspy.InputField(
        desc="Relevant context (requirements, constraints, existing designs)"
    )

    design_spec: str = dspy.OutputField(
        desc=(
            "Complete design specification (API schema, data model, architecture). "
            "Use proper notation (JSON schema, UML, SQL DDL, etc.). "
            "Be specific and implementable. "
            "Include all necessary details for implementation."
        )
    )


class TestingSignature(dspy.Signature):
    """
    Generate test code with comprehensive test cases.

    Used for:
    - Unit test generation
    - Integration test generation
    - Test fixture creation
    - Test data generation
    """

    task_description: str = dspy.InputField(
        desc="Description of what needs to be tested"
    )

    code_to_test: str = dspy.InputField(
        desc="Code that needs to be tested (functions, classes, APIs)"
    )

    test_code: str = dspy.OutputField(
        desc=(
            "Complete test code with assertions, edge cases, and error cases. "
            "Use appropriate testing framework (pytest, unittest, etc.). "
            "Include test fixtures and setup/teardown if needed. "
            "Cover normal cases, edge cases, and error conditions. "
            "Return only executable test code."
        )
    )


class DocumentationSignature(dspy.Signature):
    """
    Generate user-facing documentation.

    Used for:
    - README generation
    - API documentation
    - Usage guides
    - Code comments/docstrings
    """

    task_description: str = dspy.InputField(
        desc="Description of what needs to be documented"
    )

    code_or_api: str = dspy.InputField(
        desc="Code or API to document (functions, classes, endpoints)"
    )

    documentation: str = dspy.OutputField(
        desc=(
            "Complete documentation with examples, clear explanations, proper formatting. "
            "Use markdown for structure. "
            "Include: overview, parameters, return values, examples, edge cases. "
            "Be clear and concise. Target audience: developers using this code."
        )
    )
