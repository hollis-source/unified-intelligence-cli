"""Phase 1: Priority Worker Implementation Tasks

Clean Architecture: Tasks layer for priority worker implementation.
SOLID: SRP - each task designs one component.
"""

import asyncio
from typing import Any, Dict


async def design_priority_worker(input_data: Any = None) -> Dict[str, Any]:
    """
    Design full PriorityWorker implementation.

    Analyzes:
    - Core worker loop (continuous daemon)
    - Task claiming strategy (atomic operations)
    - Workflow execution integration
    - Error handling and retry logic
    - Status tracking and updates

    Returns:
        WorkerDesign with architecture and implementation details
    """
    cmd = [
        "./bin/atado",
        "--provider", "auto",
        "--routing", "team",
        "--agents", "scaled",
        "--orchestrator", "simple",
        "--verbose",
        "--timeout", "240",
        "--task",
        "ULTRATHINK: Design full PriorityWorker implementation for Phase 1.\n\n"
        "Context: Phase 0 complete (minimal prototype working).\n"
        "Prototype: scripts/minimal_priority_worker.py (338 lines, atomic claiming via git).\n"
        "Architecture: SYD2-like continuous daemon, 24h cycles.\n\n"
        "Requirements:\n"
        "1. Main daemon loop (similar to SYD2Agent.run())\n"
        "2. Atomic priority claiming (Redis + Git double-lock)\n"
        "3. DSL workflow execution via CLITaskExecutor\n"
        "4. Branch creation and management\n"
        "5. Error handling with retry (use SYD2 enhancements)\n"
        "6. Status updates (open → claimed → in_progress → completed/failed)\n"
        "7. Metrics tracking (throughput, latency, success rate)\n"
        "8. Graceful shutdown and cleanup\n\n"
        "Design Approach:\n"
        "- Clean Architecture: Entities, Use Cases, Adapters\n"
        "- SOLID principles (SRP, OCP, DIP)\n"
        "- Composition over inheritance\n"
        "- Dependency injection\n\n"
        "Output:\n"
        "- Class structure (PriorityWorker with methods)\n"
        "- Main loop algorithm (pseudocode)\n"
        "- Integration points (Redis, Git, DSL executor)\n"
        "- Error handling strategy\n"
        "- Configuration schema\n"
        "- Estimated LOC and complexity"
    ]

    return await _run_cli_task(cmd, "design_priority_worker")


async def design_redis_queue(input_data: Any = None) -> Dict[str, Any]:
    """
    Design Redis-based queue for fast atomic claiming.

    Analyzes:
    - Redis data structures (lists, sorted sets, hashes)
    - Atomic operations (LPOP, ZADD, HSET)
    - TTL-based auto-release
    - Pub/Sub for notifications
    - Fallback to file-based queue

    Returns:
        QueueDesign with Redis schema and operations
    """
    cmd = [
        "./bin/atado",
        "--provider", "auto",
        "--routing", "team",
        "--agents", "scaled",
        "--orchestrator", "simple",
        "--verbose",
        "--timeout", "180",
        "--task",
        "ULTRATHINK: Design Redis queue integration for priority claiming.\n\n"
        "Context: Git-based claiming works but has latency (~1-2s per claim attempt).\n"
        "Goal: Add Redis for millisecond-level atomic operations.\n\n"
        "Requirements:\n"
        "1. Fast atomic claiming (RPOPLPUSH or similar)\n"
        "2. Priority ordering (sorted sets with priority scores)\n"
        "3. Auto-release on timeout (TTL or EXPIRE)\n"
        "4. Worker registration and heartbeat\n"
        "5. Claim tracking (who claimed what, when)\n"
        "6. Fallback to file-based queue if Redis unavailable\n\n"
        "Redis Data Structures:\n"
        "- priorities:queue (sorted set: priority_id → score)\n"
        "- priorities:claims (hash: priority_id → worker_id)\n"
        "- priorities:heartbeats (hash: worker_id → timestamp)\n"
        "- priorities:channel (pub/sub for new priorities)\n\n"
        "Output:\n"
        "- RedisQueue class design\n"
        "- Key operations (claim, release, heartbeat)\n"
        "- Atomic Lua scripts for complex operations\n"
        "- Error handling and fallback strategy\n"
        "- Configuration (host, port, db, timeout)"
    ]

    return await _run_cli_task(cmd, "design_redis_queue")


async def design_git_integration(input_data: Any = None) -> Dict[str, Any]:
    """
    Design Git integration for branches and commits.

    Analyzes:
    - Branch creation (bot/priority-{id})
    - Commit strategies (atomic updates)
    - Push/pull coordination
    - Conflict resolution
    - State synchronization

    Returns:
        GitDesign with branch management and commit strategies
    """
    cmd = [
        "./bin/atado",
        "--provider", "auto",
        "--routing", "team",
        "--agents", "scaled",
        "--orchestrator", "simple",
        "--verbose",
        "--timeout", "180",
        "--task",
        "ULTRATHINK: Design Git integration for priority worker.\n\n"
        "Context: Worker commits results to branches, creates PRs.\n"
        "Prototype: Uses git commands via subprocess.\n\n"
        "Requirements:\n"
        "1. Branch creation (bot/priority-{id})\n"
        "2. Checkout and isolation from main\n"
        "3. Commit workflow results with detailed messages\n"
        "4. Push to remote (handle auth, SSH keys)\n"
        "5. Sync priorities.yaml state (atomic updates)\n"
        "6. Conflict detection and resolution\n"
        "7. Cleanup old branches after merge\n\n"
        "Operations:\n"
        "- create_branch(priority_id) → branch_name\n"
        "- commit_results(workflow_output, priority) → commit_sha\n"
        "- push_branch(branch_name) → success/failure\n"
        "- sync_priority_state(priority_id, status, **updates)\n"
        "- cleanup_branch(branch_name) → success/failure\n\n"
        "Output:\n"
        "- GitStateManager class design\n"
        "- Atomic state update algorithm\n"
        "- Conflict resolution strategy\n"
        "- SSH key configuration\n"
        "- Git command error handling"
    ]

    return await _run_cli_task(cmd, "design_git_integration")


async def design_pr_automation(input_data: Any = None) -> Dict[str, Any]:
    """
    Design GitHub PR automation for completed work.

    Analyzes:
    - PR creation via GitHub API or gh CLI
    - PR description generation
    - Label assignment (bot-generated, priority level)
    - Reviewer assignment
    - Status checks integration

    Returns:
        PRDesign with automation strategy
    """
    cmd = [
        "./bin/atado",
        "--provider", "auto",
        "--routing", "team",
        "--agents", "scaled",
        "--orchestrator", "simple",
        "--verbose",
        "--timeout", "180",
        "--task",
        "ULTRATHINK: Design GitHub PR automation for priority worker.\n\n"
        "Context: Worker completes priority, needs to create PR for review.\n"
        "Tools: GitHub API or gh CLI (prefer gh CLI for simplicity).\n\n"
        "Requirements:\n"
        "1. Auto-create PR from bot/priority-{id} → master\n"
        "2. Generate detailed PR description:\n"
        "   - Priority title and description\n"
        "   - Workflow executed\n"
        "   - Results summary\n"
        "   - Artifacts list\n"
        "   - Testing checklist\n"
        "3. Add labels (bot-generated, priority-{level})\n"
        "4. Assign reviewers (optional, configurable)\n"
        "5. Link to priority in priorities.yaml\n"
        "6. Include success criteria for review\n\n"
        "PR Description Template:\n"
        "## Priority: {id}\n"
        "{title}\n\n"
        "**Workflow**: {workflow_path}\n"
        "**Effort**: {effort_hours}h\n\n"
        "## Results\n"
        "✅ Workflow executed successfully\n\n"
        "**Artifacts**:\n"
        "- {artifact_list}\n\n"
        "## Testing\n"
        "- [ ] Review workflow output\n"
        "- [ ] Verify no regressions\n"
        "- [ ] Check code quality\n"
        "- [ ] Merge when ready\n\n"
        "🤖 Autonomous execution by {worker_id}\n\n"
        "Output:\n"
        "- PRAutomation class design\n"
        "- create_pull_request() method\n"
        "- Description template rendering\n"
        "- gh CLI integration\n"
        "- Error handling (PR already exists, etc.)"
    ]

    return await _run_cli_task(cmd, "design_pr_automation")


async def synthesize_implementation(input_data: Any = None) -> Dict[str, Any]:
    """
    Synthesize all designs into concrete implementation plan.

    Takes parallel design outputs and creates:
    - File structure
    - Implementation order
    - Integration points
    - Testing strategy
    - Deployment plan

    Returns:
        ImplementationPlan with step-by-step tasks
    """
    # Extract and flatten design results
    if isinstance(input_data, tuple):
        designs = _flatten_tuple(input_data)
        designs_text = "\n\n".join([
            f"Design {i+1}: {d.get('task', 'unknown')}\n{_format_output(d)}"
            for i, d in enumerate(designs)
        ])
    else:
        designs_text = str(input_data)

    cmd = [
        "./bin/atado",
        "--provider", "auto",
        "--routing", "team",
        "--agents", "scaled",
        "--orchestrator", "simple",
        "--verbose",
        "--timeout", "300",
        "--task",
        f"ULTRATHINK: Synthesize Phase 1 implementation plan from designs.\n\n"
        f"Context: Four parallel designs completed:\n"
        f"1. PriorityWorker main implementation\n"
        f"2. Redis queue integration\n"
        f"3. Git branch/commit management\n"
        f"4. GitHub PR automation\n\n"
        f"Designs:\n{designs_text}\n\n"
        f"Requirements:\n"
        f"1. Create concrete file structure:\n"
        f"   - scripts/priority_worker.py (main daemon)\n"
        f"   - src/priority_queue/redis_queue.py\n"
        f"   - src/priority_queue/git_state.py\n"
        f"   - src/priority_queue/pr_automation.py\n"
        f"   - config/priority_worker.yaml\n"
        f"   - tests/test_priority_worker.py\n\n"
        f"2. Implementation order (dependencies):\n"
        f"   - Which components first?\n"
        f"   - Integration sequence\n"
        f"   - Testing checkpoints\n\n"
        f"3. Integration points:\n"
        f"   - How components connect\n"
        f"   - Dependency injection\n"
        f"   - Configuration flow\n\n"
        f"4. Testing strategy:\n"
        f"   - Unit tests per component\n"
        f"   - Integration tests\n"
        f"   - Mock Redis for testing\n\n"
        f"5. Effort estimates:\n"
        f"   - Time per component\n"
        f"   - Total implementation time\n"
        f"   - Complexity assessment\n\n"
        f"Output Format:\n"
        f"- Step-by-step implementation tasks (numbered)\n"
        f"- File-by-file specifications\n"
        f"- Code structure (classes, methods)\n"
        f"- Testing requirements\n"
        f"- Success criteria for Phase 1 completion"
    ]

    return await _run_cli_task(cmd, "synthesize_implementation")


# Helper functions (reuse from other task modules)

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


def _format_output(design: Any) -> str:
    """Format design output."""
    if isinstance(design, dict):
        if 'output' in design:
            output = design['output']
            # Truncate for context
            if len(output) > 1000:
                return output[:500] + "\n...\n" + output[-500:]
            return output
        else:
            import json
            return json.dumps(design, indent=2)
    else:
        return str(design)
