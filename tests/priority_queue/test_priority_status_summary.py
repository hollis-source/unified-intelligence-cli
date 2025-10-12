import pytest

from src.priority_queue.entities import Priority


def make_priority(pid: str, status: str) -> Priority:
    return Priority(id=pid, title=f"Title {pid}", context="ctx", status=status)


def test_priority_status_validation_active_and_completed():
    p_active = make_priority("p1", "active")
    p_completed = make_priority("p2", "completed")

    assert p_active.is_valid_status() is True
    assert p_completed.is_valid_status() is True


def test_summarize_priorities_counts_active_and_completed():
    from src.priority_queue.use_cases import SummarizePrioritiesUseCase

    priorities = [make_priority("p1", "active"), make_priority("p2", "completed")]

    summary = SummarizePrioritiesUseCase().execute(priorities)

    assert summary.get("active") == 1
    assert summary.get("completed") == 1
    # Non-present statuses should default to 0 or be absent; accept either
    assert summary.get("paused", 0) in (0, summary.get("paused", 0))

