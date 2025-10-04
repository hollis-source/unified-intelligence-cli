"""Priority Worker Implementation Tasks

Clean Architecture: Tasks layer for code generation.
SOLID: SRP - each task implements one architectural layer.
"""

import asyncio
from typing import Any, Dict


async def implement_entities(input_data: Any = None) -> Dict[str, Any]:
    """
    Generate Entities layer code (Task, Metrics).

    Implements core data models with no dependencies.

    Returns:
        EntitiesCode with Python implementation
    """
    cmd = [
        "./bin/ui-cli",
        "--provider", "auto",
        "--routing", "team",
        "--agents", "scaled",
        "--orchestrator", "simple",
        "--verbose",
        "--timeout", "180",
        "--task",
        "ULTRATHINK: Generate Python code for Entities layer.\n\n"
        "Design Spec (from previous ULTRATHINK):\n"
        "- Task entity: id, priority, status (open/claimed/in_progress/completed/failed), metadata\n"
        "- Metrics entity: throughput (tasks/hour), latency (seconds), success_rate (float)\n\n"
        "Requirements:\n"
        "1. Use Python dataclasses (immutable with frozen=True)\n"
        "2. Type hints for all fields\n"
        "3. Validation methods (e.g., is_valid_status())\n"
        "4. Clean Architecture: No dependencies on other layers\n"
        "5. SOLID: SRP (single responsibility per entity)\n\n"
        "File: src/priority_queue/entities.py\n\n"
        "Output: Complete Python code ready to save to file.\n"
        "Include: imports, dataclasses, validation, docstrings."
    ]

    return await _run_cli_task(cmd, "implement_entities")


async def implement_use_cases(input_data: Any = None) -> Dict[str, Any]:
    """
    Generate Use Cases layer code (7 use cases).

    Implements business logic depending only on entities and interfaces.

    Returns:
        UseCasesCode with Python implementation
    """
    cmd = [
        "./bin/ui-cli",
        "--provider", "auto",
        "--routing", "team",
        "--agents", "scaled",
        "--orchestrator", "simple",
        "--verbose",
        "--timeout", "240",
        "--task",
        "ULTRATHINK: Generate Python code for Use Cases layer.\n\n"
        "Design Spec (from previous ULTRATHINK):\n"
        "7 use cases:\n"
        "1. ClaimTaskUseCase: Atomic claiming via adapters\n"
        "2. ExecuteWorkflowUseCase: Run DSL via CLITaskExecutor\n"
        "3. ManageBranchesUseCase: Git branch creation/management\n"
        "4. HandleErrorsUseCase: Retry with exponential backoff\n"
        "5. UpdateStatusUseCase: Status transitions\n"
        "6. TrackMetricsUseCase: Calculate/log metrics\n"
        "7. ShutdownUseCase: Graceful cleanup\n\n"
        "Requirements:\n"
        "1. Each use case as a class with execute() method\n"
        "2. Depend on interfaces (LockInterface, VCInterface, ExecutorInterface)\n"
        "3. Use entities (Task, Metrics)\n"
        "4. Async methods where appropriate\n"
        "5. Error handling with logging\n"
        "6. SOLID: DIP (depend on abstractions), SRP\n\n"
        "File: src/priority_queue/use_cases.py\n\n"
        "Output: Complete Python code with all 7 use cases.\n"
        "Include: interfaces (ABC), use case classes, type hints, docstrings."
    ]

    return await _run_cli_task(cmd, "implement_use_cases")


async def implement_adapters(input_data: Any = None) -> Dict[str, Any]:
    """
    Generate Adapters layer code (4 adapters).

    Implements external integrations (Redis, Git, CLI, Logger).

    Returns:
        AdaptersCode with Python implementation
    """
    cmd = [
        "./bin/ui-cli",
        "--provider", "auto",
        "--routing", "team",
        "--agents", "scaled",
        "--orchestrator", "simple",
        "--verbose",
        "--timeout", "240",
        "--task",
        "ULTRATHINK: Generate Python code for Adapters layer.\n\n"
        "Design Spec (from previous ULTRATHINK):\n"
        "4 adapters:\n"
        "1. RedisAdapter (implements LockInterface): SET with TTL for claiming, caching\n"
        "2. GitAdapter (implements VCInterface): Branch creation, atomic commits\n"
        "3. CLITaskExecutorAdapter (implements ExecutorInterface): Subprocess DSL execution\n"
        "4. LoggerAdapter (implements LoggingInterface): Structured logging\n\n"
        "Requirements:\n"
        "1. Each adapter implements corresponding interface\n"
        "2. Use external libraries (redis, gitpython, subprocess)\n"
        "3. Error handling for external failures\n"
        "4. Configuration via constructor injection\n"
        "5. SOLID: ISP (minimal interfaces), DIP (implement abstractions)\n\n"
        "Files: src/priority_queue/adapters/\n"
        "- redis_adapter.py\n"
        "- git_adapter.py\n"
        "- cli_executor_adapter.py\n"
        "- logger_adapter.py\n\n"
        "Output: Complete Python code for all 4 adapters.\n"
        "Include: imports, adapter classes, error handling, docstrings."
    ]

    return await _run_cli_task(cmd, "implement_adapters")


async def implement_orchestrator(input_data: Any = None) -> Dict[str, Any]:
    """
    Generate PriorityWorker orchestrator code.

    Implements main daemon that composes all components.

    Returns:
        OrchestratorCode with Python implementation
    """
    cmd = [
        "./bin/ui-cli",
        "--provider", "auto",
        "--routing", "team",
        "--agents", "scaled",
        "--orchestrator", "simple",
        "--verbose",
        "--timeout", "240",
        "--task",
        "ULTRATHINK: Generate Python code for PriorityWorker orchestrator.\n\n"
        "Design Spec (from previous ULTRATHINK):\n"
        "- PriorityWorker class composes all use cases and adapters\n"
        "- Constructor: DI for all dependencies\n"
        "- Main run() method: 24h cycle loop (pseudocode provided)\n"
        "- Delegates to use cases for each operation\n"
        "- Graceful shutdown on SIGTERM\n\n"
        "Main Loop (from design):\n"
        "```\n"
        "async def run():\n"
        "    while not shutdown_signal:\n"
        "        open_tasks = poll_tasks()\n"
        "        for task in open_tasks:\n"
        "            if claim_task(task):  # Atomic\n"
        "                update_status(task, 'in_progress')\n"
        "                branch = manage_branches(task)\n"
        "                result = await execute_workflow(task, branch)\n"
        "                update_status(task, 'completed' if success else 'failed')\n"
        "                track_metrics(task)\n"
        "        await asyncio.sleep(24h - elapsed)\n"
        "    shutdown()\n"
        "```\n\n"
        "Requirements:\n"
        "1. Composition over inheritance\n"
        "2. All use cases/adapters injected via constructor\n"
        "3. Configuration loaded from YAML\n"
        "4. Signal handling (SIGTERM, SIGINT)\n"
        "5. Logging at each step\n"
        "6. SOLID: SRP (orchestration only), DIP (depends on interfaces)\n\n"
        "File: scripts/priority_worker.py\n\n"
        "Output: Complete Python code for PriorityWorker.\n"
        "Include: imports, PriorityWorker class, main() entrypoint, signal handling."
    ]

    return await _run_cli_task(cmd, "implement_orchestrator")


async def integrate_components(input_data: Any = None) -> Dict[str, Any]:
    """
    Generate integration code and configuration.

    Creates factory, config schema, and wiring.

    Returns:
        IntegratedSystem with factory and config
    """
    if isinstance(input_data, tuple):
        components = _flatten_tuple(input_data)
        components_summary = "\n\n".join([
            f"Component {i+1}: {c.get('task', 'unknown')}"
            for i, c in enumerate(components)
        ])
    else:
        components_summary = "All components implemented"

    cmd = [
        "./bin/ui-cli",
        "--provider", "auto",
        "--routing", "team",
        "--agents", "scaled",
        "--orchestrator", "simple",
        "--verbose",
        "--timeout", "180",
        "--task",
        f"ULTRATHINK: Generate integration code for PriorityWorker.\n\n"
        f"Components Status:\n{components_summary}\n\n"
        f"Design Spec:\n"
        f"- Factory pattern for component creation\n"
        f"- Configuration schema (YAML)\n"
        f"- Dependency injection wiring\n\n"
        f"Requirements:\n"
        f"1. PriorityWorkerFactory class:\n"
        f"   - create_from_config(config_path) → PriorityWorker\n"
        f"   - Instantiates all use cases and adapters\n"
        f"   - Wires dependencies correctly\n"
        f"2. Configuration schema (from design):\n"
        f"   ```yaml\n"
        f"   priority_worker:\n"
        f"     daemon:\n"
        f"       cycle_hours: 24\n"
        f"     redis:\n"
        f"       host: localhost\n"
        f"       port: 6379\n"
        f"     git:\n"
        f"       repo_path: /path/to/repo\n"
        f"     dsl:\n"
        f"       executor_cmd: python ...\n"
        f"   ```\n"
        f"3. Example usage in main():\n"
        f"   ```python\n"
        f"   factory = PriorityWorkerFactory()\n"
        f"   worker = factory.create_from_config('config.yaml')\n"
        f"   await worker.run()\n"
        f"   ```\n\n"
        f"Files:\n"
        f"- src/priority_queue/factory.py\n"
        f"- config/priority_worker.yaml (template)\n\n"
        f"Output: Factory code and config template."
    ]

    return await _run_cli_task(cmd, "integrate_components")


async def test_system(input_data: Any = None) -> Dict[str, Any]:
    """
    Generate test suite for PriorityWorker.

    Creates unit and integration tests.

    Returns:
        TestResults with pytest code
    """
    cmd = [
        "./bin/ui-cli",
        "--provider", "auto",
        "--routing", "team",
        "--agents", "scaled",
        "--orchestrator", "simple",
        "--verbose",
        "--timeout", "180",
        "--task",
        "ULTRATHINK: Generate pytest test suite for PriorityWorker.\n\n"
        "Requirements:\n"
        "1. Unit tests for each layer:\n"
        "   - test_entities.py: Validate Task, Metrics\n"
        "   - test_use_cases.py: Mock adapters, test logic\n"
        "   - test_adapters.py: Mock external services\n"
        "2. Integration tests:\n"
        "   - test_priority_worker_integration.py\n"
        "   - Test full workflow: claim → execute → update\n"
        "3. Fixtures:\n"
        "   - Mock Redis (fakeredis)\n"
        "   - Mock Git (temporary repo)\n"
        "   - Mock DSL executor\n"
        "4. Coverage target: 80%+\n\n"
        "Testing Strategy:\n"
        "- Entities: Pure data validation\n"
        "- Use Cases: Logic with mocked adapters\n"
        "- Adapters: Integration with mocked externals\n"
        "- Orchestrator: End-to-end with all mocks\n\n"
        "File: tests/priority_queue/\n"
        "- test_entities.py\n"
        "- test_use_cases.py\n"
        "- test_adapters.py\n"
        "- test_integration.py\n"
        "- conftest.py (fixtures)\n\n"
        "Output: Complete pytest test suite.\n"
        "Include: test functions, fixtures, assertions, parametrize."
    ]

    return await _run_cli_task(cmd, "test_system")


# Helper functions

async def _run_cli_task(command: list, task_name: str) -> Dict[str, Any]:
    """Execute CLI command and return parsed result."""
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            output = stdout.decode('utf-8')
            return {
                "task": task_name,
                "status": "success",
                "output": output,
                "raw_output": output
            }
        else:
            error = stderr.decode('utf-8')
            return {
                "task": task_name,
                "status": "failed",
                "error": error
            }

    except Exception as e:
        return {
            "task": task_name,
            "status": "failed",
            "error": str(e)
        }


def _flatten_tuple(t: tuple) -> list:
    """Flatten nested tuple structure."""
    result = []
    for item in t:
        if isinstance(item, tuple):
            result.extend(_flatten_tuple(item))
        else:
            result.append(item)
    return result
