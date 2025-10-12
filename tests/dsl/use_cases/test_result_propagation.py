import pytest
import asyncio
from src.dsl.use_cases.interpreter import Interpreter
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition
from src.dsl.entities.product import Product
from src.dsl.adapters.parser import Parser


class MockTaskExecutorWithPropagation:
    """Mock executor that tracks input data propagation."""

    def __init__(self):
        """Initialize with execution log."""
        self.execution_log = []

    async def execute_task(self, task_name: str, input_data=None):
        """Mock task execution with input tracking."""
        log_entry = {"task": task_name, "input": input_data}
        self.execution_log.append(log_entry)

        # Return result that includes task name and input
        return {"task": task_name, "input_received": input_data, "output": f"result_of_{task_name}"}


class TestResultPropagation:
    """Tests for result propagation through compositions.

    Following TDD: tests verify that results flow through the DSL pipeline.
    """

    def setup_method(self):
        """Setup interpreter with propagation-aware executor."""
        self.executor = MockTaskExecutorWithPropagation()
        self.interpreter = Interpreter(self.executor)

    @pytest.mark.asyncio
    async def test_composition_propagates_result_right_to_left(self):
        """Test composition passes right's result to left as input."""
        # test ∘ build
        # Should: execute build (no input) → execute test (with build's result as input)
        ast = Composition(
            left=Literal("test"),
            right=Literal("build")
        )
        result = await self.interpreter.execute(ast)

        # Verify execution order
        assert len(self.executor.execution_log) == 2
        assert self.executor.execution_log[0]["task"] == "build"
        assert self.executor.execution_log[0]["input"] is None  # build has no input

        # Critical: test should receive build's output as input
        assert self.executor.execution_log[1]["task"] == "test"
        assert self.executor.execution_log[1]["input"] is not None
        assert self.executor.execution_log[1]["input"]["output"] == "result_of_build"

    @pytest.mark.asyncio
    async def test_nested_composition_propagates_through_chain(self):
        """Test nested composition propagates results through entire chain."""
        # deploy ∘ test ∘ build
        # Parses as: deploy ∘ (test ∘ build)
        # Should: build → test(build_result) → deploy(test_result)
        ast = Composition(
            left=Literal("deploy"),
            right=Composition(
                left=Literal("test"),
                right=Literal("build")
            )
        )
        result = await self.interpreter.execute(ast)

        # Verify execution order and propagation
        assert len(self.executor.execution_log) == 3

        # build executes first (no input)
        assert self.executor.execution_log[0]["task"] == "build"
        assert self.executor.execution_log[0]["input"] is None

        # test receives build's result
        assert self.executor.execution_log[1]["task"] == "test"
        assert self.executor.execution_log[1]["input"]["output"] == "result_of_build"

        # deploy receives test's result
        assert self.executor.execution_log[2]["task"] == "deploy"
        assert self.executor.execution_log[2]["input"]["output"] == "result_of_test"

    @pytest.mark.asyncio
    async def test_product_propagates_to_subsequent_composition(self):
        """Test product results propagate to next composition stage."""
        # integrate ∘ (frontend × backend)
        # Should: (frontend ∥ backend) → integrate(tuple_of_results)
        ast = Composition(
            left=Literal("integrate"),
            right=Product(
                left=Literal("frontend"),
                right=Literal("backend")
            )
        )
        result = await self.interpreter.execute(ast)

        # Verify parallel execution then integration
        assert len(self.executor.execution_log) == 3

        # frontend and backend execute in parallel (no specific order guaranteed)
        tasks_executed = {log["task"] for log in self.executor.execution_log[:2]}
        assert tasks_executed == {"frontend", "backend"}

        # integrate receives tuple of (frontend_result, backend_result)
        integrate_log = self.executor.execution_log[2]
        assert integrate_log["task"] == "integrate"
        assert integrate_log["input"] is not None
        # Input should be tuple of both results
        assert isinstance(integrate_log["input"], tuple)
        assert len(integrate_log["input"]) == 2

    @pytest.mark.asyncio
    async def test_execute_with_initial_input(self):
        """Test executing AST with initial input data."""
        ast = Literal("process")
        initial_data = {"user_request": "build app"}

        result = await self.interpreter.execute(ast, input_data=initial_data)

        # Verify initial input was passed to first task
        assert len(self.executor.execution_log) == 1
        assert self.executor.execution_log[0]["task"] == "process"
        assert self.executor.execution_log[0]["input"] == initial_data

    @pytest.mark.asyncio
    async def test_parse_and_execute_with_propagation(self):
        """Test end-to-end: parse DSL and verify result propagation."""
        parser = Parser()
        dsl_program = "deploy ∘ test ∘ build"

        ast = parser.parse(dsl_program)
        result = await self.interpreter.execute(ast)

        # Verify complete propagation chain
        assert len(self.executor.execution_log) == 3
        assert self.executor.execution_log[0]["task"] == "build"
        assert self.executor.execution_log[1]["input"]["output"] == "result_of_build"
        assert self.executor.execution_log[2]["input"]["output"] == "result_of_test"

    @pytest.mark.asyncio
    async def test_complex_pipeline_propagation(self):
        """Test complex pipeline: (test_ui × test_api) ∘ (build_ui × build_api)."""
        parser = Parser()
        dsl_program = "(test_ui × test_api) ∘ (build_ui × build_api)"

        ast = parser.parse(dsl_program)
        result = await self.interpreter.execute(ast)

        # Should execute: build_ui ∥ build_api → test_ui ∥ test_api
        # test tasks should receive tuple of build results
        assert len(self.executor.execution_log) == 4

        # First two are builds (parallel, order not guaranteed)
        build_tasks = {log["task"] for log in self.executor.execution_log[:2]}
        assert build_tasks == {"build_ui", "build_api"}

        # Last two are tests (parallel)
        test_tasks = {log["task"] for log in self.executor.execution_log[2:]}
        assert test_tasks == {"test_ui", "test_api"}

        # Test tasks should receive build results as input
        # Product morphism f × g unpacks tuple input (a, b) to f(a) and g(b)
        # So test_ui receives build_ui result, test_api receives build_api result (not tuples)
        for log in self.executor.execution_log[2:]:
            assert log["input"] is not None
            # Each test task receives its corresponding build result (a dict)
            assert isinstance(log["input"], dict)
            assert "output" in log["input"]
            assert log["input"]["output"].startswith("result_of_build")
