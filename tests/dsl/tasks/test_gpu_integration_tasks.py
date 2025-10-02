"""Unit tests for GPU integration tasks.

TDD: Test-driven development for DSL task implementations.
Clean Architecture: Tests for Use Cases layer.
"""

import pytest
import asyncio
from src.dsl.tasks.gpu_integration_tasks import (
    # Phase 1: Planning & Research
    research_modal_api,
    research_together_api,
    design_architecture,
    write_technical_spec,
    # Phase 2: Test Writing
    write_adapter_tests,
    write_integration_tests,
    write_cli_tests,
    # Phase 3: Implementation
    implement_modal_adapter,
    implement_together_adapter,
    implement_cli_commands,
    # Phase 4: CI/CD
    run_ci_pipeline,
    integration_test,
    generate_docs,
    build_package,
    deploy_to_staging,
)


# =============================================================================
# Phase 1: Planning & Research Tasks Tests
# =============================================================================

@pytest.mark.asyncio
async def test_research_modal_api():
    """Test Modal API research task."""
    result = await research_modal_api()

    assert result["task"] == "research_modal_api"
    assert result["status"] == "success"
    assert result["provider"] == "Modal"
    assert "findings" in result
    assert "pricing" in result["findings"]
    assert "T4" in result["findings"]["pricing"]
    assert "next_steps" in result
    assert len(result["next_steps"]) > 0


@pytest.mark.asyncio
async def test_research_together_api():
    """Test Together.ai API research task."""
    result = await research_together_api()

    assert result["task"] == "research_together_api"
    assert result["status"] == "success"
    assert result["provider"] == "Together.ai"
    assert "findings" in result
    assert "H100" in result["findings"]["pricing"]


@pytest.mark.asyncio
async def test_design_architecture():
    """Test architecture design task."""
    result = await design_architecture()

    assert result["task"] == "design_architecture"
    assert result["status"] == "success"
    assert "architecture" in result
    assert "layers" in result["architecture"]
    assert "entities" in result["architecture"]["layers"]
    assert "adapters" in result["architecture"]["layers"]
    assert "design_principles" in result
    assert any("SOLID" in principle or "Dependency" in principle
               for principle in result["design_principles"])


@pytest.mark.asyncio
async def test_write_technical_spec():
    """Test technical spec writing task."""
    result = await write_technical_spec()

    assert result["task"] == "write_technical_spec"
    assert result["status"] == "success"
    assert "spec" in result
    assert "requirements" in result["spec"]
    assert "functional" in result["spec"]["requirements"]
    assert "test_scenarios" in result["spec"]


# =============================================================================
# Phase 2: Test Writing Tasks Tests (Meta-tests!)
# =============================================================================

@pytest.mark.asyncio
async def test_write_adapter_tests():
    """Test adapter test writing task."""
    result = await write_adapter_tests()

    assert result["task"] == "write_adapter_tests"
    assert result["status"] == "success"
    assert "tests_written" in result
    assert result["tests_written"]["test_count"] > 0
    assert "test_cases" in result["tests_written"]


@pytest.mark.asyncio
async def test_write_integration_tests():
    """Test integration test writing task."""
    result = await write_integration_tests()

    assert result["task"] == "write_integration_tests"
    assert result["status"] == "success"
    assert result["tests_written"]["test_count"] >= 3


@pytest.mark.asyncio
async def test_write_cli_tests():
    """Test CLI test writing task."""
    result = await write_cli_tests()

    assert result["task"] == "write_cli_tests"
    assert result["status"] == "success"
    assert result["tests_written"]["test_count"] >= 5


# =============================================================================
# Phase 3: Implementation Tasks Tests
# =============================================================================

@pytest.mark.asyncio
async def test_implement_modal_adapter():
    """Test Modal adapter implementation task."""
    result = await implement_modal_adapter()

    assert result["task"] == "implement_modal_adapter"
    assert result["status"] == "success"
    assert "implementation" in result
    assert "file" in result["implementation"]
    assert "modal_adapter" in result["implementation"]["file"]
    assert result["implementation"]["lines_of_code"] > 0


@pytest.mark.asyncio
async def test_implement_together_adapter():
    """Test Together.ai adapter implementation task."""
    result = await implement_together_adapter()

    assert result["task"] == "implement_together_adapter"
    assert result["status"] == "success"
    assert "together_adapter" in result["implementation"]["file"]


@pytest.mark.asyncio
async def test_implement_cli_commands():
    """Test CLI commands implementation task."""
    result = await implement_cli_commands()

    assert result["task"] == "implement_cli_commands"
    assert result["status"] == "success"
    assert len(result["implementation"]["commands_added"]) >= 4
    assert "deploy" in result["implementation"]["commands_added"]
    assert "infer" in result["implementation"]["commands_added"]


# =============================================================================
# Phase 4: CI/CD Tasks Tests
# =============================================================================

@pytest.mark.asyncio
async def test_run_ci_pipeline():
    """Test CI pipeline execution."""
    result = await run_ci_pipeline()

    assert result["task"] == "run_ci_pipeline"
    assert result["status"] == "success"
    assert "pipeline_results" in result
    assert "unit_tests" in result["pipeline_results"]
    assert result["pipeline_results"]["unit_tests"]["failed"] == 0
    assert "✅ PASS" in result["overall_status"]


@pytest.mark.asyncio
async def test_integration_test():
    """Test integration testing task."""
    result = await integration_test()

    assert result["task"] == "integration_test"
    assert result["status"] == "success"
    assert "test_results" in result
    assert all(status == "PASS" for status in result["test_results"].values())


@pytest.mark.asyncio
async def test_generate_docs():
    """Test documentation generation task."""
    result = await generate_docs()

    assert result["task"] == "generate_docs"
    assert result["status"] == "success"
    assert "docs_generated" in result
    assert len(result["docs_generated"]) >= 3


@pytest.mark.asyncio
async def test_build_package():
    """Test package building task."""
    result = await build_package()

    assert result["task"] == "build_package"
    assert result["status"] == "success"
    assert "build_artifacts" in result
    assert "wheel" in result["build_artifacts"]
    assert "version" in result


@pytest.mark.asyncio
async def test_deploy_to_staging():
    """Test staging deployment task."""
    result = await deploy_to_staging()

    assert result["task"] == "deploy_to_staging"
    assert result["status"] == "success"
    assert "deployment" in result
    assert result["deployment"]["environment"] == "staging"
    assert "✅" in result["deployment"]["health_check"]
    assert "next_steps" in result


# =============================================================================
# Integration Tests: Task Composition
# =============================================================================

@pytest.mark.asyncio
async def test_parallel_planning_tasks():
    """Test executing planning tasks in parallel."""
    # Execute all planning tasks concurrently
    results = await asyncio.gather(
        research_modal_api(),
        research_together_api(),
        design_architecture(),
        write_technical_spec(),
    )

    # Verify all succeeded
    assert len(results) == 4
    assert all(r["status"] == "success" for r in results)

    # Verify each task has unique output
    task_names = [r["task"] for r in results]
    assert len(set(task_names)) == 4


@pytest.mark.asyncio
async def test_sequential_ci_cd_pipeline():
    """Test sequential CI/CD execution."""
    # Run CI/CD stages in order
    ci_result = await run_ci_pipeline()
    test_result = await integration_test(ci_result)
    docs_result = await generate_docs(test_result)
    build_result = await build_package(docs_result)
    deploy_result = await deploy_to_staging(build_result)

    # Verify pipeline completed
    assert deploy_result["status"] == "success"
    assert deploy_result["deployment"]["environment"] == "staging"


@pytest.mark.asyncio
async def test_task_input_propagation():
    """Test that tasks can receive input from previous tasks."""
    # First task
    research_result = await research_modal_api()

    # Second task receives input from first
    spec_result = await write_technical_spec(research_result)

    # Verify input was available
    assert spec_result["status"] == "success"


# =============================================================================
# Performance Tests
# =============================================================================

@pytest.mark.asyncio
async def test_parallel_execution_faster_than_sequential():
    """Test that parallel execution is faster than sequential."""
    import time

    # Sequential execution
    start_seq = time.time()
    await research_modal_api()
    await research_together_api()
    await design_architecture()
    seq_time = time.time() - start_seq

    # Parallel execution
    start_par = time.time()
    await asyncio.gather(
        research_modal_api(),
        research_together_api(),
        design_architecture(),
    )
    par_time = time.time() - start_par

    # Parallel should be faster (within margin for overhead)
    assert par_time < seq_time


@pytest.mark.asyncio
async def test_full_pipeline_completes_under_time_limit():
    """Test that full pipeline completes in reasonable time."""
    import time

    start = time.time()

    # Execute full pipeline (simplified)
    planning = await asyncio.gather(
        research_modal_api(),
        research_together_api(),
        design_architecture(),
        write_technical_spec(),
    )

    tests = await asyncio.gather(
        write_adapter_tests(),
        write_integration_tests(),
        write_cli_tests(),
    )

    impl = await asyncio.gather(
        implement_modal_adapter(),
        implement_together_adapter(),
        implement_cli_commands(),
    )

    ci_result = await run_ci_pipeline()
    deploy_result = await deploy_to_staging(ci_result)

    elapsed = time.time() - start

    # Should complete in under 5 seconds (all tasks are fast mocks)
    assert elapsed < 5.0
    assert deploy_result["status"] == "success"
