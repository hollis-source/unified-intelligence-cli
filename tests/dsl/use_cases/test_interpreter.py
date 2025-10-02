import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from src.dsl.use_cases.interpreter import Interpreter
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition
from src.dsl.entities.product import Product
from src.dsl.entities.functor import Functor
from src.dsl.adapters.parser import Parser


class MockTaskExecutor:
    """Mock task executor for testing."""

    def __init__(self):
        """Initialize with execution log."""
        self.execution_log = []

    async def execute_task(self, task_name: str, input_data=None):
        """Mock task execution."""
        self.execution_log.append(f"execute: {task_name}")
        return f"result_{task_name}"


class TestInterpreter:
    """Tests for DSL Interpreter use case.

    Following TDD: tests written first, implementation follows.
    """

    def setup_method(self):
        """Setup interpreter and mock executor for each test."""
        self.executor = MockTaskExecutor()
        self.interpreter = Interpreter(self.executor)

    @pytest.mark.asyncio
    async def test_execute_literal(self):
        """Test executing a single literal task."""
        ast = Literal("build")
        result = await self.interpreter.execute(ast)

        assert result == "result_build"
        assert self.executor.execution_log == ["execute: build"]

    @pytest.mark.asyncio
    async def test_execute_composition_sequential(self):
        """Test composition executes right-to-left (CT semantics)."""
        # test ∘ build -> execute build first, then test
        ast = Composition(
            left=Literal("test"),
            right=Literal("build")
        )
        result = await self.interpreter.execute(ast)

        # Should execute right first (build), then left (test)
        assert self.executor.execution_log == ["execute: build", "execute: test"]

    @pytest.mark.asyncio
    async def test_execute_product_parallel(self):
        """Test product executes tasks in parallel."""
        # frontend × backend
        ast = Product(
            left=Literal("frontend"),
            right=Literal("backend")
        )
        result = await self.interpreter.execute(ast)

        # Both should be executed (order not guaranteed for parallel)
        assert "execute: frontend" in self.executor.execution_log
        assert "execute: backend" in self.executor.execution_log
        assert len(self.executor.execution_log) == 2

    @pytest.mark.asyncio
    async def test_execute_nested_composition(self):
        """Test nested composition (deploy ∘ test ∘ build)."""
        # Parses as: deploy ∘ (test ∘ build)
        ast = Composition(
            left=Literal("deploy"),
            right=Composition(
                left=Literal("test"),
                right=Literal("build")
            )
        )
        result = await self.interpreter.execute(ast)

        # Right-to-left: build, test, deploy
        assert self.executor.execution_log == [
            "execute: build",
            "execute: test",
            "execute: deploy"
        ]

    @pytest.mark.asyncio
    async def test_execute_complex_parallel_sequential(self):
        """Test complex expression: (frontend × backend) ∘ plan."""
        ast = Composition(
            left=Product(
                left=Literal("frontend"),
                right=Literal("backend")
            ),
            right=Literal("plan")
        )
        result = await self.interpreter.execute(ast)

        # Should execute plan first, then frontend and backend in parallel
        assert self.executor.execution_log[0] == "execute: plan"
        assert "execute: frontend" in self.executor.execution_log[1:]
        assert "execute: backend" in self.executor.execution_log[1:]

    @pytest.mark.asyncio
    async def test_execute_functor(self):
        """Test functor execution."""
        ast = Functor(
            name="ci_pipeline",
            expression=Composition(
                left=Literal("test"),
                right=Literal("build")
            )
        )
        result = await self.interpreter.execute(ast)

        # Should execute the functor's expression
        assert self.executor.execution_log == ["execute: build", "execute: test"]

    @pytest.mark.asyncio
    async def test_parse_and_execute(self):
        """Test end-to-end: parse DSL and execute."""
        parser = Parser()
        dsl_program = "test ∘ build"

        ast = parser.parse(dsl_program)
        result = await self.interpreter.execute(ast)

        assert self.executor.execution_log == ["execute: build", "execute: test"]

    @pytest.mark.asyncio
    async def test_parse_and_execute_parallel(self):
        """Test end-to-end with parallel execution."""
        parser = Parser()
        dsl_program = "frontend × backend"

        ast = parser.parse(dsl_program)
        result = await self.interpreter.execute(ast)

        assert "execute: frontend" in self.executor.execution_log
        assert "execute: backend" in self.executor.execution_log
