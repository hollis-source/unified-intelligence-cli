# Hierarchical Priority System Design

**Problem Statement:**
Current flat task model causes orphaned work - ULTRATHINK analyses generate tasks that become stale when parent priorities change, but system doesn't detect this.

**Requirements:**
1. Parent-child task hierarchy
2. Automatic staleness detection
3. Context linking (tasks remember parent state)
4. ULTRATHINK output tagging

## Architecture

### Core Entities

```python
@dataclass(frozen=True)
class Priority:
    """Top-level priority (user-defined goal)."""
    id: str  # e.g., "autonomous-container-deployment"
    title: str
    context: str  # Current state, goals, constraints
    context_hash: str  # SHA256 of context for staleness detection
    status: str  # active, paused, abandoned, completed
    created_at: datetime
    updated_at: datetime

@dataclass(frozen=True)
class Task:
    """Implementation task (spawned from priority or ULTRATHINK)."""
    id: str
    parent_priority_id: str  # Links to Priority.id
    parent_context_hash: str  # Context hash when task was created
    description: str
    priority: int  # 1-5 for ordering
    status: str  # open, claimed, in_progress, completed, failed, stale
    is_stale: bool  # Auto-set if parent context changed
    spawned_by: str  # "user" | "ultrathink" | "analysis"
    metadata: Dict[str, Any]
```

### Staleness Detection

```python
def check_staleness(task: Task, priority: Priority) -> bool:
    """Return True if task is stale (parent context changed)."""
    return task.parent_context_hash != priority.context_hash

def mark_children_stale(priority_id: str) -> None:
    """When priority context changes, mark all children stale."""
    tasks = get_tasks_by_parent(priority_id)
    for task in tasks:
        if not check_staleness(task, get_priority(priority_id)):
            continue
        update_task_status(task.id, status='stale', is_stale=True)
```

### Worker Integration

```python
async def claim_task(worker: PriorityWorker, task: Task) -> bool:
    """Claim task, but skip if stale."""
    # Check staleness before claiming
    parent = get_priority(task.parent_priority_id)
    if check_staleness(task, parent):
        logger.warning(f"Task {task.id} is stale (parent context changed)")
        update_task_status(task.id, status='stale', is_stale=True)
        return False

    # Standard claiming logic
    return await worker.atomic_claim(task)
```

### ULTRATHINK Integration

When spawning ULTRATHINK analysis:

```python
def spawn_ultrathink_analysis(priority: Priority, analysis_type: str) -> str:
    """Spawn ULTRATHINK background process, tag with parent."""
    task_description = f"""ULTRATHINK: {analysis_type}

Parent Priority: {priority.id}
Parent Context Hash: {priority.context_hash}
Context: {priority.context}

[analysis requirements...]
"""

    # Spawn with metadata
    task_id = submit_task(
        description=task_description,
        parent_priority_id=priority.id,
        parent_context_hash=priority.context_hash,
        spawned_by="ultrathink",
        metadata={
            "analysis_type": analysis_type,
            "parent_priority": priority.id
        }
    )

    return task_id
```

When ULTRATHINK outputs implementation recommendations:

```python
def process_ultrathink_output(analysis_task_id: str, recommendations: List[Dict]) -> List[str]:
    """Convert ULTRATHINK recommendations to implementation tasks."""
    analysis_task = get_task(analysis_task_id)
    parent_priority = get_priority(analysis_task.parent_priority_id)

    # Check if analysis is still valid
    if check_staleness(analysis_task, parent_priority):
        logger.warning(f"ULTRATHINK analysis {analysis_task_id} is stale, skipping recommendations")
        return []

    # Create implementation tasks linked to same parent
    task_ids = []
    for rec in recommendations:
        task_id = submit_task(
            description=rec['description'],
            parent_priority_id=parent_priority.id,
            parent_context_hash=parent_priority.context_hash,
            spawned_by=f"ultrathink:{analysis_task_id}",
            priority=rec['priority'],
            metadata={
                "ultrathink_source": analysis_task_id,
                **rec.get('metadata', {})
            }
        )
        task_ids.append(task_id)

    return task_ids
```

## Data Model (Redis)

```
# Priorities
priority:{priority_id} -> Hash {
    id, title, context, context_hash, status, created_at, updated_at
}

# Priority index
priorities:active -> Set of active priority IDs
priorities:all -> List of all priority IDs

# Tasks (existing, enhanced)
task_status:{task_id} -> Hash {
    id, parent_priority_id, parent_context_hash, description,
    priority, status, is_stale, spawned_by, metadata
}

# Parent-child index
priority_children:{priority_id} -> Set of child task IDs

# Queue (existing)
priority_queue -> List of task IDs (sorted by priority)
```

## Migration Strategy

### Phase 1: Add parent tracking (no staleness yet)
1. Add `parent_priority_id`, `parent_context_hash` fields to Task
2. Create default priority for existing tasks
3. Update submit_task() to require parent

### Phase 2: Staleness detection
1. Implement check_staleness()
2. Add staleness check to worker claim logic
3. Add mark_children_stale() hook when priorities update

### Phase 3: ULTRATHINK integration
1. Tag ULTRATHINK spawns with parent metadata
2. Process ULTRATHINK outputs → implementation tasks
3. Automatic staleness for abandoned analyses

## Example Flow

```
1. User creates priority:
   Priority(
       id="autonomous-container",
       context="Deploy PriorityWorker in Docker for 3-5x throughput",
       context_hash="abc123..."
   )

2. Spawn ULTRATHINK analyses (8 background processes):
   - feasibility-analysis (parent: autonomous-container, hash: abc123)
   - design-analysis (parent: autonomous-container, hash: abc123)
   - docker-strategy (parent: autonomous-container, hash: abc123)
   [etc.]

3. ULTRATHINK outputs recommendations:
   - implement-redis-dedup (parent: autonomous-container, hash: abc123, spawned_by: ultrathink:feasibility-analysis)
   - add-metrics-dashboard (parent: autonomous-container, hash: abc123, spawned_by: ultrathink:design-analysis)
   [etc.]

4. User updates priority context (pivot):
   Priority(
       id="autonomous-container",
       context="Actually, focus on native systemd deployment instead",
       context_hash="def456..."  # CHANGED
   )

5. System auto-marks children stale:
   - implement-redis-dedup → status=stale (hash mismatch)
   - add-metrics-dashboard → status=stale (hash mismatch)

6. Worker skips stale tasks:
   - poll_tasks() filters out stale=True
   - claim_task() double-checks staleness before claiming
```

## Benefits

1. **No orphaned work**: Tasks auto-invalidate when parent context changes
2. **Transparent traceability**: Every task links to parent priority
3. **ULTRATHINK accountability**: Know which analysis spawned each task
4. **Automatic cleanup**: Stale detection prevents wasted effort
5. **Context preservation**: Tasks remember parent state at spawn time

## Implementation Estimate

- **Entities layer**: +50 LOC (Priority dataclass, staleness methods)
- **Adapters layer**: +100 LOC (Redis priority storage, parent-child index)
- **Use cases layer**: +80 LOC (mark_children_stale, staleness checks)
- **Worker changes**: +30 LOC (staleness check in claim logic)
- **ULTRATHINK wrapper**: +120 LOC (auto-tagging, output processing)
- **Migration script**: +150 LOC (convert existing tasks)

**Total**: ~530 LOC, estimated 4-6 hours for full implementation + testing

## Next Steps

1. Review this design for accuracy
2. Implement Phase 1 (parent tracking)
3. Test with current 4 real tasks
4. Implement Phase 2 (staleness)
5. Implement Phase 3 (ULTRATHINK integration)
6. Apply to 8 background ULTRATHINK processes
