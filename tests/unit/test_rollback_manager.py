import tempfile
from pathlib import Path

from src.routing.rollback_manager import RollbackManager


def test_create_and_get_snapshot():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = RollbackManager(storage_dir=tmpdir)
        
        weights = {"backend": 1.0, "frontend": 0.9}
        snapshot_id = manager.create_snapshot(
            weights=weights,
            reason="test-snapshot",
            user="test-user"
        )
        
        assert snapshot_id.startswith("snapshot_")
        
        snapshot = manager.get_snapshot(snapshot_id)
        assert snapshot is not None
        assert snapshot.weights == weights
        assert snapshot.reason == "test-snapshot"
        assert snapshot.user == "test-user"


def test_rollback_to_previous_snapshot():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = RollbackManager(storage_dir=tmpdir)
        
        # Create initial snapshot
        weights_v1 = {"backend": 1.0, "frontend": 0.9}
        snapshot_v1 = manager.create_snapshot(weights_v1, "v1", "user1")
        
        # Create second snapshot
        weights_v2 = {"backend": 1.1, "frontend": 0.95}
        snapshot_v2 = manager.create_snapshot(weights_v2, "v2", "user1")
        
        # Rollback to v1
        result = manager.rollback(snapshot_v1, "revert-to-v1", "user2")
        
        assert result["success"] is True
        assert result["weights"] == weights_v1
        assert result["to_snapshot"] == snapshot_v1
        
        # Check audit log
        audit = manager.get_audit_log()
        assert len(audit) == 1
        assert audit[0].to_snapshot_id == snapshot_v1
        assert audit[0].reason == "revert-to-v1"


def test_cleanup_old_snapshots():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = RollbackManager(storage_dir=tmpdir)
        
        # Create 10 snapshots
        for i in range(10):
            manager.create_snapshot({"weight": float(i)}, f"snapshot-{i}", "user")
        
        assert len(manager.snapshots) == 10
        
        # Cleanup, keep only 5
        removed = manager.cleanup_old_snapshots(keep_count=5)
        
        assert removed == 5
        assert len(manager.snapshots) == 5
        assert manager.snapshots[0].reason == "snapshot-5"  # oldest kept

