"""Comprehensive tests for priority_queue entities

Tests cover missing coverage lines in:
- Priority entity: is_valid_status, to_dict, from_dict methods
- Task entity: check_staleness method
- Edge cases and error conditions

Improves coverage for src/priority_queue/entities.py
"""

import pytest
import hashlib
from src.priority_queue.entities import Priority, Task, Metrics


class TestPriorityEntity:
    """Test suite for Priority entity"""

    def test_priority_creation_basic(self):
        """Test basic Priority entity creation"""
        priority = Priority(
            id="test-priority",
            title="Test Priority",
            context="Test context for priority",
            status="active"
        )
        
        assert priority.id == "test-priority"
        assert priority.title == "Test Priority"
        assert priority.context == "Test context for priority"
        assert priority.status == "active"
        
        # Check context_hash is auto-computed
        expected_hash = hashlib.sha256("Test context for priority".encode()).hexdigest()
        assert priority.context_hash == expected_hash

    def test_priority_context_hash_auto_computation(self):
        """Test context_hash is automatically computed from context"""
        context = "Specific context string"
        priority = Priority(
            id="test",
            title="Test",
            context=context,
            status="active"
        )
        
        expected_hash = hashlib.sha256(context.encode()).hexdigest()
        assert priority.context_hash == expected_hash

    def test_priority_is_valid_status_valid_statuses(self):
        """Test is_valid_status returns True for valid statuses"""
        valid_statuses = ["active", "paused", "abandoned", "completed"]
        
        for status in valid_statuses:
            priority = Priority(
                id="test",
                title="Test",
                context="Test context",
                status=status
            )
            assert priority.is_valid_status() is True

    def test_priority_is_valid_status_invalid_statuses(self):
        """Test is_valid_status returns False for invalid statuses"""
        invalid_statuses = ["open", "failed", "in_progress", "unknown", "", "ACTIVE"]
        
        for status in invalid_statuses:
            priority = Priority(
                id="test",
                title="Test",
                context="Test context",
                status=status
            )
            assert priority.is_valid_status() is False

    def test_priority_to_dict(self):
        """Test Priority.to_dict() serialization"""
        priority = Priority(
            id="priority-123",
            title="Test Priority Title",
            context="Complex context with special chars: !@#$%",
            status="paused"
        )
        
        result = priority.to_dict()
        
        expected = {
            'id': "priority-123",
            'title': "Test Priority Title",
            'context': "Complex context with special chars: !@#$%",
            'status': "paused",
            'context_hash': priority.context_hash
        }
        
        assert result == expected
        assert isinstance(result, dict)

    def test_priority_from_dict_basic(self):
        """Test Priority.from_dict() deserialization"""
        data = {
            'id': "from-dict-test",
            'title': "From Dict Title",
            'context': "From dict context",
            'status': "completed"
        }
        
        priority = Priority.from_dict(data)
        
        assert priority.id == "from-dict-test"
        assert priority.title == "From Dict Title"
        assert priority.context == "From dict context"
        assert priority.status == "completed"
        
        # Context hash should be computed
        expected_hash = hashlib.sha256("From dict context".encode()).hexdigest()
        assert priority.context_hash == expected_hash

    def test_priority_from_dict_with_preserved_hash(self):
        """Test Priority.from_dict() preserves existing context_hash"""
        preserved_hash = "custom_hash_value_123"
        data = {
            'id': "hash-test",
            'title': "Hash Test",
            'context': "Test context",
            'status': "active",
            'context_hash': preserved_hash
        }
        
        priority = Priority.from_dict(data)
        
        # Should preserve the provided hash, not compute new one
        assert priority.context_hash == preserved_hash

    def test_priority_roundtrip_serialization(self):
        """Test Priority to_dict -> from_dict roundtrip"""
        original = Priority(
            id="roundtrip-test",
            title="Roundtrip Test",
            context="Roundtrip context",
            status="abandoned"
        )
        
        # Serialize and deserialize
        data = original.to_dict()
        restored = Priority.from_dict(data)
        
        # Should be identical
        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.context == original.context
        assert restored.status == original.status
        assert restored.context_hash == original.context_hash


class TestTaskEntityStaleness:
    """Test suite for Task entity staleness checking"""

    def test_task_check_staleness_no_parent_tracking(self):
        """Test check_staleness returns False when no parent tracking"""
        task = Task(
            id="no-parent-task",
            priority=1,
            status="open",
            metadata={},
            parent_priority_id=None,
            parent_context_hash=None
        )
        
        priority = Priority(
            id="some-priority",
            title="Test",
            context="Test context",
            status="active"
        )
        
        # Should return False (not stale) when no parent tracking
        assert task.check_staleness(priority) is False

    def test_task_check_staleness_parent_id_none(self):
        """Test check_staleness returns False when parent_priority_id is None"""
        task = Task(
            id="task-1",
            priority=1,
            status="open",
            metadata={},
            parent_priority_id=None,
            parent_context_hash="some_hash"
        )
        
        priority = Priority(
            id="priority-1",
            title="Test",
            context="Test context",
            status="active"
        )
        
        assert task.check_staleness(priority) is False

    def test_task_check_staleness_parent_hash_none(self):
        """Test check_staleness returns False when parent_context_hash is None"""
        task = Task(
            id="task-1",
            priority=1,
            status="open",
            metadata={},
            parent_priority_id="priority-1",
            parent_context_hash=None
        )
        
        priority = Priority(
            id="priority-1",
            title="Test",
            context="Test context",
            status="active"
        )
        
        assert task.check_staleness(priority) is False

    def test_task_check_staleness_priority_id_mismatch(self):
        """Test check_staleness raises ValueError for priority ID mismatch"""
        task = Task(
            id="task-1",
            priority=1,
            status="open",
            metadata={},
            parent_priority_id="priority-1",
            parent_context_hash="some_hash"
        )
        
        priority = Priority(
            id="different-priority",
            title="Test",
            context="Test context",
            status="active"
        )
        
        with pytest.raises(ValueError, match="Priority ID mismatch"):
            task.check_staleness(priority)

    def test_task_check_staleness_not_stale(self):
        """Test check_staleness returns False when context hashes match"""
        priority = Priority(
            id="priority-1",
            title="Test Priority",
            context="Current context",
            status="active"
        )
        
        task = Task(
            id="task-1",
            priority=1,
            status="open",
            metadata={},
            parent_priority_id="priority-1",
            parent_context_hash=priority.context_hash  # Same hash
        )
        
        assert task.check_staleness(priority) is False

    def test_task_check_staleness_is_stale(self):
        """Test check_staleness returns True when context hashes differ"""
        priority = Priority(
            id="priority-1",
            title="Test Priority",
            context="Updated context",
            status="active"
        )
        
        # Task has old context hash
        old_hash = hashlib.sha256("Old context".encode()).hexdigest()
        task = Task(
            id="task-1",
            priority=1,
            status="open",
            metadata={},
            parent_priority_id="priority-1",
            parent_context_hash=old_hash
        )
        
        # Should be stale since hashes differ
        assert task.check_staleness(priority) is True

    def test_task_check_staleness_context_change_scenario(self):
        """Test realistic scenario where priority context changes"""
        # Original priority and task
        original_priority = Priority(
            id="feature-123",
            title="Feature Development",
            context="Implement user authentication",
            status="active"
        )
        
        task = Task(
            id="task-auth-1",
            priority=3,
            status="open",
            metadata={"title": "Create login form"},
            parent_priority_id="feature-123",
            parent_context_hash=original_priority.context_hash
        )
        
        # Task should not be stale initially
        assert task.check_staleness(original_priority) is False
        
        # Priority context changes
        updated_priority = Priority(
            id="feature-123",
            title="Feature Development",
            context="Implement OAuth authentication instead",  # Changed context
            status="active"
        )
        
        # Task should now be stale
        assert task.check_staleness(updated_priority) is True


class TestMetricsEntityValidation:
    """Test suite for Metrics entity validation edge cases"""

    def test_metrics_success_rate_boundary_values(self):
        """Test success_rate validation at boundary values"""
        # Test exact boundaries
        metrics_0 = Metrics(throughput=1.0, latency=1.0, success_rate=0.0)
        assert metrics_0.is_valid_success_rate() is True
        
        metrics_1 = Metrics(throughput=1.0, latency=1.0, success_rate=1.0)
        assert metrics_1.is_valid_success_rate() is True
        
        # Test just outside boundaries
        metrics_negative = Metrics(throughput=1.0, latency=1.0, success_rate=-0.001)
        assert metrics_negative.is_valid_success_rate() is False
        
        metrics_over_one = Metrics(throughput=1.0, latency=1.0, success_rate=1.001)
        assert metrics_over_one.is_valid_success_rate() is False

    def test_metrics_success_rate_extreme_values(self):
        """Test success_rate validation with extreme values"""
        extreme_values = [-1000.0, -1.0, 2.0, 100.0, float('inf'), float('-inf')]
        
        for value in extreme_values:
            metrics = Metrics(throughput=1.0, latency=1.0, success_rate=value)
            assert metrics.is_valid_success_rate() is False

    def test_metrics_success_rate_valid_range(self):
        """Test success_rate validation within valid range"""
        valid_values = [0.0, 0.25, 0.5, 0.75, 0.99, 1.0]
        
        for value in valid_values:
            metrics = Metrics(throughput=1.0, latency=1.0, success_rate=value)
            assert metrics.is_valid_success_rate() is True
