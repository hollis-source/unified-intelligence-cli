# Priority Worker Coordination Protocol

**Problem:** Autonomous priority workers completing tasks faster than humans can integrate them leads to stale, conflicting work.

**Solution:** Git-based lock-step coordination using priorities.yaml as state machine.

---

## State Machine

### States

```
open
  ↓ [worker claims]
claimed
  ↓ [worker executes]
in_progress
  ↓ [worker completes + creates PR]
pending_review
  ↓ [human reviews + merges PR]
integrated
  ↓ [worker confirms]
completed
```

### State Definitions

| State | Owner | Meaning | Next Action |
|-------|-------|---------|-------------|
| `open` | None | Available for claiming | Worker can claim |
| `claimed` | Worker | Reserved, not started | Worker starts execution |
| `in_progress` | Worker | Currently executing | Worker completes |
| `pending_review` | Human | Completed, awaiting review | Human reviews PR |
| `integrated` | Worker | Merged, ready to finalize | Worker marks complete |
| `completed` | None | Fully done | Archive |

---

## Protocol

### Worker Behavior

**1. Task Discovery**
```python
def find_claimable_task(priorities: List[Priority]) -> Optional[Priority]:
    """Find task that worker can claim."""
    for priority in priorities:
        if (
            priority.status == "open"
            and priority.claimed_by is None
            and priority.priority in ["low", "medium"]  # Configurable
            and priority.complexity in ["low"]  # Start conservative
            and priority.get("autonomous", False) == True  # Opt-in flag
            and priority.get("requires_integration", True)  # Default: yes
        ):
            return priority
    return None
```

**2. Claim Task**
```python
def claim_task(priority: Priority, worker_id: str) -> None:
    """Claim task for execution."""
    priority.status = "claimed"
    priority.claimed_by = worker_id
    priority.claimed_at = datetime.now().isoformat()
    save_priorities()  # Commit to git
```

**3. Execute Task**
```python
async def execute_task(priority: Priority) -> ExecutionResult:
    """Execute task via Project Builder or direct implementation."""
    priority.status = "in_progress"
    priority.started_at = datetime.now().isoformat()
    save_priorities()

    # Execute (Project Builder, direct code, etc.)
    result = await execute_priority(priority)

    return result
```

**4. Create PR and Mark Pending**
```python
def complete_task(priority: Priority, result: ExecutionResult) -> None:
    """Mark task complete and create PR for review."""
    # Create branch and PR
    branch = f"priority/{priority.id}"
    pr_url = create_pull_request(
        branch=branch,
        title=priority.title,
        body=generate_pr_body(priority, result),
        files=result.changed_files
    )

    # Update state
    priority.status = "pending_review"
    priority.pr_url = pr_url
    priority.completed_at = datetime.now().isoformat()
    priority.artifacts = result.artifacts
    save_priorities()  # Commit to git
```

**5. Wait for Integration**
```python
async def wait_for_integration(priority: Priority, timeout_hours: int = 24) -> bool:
    """Poll priorities.yaml until human integrates (or timeout)."""
    start = datetime.now()

    while (datetime.now() - start).total_seconds() < timeout_hours * 3600:
        # Pull latest from git
        subprocess.run(["git", "pull", "origin", "main"], check=True)

        # Reload priorities
        priorities = load_priorities()
        current = find_priority_by_id(priorities, priority.id)

        if current.status == "integrated":
            # Human has integrated!
            return True

        # Wait 5 minutes before checking again
        await asyncio.sleep(300)

    # Timeout - human hasn't integrated yet
    logger.warning(f"Integration timeout for {priority.id}")
    return False
```

**6. Finalize and Continue**
```python
def finalize_task(priority: Priority) -> None:
    """Mark task fully completed after integration."""
    priority.status = "completed"
    save_priorities()

    logger.info(f"Task {priority.id} fully integrated and completed")
```

### Human Behavior

**1. Check for Pending Reviews**
```bash
# Check priorities.yaml for pending_review tasks
grep -A 20 "status: \"pending_review\"" priorities.yaml

# Or use helper script
python scripts/check_pending_reviews.py
```

**2. Review PR**
```bash
# Check out PR branch
git fetch origin
git checkout priority/task-123

# Review changes
git diff main...priority/task-123

# Run tests
pytest tests/

# Run Project Builder validation (if applicable)
python -m src.project_builder.cli.command --validate
```

**3. Integrate PR**
```bash
# If approved, merge
git checkout main
git merge priority/task-123
git push origin main
```

**4. Update Priority Status**
```python
# Update priorities.yaml
def mark_integrated(priority_id: str) -> None:
    """Mark priority as integrated after merging PR."""
    priorities = load_priorities()
    priority = find_priority_by_id(priorities, priority_id)

    priority.status = "integrated"
    priority.integrated_at = datetime.now().isoformat()
    priority.integrated_by = "human-reviewer-name"

    save_priorities()  # Commit to git
```

Or use helper script:
```bash
python scripts/mark_priority_integrated.py --id task-123
```

---

## Priority Schema Updates

### New Fields

```yaml
priorities:
  - id: "example_task"
    title: "Example Task"
    status: "open"  # open, claimed, in_progress, pending_review, integrated, completed

    # Autonomous execution flags (NEW)
    autonomous: true  # Whether autonomous workers can claim this
    requires_integration: true  # Whether human integration is required (default: true)
    batch_allowed: false  # Whether this can be batched with other tasks (default: false)

    # Integration tracking (NEW)
    pending_review_at: null  # When task moved to pending_review
    integrated_at: null  # When human marked as integrated
    integrated_by: null  # Who integrated it

    # Existing fields
    claimed_by: null
    claimed_at: null
    started_at: null
    completed_at: null
    pr_url: null
    branch: null
    artifacts: []
```

---

## Configuration

### Worker Config (syd2_agent.yml or priority_worker_config.yml)

```yaml
priority_worker:
  # Claiming behavior
  poll_interval_seconds: 300  # Check for new tasks every 5 minutes
  max_concurrent_tasks: 1  # Lock-step: only 1 task at a time

  # Task selection
  eligible_priorities: ["low", "medium"]  # Which priorities to claim
  eligible_complexity: ["low"]  # Start conservative
  require_autonomous_flag: true  # Only claim tasks marked autonomous=true

  # Integration wait
  integration_poll_interval_seconds: 300  # Check for integration every 5 minutes
  integration_timeout_hours: 24  # Give up after 24 hours

  # Behavior on timeout
  timeout_action: "unclaim"  # Options: "unclaim", "keep", "alert"
```

---

## Safety Mechanisms

### 1. Timeout Recovery
```python
def handle_integration_timeout(priority: Priority) -> None:
    """Handle case where human doesn't integrate within timeout."""
    # Unclaim task so another worker (or human) can take it
    priority.status = "open"
    priority.claimed_by = None
    priority.timeout_count = priority.get("timeout_count", 0) + 1

    # Alert if this keeps timing out
    if priority.timeout_count >= 3:
        send_alert(f"Task {priority.id} has timed out 3 times - may need review")

    save_priorities()
```

### 2. Conflict Detection
```python
def check_for_conflicts(priority: Priority) -> bool:
    """Check if main branch has diverged significantly since task started."""
    # Get commits on main since task started
    start_time = priority.started_at
    commits_since = get_commits_since(start_time)

    # Check if any commits touch same files
    task_files = set(priority.artifacts.get("files_modified", []))
    for commit in commits_since:
        if any(f in task_files for f in commit.files):
            logger.warning(f"Potential conflict in {priority.id}")
            return True

    return False
```

### 3. Stale Task Prevention
```python
def is_task_stale(priority: Priority, max_age_hours: int = 72) -> bool:
    """Check if pending_review task is too old (likely stale)."""
    if priority.status != "pending_review":
        return False

    pending_since = datetime.fromisoformat(priority.pending_review_at)
    age = datetime.now() - pending_since

    if age.total_seconds() > max_age_hours * 3600:
        logger.warning(f"Task {priority.id} pending for {age.total_seconds() / 3600:.1f} hours")
        return True

    return False
```

---

## Workflow Examples

### Example 1: Successful Lock-Step Execution

**T+0:00** - Worker discovers task
```yaml
- id: "add_docstrings_utils"
  status: "open"
  autonomous: true
```

**T+0:01** - Worker claims and executes
```yaml
- id: "add_docstrings_utils"
  status: "in_progress"
  claimed_by: "syd2-auggie"
```

**T+0:15** - Worker completes, creates PR
```yaml
- id: "add_docstrings_utils"
  status: "pending_review"
  pr_url: "https://github.com/.../pull/123"
```

**T+2:00** - Human reviews and merges PR

**T+2:05** - Human updates status
```yaml
- id: "add_docstrings_utils"
  status: "integrated"
  integrated_by: "jake"
```

**T+2:10** - Worker detects integration
```yaml
- id: "add_docstrings_utils"
  status: "completed"
```

**T+2:11** - Worker starts next task (cycle repeats)

---

### Example 2: Batch Mode (Optional Future Enhancement)

If task has `batch_allowed: true`:
- Worker can claim up to N tasks (e.g., 5)
- Executes all, creates 5 separate PRs
- Waits for ALL 5 to be integrated before continuing
- Useful for: documentation tasks, test additions, simple refactors

---

## Helper Scripts

### check_pending_reviews.py
```python
#!/usr/bin/env python3
"""Check for priorities awaiting review."""
import yaml
from datetime import datetime

def main():
    with open("priorities.yaml") as f:
        data = yaml.safe_load(f)

    pending = [p for p in data["priorities"] if p.get("status") == "pending_review"]

    if not pending:
        print("✓ No pending reviews")
        return

    print(f"⚠️  {len(pending)} tasks awaiting review:\n")
    for p in pending:
        age = datetime.now() - datetime.fromisoformat(p["pending_review_at"])
        print(f"- {p['id']}: {p['title']}")
        print(f"  PR: {p['pr_url']}")
        print(f"  Pending for: {age.total_seconds() / 3600:.1f} hours")
        print()

if __name__ == "__main__":
    main()
```

### mark_integrated.py
```python
#!/usr/bin/env python3
"""Mark priority as integrated after merging PR."""
import sys
import yaml
from datetime import datetime

def main():
    if len(sys.argv) < 2:
        print("Usage: python mark_integrated.py <priority_id>")
        sys.exit(1)

    priority_id = sys.argv[1]

    with open("priorities.yaml") as f:
        data = yaml.safe_load(f)

    for p in data["priorities"]:
        if p["id"] == priority_id:
            p["status"] = "integrated"
            p["integrated_at"] = datetime.now().isoformat()
            p["integrated_by"] = "human"  # Or get from git config

            with open("priorities.yaml", "w") as f:
                yaml.dump(data, f, sort_keys=False)

            print(f"✓ Marked {priority_id} as integrated")
            return

    print(f"✗ Priority {priority_id} not found")

if __name__ == "__main__":
    main()
```

---

## Benefits

### Lock-Step Advantages
1. **No Stale Work** - Every completion is integrated before next task
2. **Tight Sync** - Local dev and worker stay in lock-step
3. **Conflict Prevention** - Human reviews before conflicts grow
4. **Quality Control** - Human validates each completion
5. **Auditable** - Clear state transitions in priorities.yaml

### Trade-offs Accepted
1. **Lower Throughput** - 1 task at a time vs batch
2. **Human Bottleneck** - Worker waits for human review
3. **Latency** - 5 min poll intervals add overhead

---

## Future Enhancements

1. **Batch Mode** - Allow N tasks in parallel for low-risk work
2. **Auto-merge** - For tasks with 100% test pass + no conflicts
3. **Priority Escalation** - Notify human if pending too long
4. **Conflict Auto-resolve** - For non-overlapping changes
5. **Dashboard** - Visual status of all priorities

---

## Success Metrics

**Targets:**
- Integration lag < 4 hours (median)
- Stale task rate < 5% (tasks that time out)
- Conflict rate < 2% (PRs requiring manual conflict resolution)
- Worker utilization > 60% (not waiting too long)

---

**Document Version:** 1.0
**Last Updated:** 2025-10-13
**Status:** Design Complete, Ready for Implementation
