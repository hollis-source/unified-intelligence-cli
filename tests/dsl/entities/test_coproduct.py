"""
Unit tests for Coproduct entity - Phase 2c.

Tests categorical coproduct (sum type) semantics:
- Entity creation and validation
- String representation
- Visitor pattern
- First-success execution with lazy evaluation
- Error handling and fallback behavior

Clean Architecture: Test layer validating entity contracts.
"""

import pytest
from src.dsl.entities.coproduct import Coproduct
from src.dsl.entities.literal import Literal
from src.dsl.entities.composition import Composition


class TestCoproductEntity:
    """Test Coproduct entity structure and validation."""

    def test_coproduct_creation(self):
        """Test creating a valid Coproduct entity."""
        left = Literal("grok_model")
        right = Literal("qwen_model")
        coproduct = Coproduct(left=left, right=right)

        assert coproduct.left == left
        assert coproduct.right == right

    def test_coproduct_immutability(self):
        """Test that Coproduct entities are immutable (frozen=True)."""
        left = Literal("task_a")
        right = Literal("task_b")
        coproduct = Coproduct(left=left, right=right)

        # Attempt to modify should raise FrozenInstanceError
        with pytest.raises(Exception):  # dataclass.FrozenInstanceError
            coproduct.left = Literal("modified")

    def test_coproduct_left_validation(self):
        """Test that left must be an ASTNode instance."""
        right = Literal("valid_task")

        with pytest.raises(TypeError) as exc_info:
            Coproduct(left="not_an_ast_node", right=right)

        assert "left must be an instance of ASTNode" in str(exc_info.value)

    def test_coproduct_right_validation(self):
        """Test that right must be an ASTNode instance."""
        left = Literal("valid_task")

        with pytest.raises(TypeError) as exc_info:
            Coproduct(left=left, right=42)

        assert "right must be an instance of ASTNode" in str(exc_info.value)

    def test_coproduct_repr(self):
        """Test string representation of Coproduct."""
        left = Literal("primary")
        right = Literal("fallback")
        coproduct = Coproduct(left=left, right=right)

        expected = "(Literal(value='primary') + Literal(value='fallback'))"
        assert repr(coproduct) == expected

    def test_coproduct_nested_repr(self):
        """Test string representation with nested coproducts."""
        # (task1 + task2) + task3
        inner = Coproduct(left=Literal("task1"), right=Literal("task2"))
        outer = Coproduct(left=inner, right=Literal("task3"))

        expected = "((Literal(value='task1') + Literal(value='task2')) + Literal(value='task3'))"
        assert repr(outer) == expected

    def test_coproduct_mixed_composition_repr(self):
        """Test string representation with mixed operators."""
        # (build ∘ test) + (lint ∘ format)
        left = Composition(left=Literal("build"), right=Literal("test"))
        right = Composition(left=Literal("lint"), right=Literal("format"))
        coproduct = Coproduct(left=left, right=right)

        expected = "((Literal(value='build') ∘ Literal(value='test')) + (Literal(value='lint') ∘ Literal(value='format')))"
        assert repr(coproduct) == expected

    def test_coproduct_visitor_pattern(self):
        """Test that Coproduct implements visitor pattern correctly."""
        left = Literal("task_x")
        right = Literal("task_y")
        coproduct = Coproduct(left=left, right=right)

        # Mock visitor
        class MockVisitor:
            def visit_coproduct(self, node):
                return f"visited_{node.left}_{node.right}"

        visitor = MockVisitor()
        result = coproduct.accept(visitor)

        assert result == "visited_Literal(value='task_x')_Literal(value='task_y')"


class TestCoproductParser:
    """Test parser transformation of coproduct expressions."""

    def test_parse_simple_coproduct(self):
        """Test parsing simple coproduct expression: task1 + task2."""
        from src.dsl.adapters.parser import Parser

        parser = Parser()
        ast = parser.parse("task1 + task2")

        assert isinstance(ast, Coproduct)
        assert isinstance(ast.left, Literal)
        assert isinstance(ast.right, Literal)
        assert ast.left.value == "task1"
        assert ast.right.value == "task2"

    def test_parse_coproduct_with_unicode(self):
        """Test parsing coproduct with categorical symbol ⊕."""
        from src.dsl.adapters.parser import Parser

        parser = Parser()
        ast = parser.parse("primary ⊕ secondary")

        assert isinstance(ast, Coproduct)
        assert ast.left.value == "primary"
        assert ast.right.value == "secondary"

    def test_parse_chained_coproduct(self):
        """Test parsing chained coproduct: task1 + task2 + task3."""
        from src.dsl.adapters.parser import Parser

        parser = Parser()
        ast = parser.parse("task1 + task2 + task3")

        # Should parse as left-associative: (task1 + task2) + task3
        assert isinstance(ast, Coproduct)
        assert isinstance(ast.left, Coproduct)  # Inner coproduct
        assert isinstance(ast.right, Literal)   # task3

        # Verify inner coproduct
        inner = ast.left
        assert inner.left.value == "task1"
        assert inner.right.value == "task2"
        assert ast.right.value == "task3"

    def test_parse_coproduct_with_composition(self):
        """Test parsing mixed coproduct and composition: (build ∘ test) + (lint ∘ format)."""
        from src.dsl.adapters.parser import Parser

        parser = Parser()
        ast = parser.parse("(build ∘ test) + (lint ∘ format)")

        assert isinstance(ast, Coproduct)
        assert isinstance(ast.left, Composition)
        assert isinstance(ast.right, Composition)

        # Verify left composition: build ∘ test
        assert ast.left.left.value == "build"
        assert ast.left.right.value == "test"

        # Verify right composition: lint ∘ format
        assert ast.right.left.value == "lint"
        assert ast.right.right.value == "format"


class TestCoproductInterpreter:
    """Test interpreter execution of coproduct with first-success semantics."""

    @pytest.mark.asyncio
    async def test_coproduct_left_success(self):
        """Test coproduct returns left result when left succeeds (short-circuit)."""
        from src.dsl.use_cases.interpreter import Interpreter

        # Mock executor that always succeeds
        class MockExecutor:
            async def execute_task(self, task_name, input_data=None):
                return f"success_{task_name}"

        interpreter = Interpreter(MockExecutor())
        coproduct = Coproduct(left=Literal("primary"), right=Literal("fallback"))

        result = await interpreter.execute(coproduct)

        # Should return left result (primary) and NOT execute right
        assert result == "success_primary"

    @pytest.mark.asyncio
    async def test_coproduct_left_fails_right_succeeds(self):
        """Test coproduct falls back to right when left fails."""
        from src.dsl.use_cases.interpreter import Interpreter

        # Mock executor that fails on primary, succeeds on fallback
        class MockExecutor:
            async def execute_task(self, task_name, input_data=None):
                if task_name == "primary":
                    raise RuntimeError("Primary service unavailable")
                return f"success_{task_name}"

        interpreter = Interpreter(MockExecutor())
        coproduct = Coproduct(left=Literal("primary"), right=Literal("fallback"))

        result = await interpreter.execute(coproduct)

        # Should return right result (fallback) after left failed
        assert result == "success_fallback"

    @pytest.mark.asyncio
    async def test_coproduct_both_fail(self):
        """Test coproduct raises combined error when both alternatives fail."""
        from src.dsl.use_cases.interpreter import Interpreter

        # Mock executor that always fails
        class MockExecutor:
            async def execute_task(self, task_name, input_data=None):
                raise RuntimeError(f"{task_name}_error")

        interpreter = Interpreter(MockExecutor())
        coproduct = Coproduct(left=Literal("task1"), right=Literal("task2"))

        with pytest.raises(Exception) as exc_info:
            await interpreter.execute(coproduct)

        # Should contain both error messages
        error_msg = str(exc_info.value)
        assert "both alternatives failed" in error_msg
        assert "task1_error" in error_msg
        assert "task2_error" in error_msg

    @pytest.mark.asyncio
    async def test_coproduct_lazy_evaluation(self):
        """Test coproduct does NOT execute right if left succeeds (lazy evaluation)."""
        from src.dsl.use_cases.interpreter import Interpreter

        execution_log = []

        # Mock executor that logs executions
        class MockExecutor:
            async def execute_task(self, task_name, input_data=None):
                execution_log.append(task_name)
                return f"success_{task_name}"

        interpreter = Interpreter(MockExecutor())
        coproduct = Coproduct(left=Literal("primary"), right=Literal("fallback"))

        result = await interpreter.execute(coproduct)

        # Verify only left was executed (short-circuit)
        assert execution_log == ["primary"]
        assert "fallback" not in execution_log
        assert result == "success_primary"

    @pytest.mark.asyncio
    async def test_coproduct_input_propagation(self):
        """Test coproduct propagates input data to both alternatives."""
        from src.dsl.use_cases.interpreter import Interpreter

        # Mock executor that returns input data
        class MockExecutor:
            async def execute_task(self, task_name, input_data=None):
                if task_name == "fail_task":
                    raise RuntimeError("Simulated failure")
                return f"{task_name}_received_{input_data}"

        interpreter = Interpreter(MockExecutor())
        coproduct = Coproduct(left=Literal("fail_task"), right=Literal("success_task"))

        input_data = "test_input"
        result = await interpreter.execute(coproduct, input_data=input_data)

        # Right task should receive input after left failed
        assert result == "success_task_received_test_input"

    @pytest.mark.asyncio
    async def test_coproduct_chained_fallback(self):
        """Test chained coproduct: (task1 + task2) + task3."""
        from src.dsl.use_cases.interpreter import Interpreter

        # Mock executor that fails on task1 and task2, succeeds on task3
        class MockExecutor:
            async def execute_task(self, task_name, input_data=None):
                if task_name in ["task1", "task2"]:
                    raise RuntimeError(f"{task_name}_failed")
                return f"success_{task_name}"

        interpreter = Interpreter(MockExecutor())

        # (task1 + task2) + task3
        inner = Coproduct(left=Literal("task1"), right=Literal("task2"))
        outer = Coproduct(left=inner, right=Literal("task3"))

        result = await interpreter.execute(outer)

        # Should fallback to task3 after both task1 and task2 fail
        assert result == "success_task3"

    @pytest.mark.asyncio
    async def test_coproduct_model_fallback_use_case(self):
        """Test realistic use case: grok_model + qwen_model + local_model."""
        from src.dsl.use_cases.interpreter import Interpreter
        from src.dsl.adapters.parser import Parser

        # Mock executor simulating model availability
        class MockModelExecutor:
            async def execute_task(self, task_name, input_data=None):
                if task_name == "grok_model":
                    raise RuntimeError("Grok API rate limit exceeded")
                elif task_name == "qwen_model":
                    raise RuntimeError("Qwen service unavailable")
                elif task_name == "local_model":
                    return f"local_model_result: {input_data}"
                else:
                    raise RuntimeError(f"Unknown model: {task_name}")

        parser = Parser()
        ast = parser.parse("grok_model + qwen_model + local_model")

        interpreter = Interpreter(MockModelExecutor())
        result = await interpreter.execute(ast, input_data="translate this text")

        # Should fallback to local_model after grok and qwen fail
        assert result == "local_model_result: translate this text"


class TestCoproductIntegration:
    """Integration tests for coproduct with real parser and interpreter."""

    @pytest.mark.asyncio
    async def test_parse_and_execute_coproduct(self):
        """Test end-to-end: parse DSL text and execute coproduct."""
        from src.dsl.adapters.parser import Parser
        from src.dsl.use_cases.interpreter import Interpreter

        # Mock executor
        class MockExecutor:
            async def execute_task(self, task_name, input_data=None):
                if task_name == "primary":
                    raise RuntimeError("Primary failed")
                return f"{task_name}_success"

        parser = Parser()
        ast = parser.parse("primary + backup")

        interpreter = Interpreter(MockExecutor())
        result = await interpreter.execute(ast)

        assert result == "backup_success"

    @pytest.mark.asyncio
    async def test_complex_workflow_with_coproduct(self):
        """Test complex workflow: (build ∘ test) + (lint ∘ format).

        Composition is right-to-left: build ∘ test means test first, then build.
        If left branch fails, coproduct falls back to right branch.
        """
        from src.dsl.adapters.parser import Parser
        from src.dsl.use_cases.interpreter import Interpreter

        execution_log = []

        # Mock executor that fails on test (causing left branch to fail)
        class MockExecutor:
            async def execute_task(self, task_name, input_data=None):
                execution_log.append(task_name)
                if task_name == "test":
                    # test executes first (right-to-left), fails
                    raise RuntimeError("Tests failed")
                return f"{task_name}_result"

        parser = Parser()
        ast = parser.parse("(build ∘ test) + (lint ∘ format)")

        interpreter = Interpreter(MockExecutor())
        result = await interpreter.execute(ast)

        # Left branch: test (fails) → no build execution
        # Right branch: format (succeeds) → lint (succeeds)
        assert "test" in execution_log  # Left branch tried test first
        assert "format" in execution_log  # Right branch executed format first
        assert "lint" in execution_log  # Then lint

        # build should NOT be in log because test failed before build could run
        # Final result from lint (last in right branch composition)
        assert result == "lint_result"
