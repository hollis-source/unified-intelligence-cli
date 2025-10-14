"""Manual Test for Claude Orchestrator - Run via Claude with MCP SSH tools.

This test uses Claude's MCP SSH tools directly for authentication.
For standalone execution, SSH keys must be configured.
"""

from datetime import datetime

from src.claude_orchestrator.entities.worker import WorkerPoolConfig
from src.claude_orchestrator.entities.generated_task import GeneratedTask


# Create simple test task
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

config = WorkerPoolConfig(
    pool_type="ssh",
    max_workers=1,
    ssh_host="ui-cli_jake@syd2.jacobhollis.com",
    working_dir="/home/ui-cli_jake/autonomous-task-agent-dev-orchestration",
    model_name="sonnet4",
)

task = GeneratedTask.create(
    id=f"orchestrator-test-{timestamp}",
    instruction=f"""Create a test file to verify orchestrator works:

echo "Claude Orchestrator Test - {timestamp}" > /tmp/orchestrator_test_{timestamp}.txt
echo "Status: SUCCESS" >> /tmp/orchestrator_test_{timestamp}.txt
cat /tmp/orchestrator_test_{timestamp}.txt
""",
    rationale="Manual test of Claude Orchestrator MVP",
    goal_id="testing",
    estimated_minutes=1,
    priority="P0",
)

print("=== Claude Orchestrator Manual Test ===")
print(f"Task ID: {task.id}")
print(f"Instruction: {task.instruction[:100]}...")
print(f"\nConfig: SSH to {config.ssh_host}")
print(f"Working dir: {config.working_dir}")
print(f"Model: {config.model_name}")
print("\nReady to execute!")
