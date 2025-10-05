# Session Continuation Guide

**Last Session**: 2025-10-04 16:30 UTC
**Branch**: priority/prod-010
**Commit**: fdd9367 "Design: Hierarchical Priority System for Task Staleness Prevention"

## Current State

### Problem Identified
- ULTRATHINK-generated tasks become orphaned when parent priorities change
- Container keeps processing old placeholder tasks (prod-001 to prod-010) instead of real tasks
- No staleness detection for background analysis outputs

### Solution Designed
Hierarchical Priority System (3 phases):
- **Phase 1**: Parent tracking (ready to implement)
- **Phase 2**: Staleness detection (deferred)
- **Phase 3**: ULTRATHINK auto-tagging (deferred)

### Files Created
1. `docs/hierarchical_priority_design.md` - Complete architecture (530 LOC, 4-6 hours estimate)
2. `scripts/submit_real_tasks.py` - Real task submission (4 tasks to Redis)
3. `config/priority_worker_docker.yaml` - Modified for 3s cycles (testing mode)

### Current Issues
1. **Container stuck processing old tasks**: Reads from `config/priorities_production.yaml` which has prod-* placeholder tasks
2. **Redis queue clean**: Has 4 real tasks (implement-redis-deduplication, multi-worker-scaling-test, quality-gates-autonomous, monitoring-alerts-integration)
3. **Config mismatch**: Container polls YAML file instead of Redis

## How to Continue This Session

### Method 1: Reference Commit in New Session
```
"Continue from commit fdd9367. Read docs/hierarchical_priority_design.md and implement Phase 1 of hierarchical priority system."
```

### Method 2: Reference Files
```
"Implement hierarchical priority system based on docs/hierarchical_priority_design.md. Previous ULTRATHINK analysis available in git log."
```

### Method 3: Explicit Context
```
"Previous session designed hierarchical priority system (commit fdd9367).
Current task: Implement Phase 1 - add Priority entity, extend Task with parent fields,
update RedisAdapter with CRUD methods. See docs/hierarchical_priority_design.md."
```

## Immediate Next Steps (Phase 1 Implementation)

### 1. Add Priority Entity
**File**: `src/priority_queue/entities.py`
```python
import hashlib
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class Priority:
    """Priority (parent) entity for hierarchical task tracking."""
    id: str
    title: str
    context: str
    status: str  # active, paused, abandoned, completed
    context_hash: str = field(init=False)

    def __post_init__(self):
        self.context_hash = hashlib.sha256(self.context.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'context': self.context,
            'status': self.status,
            'context_hash': self.context_hash
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Priority':
        p = cls(
            id=data['id'],
            title=data['title'],
            context=data['context'],
            status=data['status']
        )
        if 'context_hash' in data:
            p.context_hash = data['context_hash']
        return p
```

### 2. Extend RedisAdapter
**File**: `src/priority_queue/adapters/redis_adapter.py`

Add methods:
- `create_priority(priority: Priority) -> bool`
- `get_priority(priority_id: str) -> Optional[Priority]`
- `update_priority(priority: Priority) -> bool`
- `delete_priority(priority_id: str) -> bool`
- `submit_task()` - add parent_priority_id, parent_context_hash, spawned_by params

Storage keys:
```python
# Priorities
priority:{priority_id} -> Hash

# Parent-child index
priority_children:{priority_id} -> Set of child task IDs
```

### 3. Create Migration Script
**File**: `scripts/migrate_phase1_hierarchy.py`

```python
# Create default priority
default_priority = Priority(
    id='autonomous-container',
    title='Autonomous Container Deployment',
    context='Deploy PriorityWorker in Docker for autonomous parallel work',
    status='active'
)

# Migrate 4 existing Redis tasks
for task_id in ['implement-redis-deduplication', 'multi-worker-scaling-test',
                'quality-gates-autonomous', 'monitoring-alerts-integration']:
    # Add parent_priority_id, parent_context_hash fields
    # Keep existing task data intact
```

### 4. Fix Container Task Source
**Issue**: Container reads `config/priorities_production.yaml` (has old prod-* tasks)
**Fix**: Either:
- A) Update priorities_production.yaml with 4 real tasks
- B) Change worker to poll Redis directly (skip YAML)

## Background ULTRATHINK Processes

8 processes running (ignore per user request):
- feasibility analysis (bash 707522)
- phase1 implementation plan (bash fc54c0)
- design (bash a5e5cf)
- entities implementation (bash 11f8bb)
- deployment strategy (bash ea17ba)
- metrics dashboard (bash 27f496)
- alerting system (bash ad0303)
- docker strategy (bash 3f7c02)
- multi-worker deployment (bash 6e87e8)

## Token Optimization Strategy

**Problem**: Claude Code has 200k token limit (127k used this session)
**Solution**: Use tongyi-local (128k+ context) for long tasks
- Modify `src/adapters/llm/model_orchestrator.py`:
  - Route ULTRATHINK >6k tokens → tongyi-local
  - Keep Grok for quick tasks (<4k tokens)
  - Use qwen3_zerogpu for GPU-heavy tasks

**Implementation**:
```python
if 'ULTRATHINK' in task_description:
    estimated_tokens = len(task_description.split()) * 1.3
    if estimated_tokens > 6000:
        return 'tongyi-local'  # Long context, free
    return 'grok'  # Fast for shorter tasks
```

## Git Workflow

Current branch: `priority/prod-010`

**To continue**:
```bash
# Pull latest commit
git log -1 --oneline  # Should show fdd9367

# Create new branch for Phase 1 implementation
git checkout -b feature/hierarchical-priority-phase1

# Or continue on current branch
git checkout priority/prod-010
```

## Testing Checklist

After implementing Phase 1:

1. **Unit tests**: Priority entity, hash computation
2. **RedisAdapter tests**: CRUD operations, parent-child linking
3. **Migration test**: Run on Redis with 4 tasks, verify parent fields added
4. **Integration test**: Worker polls tasks, sees parent_priority_id
5. **Container test**: Restart priority-worker, verify it processes real tasks (not prod-*)

## Success Criteria

Phase 1 complete when:
- ✅ Priority entity in entities.py
- ✅ RedisAdapter has Priority CRUD methods
- ✅ Tasks in Redis have parent_priority_id field
- ✅ Default priority 'autonomous-container' created
- ✅ Container processes real tasks (not placeholder prod-* tasks)
- ✅ Tests pass
- ✅ Code committed

## Additional Context

- Docker container running: `unified-intelligence-cli_priority-worker_1`
- Redis: `localhost:6379` (clean state, 4 real tasks)
- Config: `config/priority_worker_docker.yaml` (3s cycles for testing)
- Venv: `venv/` (tenacity, gradio-client installed)

## Estimated Effort

- **Phase 1**: 4-6 hours (530 LOC total)
- **Priority entity**: 30 min (50 LOC)
- **RedisAdapter updates**: 1-2 hours (110 LOC)
- **Migration script**: 1 hour (80 LOC)
- **Testing + validation**: 1-2 hours
- **Documentation**: 30 min

---

**To start next session**, simply say:
```
"Continue from CONTINUATION.md - implement Phase 1 of hierarchical priority system"
```

Claude Code will read this file and have full context to resume.
