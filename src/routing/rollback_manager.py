"""
Rollback Manager for ATADO Routing Weights

Provides one-click rollback capability with audit trail for routing weight changes.
Stores snapshots before changes and enables safe reversion.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class WeightSnapshot:
    """Snapshot of routing weights at a point in time."""
    snapshot_id: str
    timestamp: str
    weights: Dict[str, float]
    reason: str
    user: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RollbackEntry:
    """Audit log entry for a rollback operation."""
    rollback_id: str
    timestamp: str
    from_snapshot_id: str
    to_snapshot_id: str
    user: str
    reason: str
    success: bool
    error: Optional[str] = None


class RollbackManager:
    """
    Manages routing weight snapshots and rollback operations.
    
    Features:
    - Store snapshots before weight changes
    - One-click rollback to previous snapshot
    - Audit trail of all changes and rollbacks
    - Configurable retention policy
    """
    
    def __init__(self, storage_dir: str = "data/rollback"):
        """
        Initialize rollback manager.
        
        Args:
            storage_dir: Directory for storing snapshots and audit logs
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.snapshots_file = self.storage_dir / "snapshots.json"
        self.audit_log_file = self.storage_dir / "audit_log.json"
        
        # Load existing data
        self.snapshots: List[WeightSnapshot] = self._load_snapshots()
        self.audit_log: List[RollbackEntry] = self._load_audit_log()
    
    def _load_snapshots(self) -> List[WeightSnapshot]:
        """Load snapshots from disk."""
        if not self.snapshots_file.exists():
            return []
        try:
            data = json.load(open(self.snapshots_file))
            return [WeightSnapshot(**s) for s in data]
        except Exception:
            return []
    
    def _load_audit_log(self) -> List[RollbackEntry]:
        """Load audit log from disk."""
        if not self.audit_log_file.exists():
            return []
        try:
            data = json.load(open(self.audit_log_file))
            return [RollbackEntry(**e) for e in data]
        except Exception:
            return []
    
    def _save_snapshots(self) -> None:
        """Save snapshots to disk."""
        data = [s.__dict__ for s in self.snapshots]
        with open(self.snapshots_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _save_audit_log(self) -> None:
        """Save audit log to disk."""
        data = [e.__dict__ for e in self.audit_log]
        with open(self.audit_log_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_snapshot(
        self,
        weights: Dict[str, float],
        reason: str,
        user: str = "system",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a snapshot of current weights.
        
        Args:
            weights: Current routing weights
            reason: Reason for snapshot (e.g., "pre-promotion", "manual-backup")
            user: User or system creating snapshot
            metadata: Additional metadata (e.g., promotion proposal details)
            
        Returns:
            Snapshot ID
        """
        snapshot_id = f"snapshot_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        timestamp = datetime.now(UTC).isoformat()
        
        snapshot = WeightSnapshot(
            snapshot_id=snapshot_id,
            timestamp=timestamp,
            weights=weights.copy(),
            reason=reason,
            user=user,
            metadata=metadata or {}
        )
        
        self.snapshots.append(snapshot)
        self._save_snapshots()
        
        return snapshot_id
    
    def get_snapshot(self, snapshot_id: str) -> Optional[WeightSnapshot]:
        """Get snapshot by ID."""
        for snapshot in self.snapshots:
            if snapshot.snapshot_id == snapshot_id:
                return snapshot
        return None
    
    def get_latest_snapshot(self) -> Optional[WeightSnapshot]:
        """Get most recent snapshot."""
        if not self.snapshots:
            return None
        return self.snapshots[-1]
    
    def list_snapshots(self, limit: int = 10) -> List[WeightSnapshot]:
        """List recent snapshots."""
        return self.snapshots[-limit:]
    
    def rollback(
        self,
        to_snapshot_id: str,
        reason: str,
        user: str = "system"
    ) -> Dict[str, Any]:
        """
        Rollback to a previous snapshot.
        
        Args:
            to_snapshot_id: Snapshot ID to rollback to
            reason: Reason for rollback
            user: User performing rollback
            
        Returns:
            Dict with rollback result and weights to apply
        """
        # Get target snapshot
        target = self.get_snapshot(to_snapshot_id)
        if not target:
            return {
                "success": False,
                "error": f"Snapshot {to_snapshot_id} not found",
                "weights": None
            }
        
        # Get current snapshot (if exists)
        current = self.get_latest_snapshot()
        from_snapshot_id = current.snapshot_id if current else "none"
        
        # Create rollback entry
        rollback_id = f"rollback_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        timestamp = datetime.now(UTC).isoformat()
        
        entry = RollbackEntry(
            rollback_id=rollback_id,
            timestamp=timestamp,
            from_snapshot_id=from_snapshot_id,
            to_snapshot_id=to_snapshot_id,
            user=user,
            reason=reason,
            success=True
        )
        
        self.audit_log.append(entry)
        self._save_audit_log()
        
        return {
            "success": True,
            "rollback_id": rollback_id,
            "weights": target.weights.copy(),
            "from_snapshot": from_snapshot_id,
            "to_snapshot": to_snapshot_id
        }
    
    def get_audit_log(self, limit: int = 20) -> List[RollbackEntry]:
        """Get recent audit log entries."""
        return self.audit_log[-limit:]
    
    def cleanup_old_snapshots(self, keep_count: int = 50) -> int:
        """
        Remove old snapshots, keeping only the most recent.
        
        Args:
            keep_count: Number of snapshots to keep
            
        Returns:
            Number of snapshots removed
        """
        if len(self.snapshots) <= keep_count:
            return 0
        
        removed = len(self.snapshots) - keep_count
        self.snapshots = self.snapshots[-keep_count:]
        self._save_snapshots()
        
        return removed

