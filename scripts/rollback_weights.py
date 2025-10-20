#!/usr/bin/env python3
"""
Rollback Routing Weights CLI

Provides one-click rollback capability for routing weight changes.

Usage:
    # List recent snapshots
    python scripts/rollback_weights.py --list
    
    # Rollback to specific snapshot
    python scripts/rollback_weights.py --rollback snapshot_20251019_120000 --reason "Revert regression"
    
    # View audit log
    python scripts/rollback_weights.py --audit
    
    # Create manual snapshot
    python scripts/rollback_weights.py --snapshot --reason "Pre-deployment backup"
"""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.routing.rollback_manager import RollbackManager


def load_current_weights(weights_file: str = "data/routing_weights.json") -> dict:
    """Load current routing weights from file."""
    weights_path = Path(weights_file)
    if not weights_path.exists():
        return {}
    
    with open(weights_path) as f:
        return json.load(f)


def save_weights(weights: dict, weights_file: str = "data/routing_weights.json") -> None:
    """Save routing weights to file."""
    weights_path = Path(weights_file)
    weights_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(weights_path, 'w') as f:
        json.dump(weights, f, indent=2)


def list_snapshots(manager: RollbackManager, limit: int = 10) -> None:
    """List recent snapshots."""
    snapshots = manager.list_snapshots(limit=limit)
    
    if not snapshots:
        print("No snapshots found.")
        return
    
    print(f"\n{'Snapshot ID':<30} {'Timestamp':<25} {'Reason':<30} {'User':<15}")
    print("-" * 100)
    
    for snapshot in reversed(snapshots):  # Most recent first
        print(f"{snapshot.snapshot_id:<30} {snapshot.timestamp:<25} {snapshot.reason:<30} {snapshot.user:<15}")
    
    print(f"\nTotal: {len(snapshots)} snapshots")


def show_snapshot_details(manager: RollbackManager, snapshot_id: str) -> None:
    """Show detailed information about a snapshot."""
    snapshot = manager.get_snapshot(snapshot_id)
    
    if not snapshot:
        print(f"Snapshot '{snapshot_id}' not found.")
        return
    
    print(f"\nSnapshot: {snapshot.snapshot_id}")
    print(f"Timestamp: {snapshot.timestamp}")
    print(f"Reason: {snapshot.reason}")
    print(f"User: {snapshot.user}")
    print(f"\nWeights:")
    for key, value in sorted(snapshot.weights.items()):
        print(f"  {key}: {value}")
    
    if snapshot.metadata:
        print(f"\nMetadata:")
        for key, value in snapshot.metadata.items():
            print(f"  {key}: {value}")


def rollback_to_snapshot(
    manager: RollbackManager,
    snapshot_id: str,
    reason: str,
    user: str = "cli",
    weights_file: str = "data/routing_weights.json"
) -> None:
    """Rollback to a specific snapshot."""
    # Perform rollback
    result = manager.rollback(snapshot_id, reason=reason, user=user)
    
    if not result["success"]:
        print(f"❌ Rollback failed: {result['error']}")
        return
    
    # Save weights to file
    save_weights(result["weights"], weights_file)
    
    print(f"✅ Rollback successful!")
    print(f"   Rollback ID: {result['rollback_id']}")
    print(f"   From: {result['from_snapshot']}")
    print(f"   To: {result['to_snapshot']}")
    print(f"   Weights saved to: {weights_file}")


def create_snapshot(
    manager: RollbackManager,
    reason: str,
    user: str = "cli",
    weights_file: str = "data/routing_weights.json"
) -> None:
    """Create a manual snapshot of current weights."""
    weights = load_current_weights(weights_file)
    
    if not weights:
        print(f"⚠️  No weights found in {weights_file}")
        return
    
    snapshot_id = manager.create_snapshot(weights, reason=reason, user=user)
    
    print(f"✅ Snapshot created: {snapshot_id}")
    print(f"   Reason: {reason}")
    print(f"   User: {user}")
    print(f"   Weights: {len(weights)} entries")


def show_audit_log(manager: RollbackManager, limit: int = 20) -> None:
    """Show audit log of rollback operations."""
    entries = manager.get_audit_log(limit=limit)
    
    if not entries:
        print("No audit log entries found.")
        return
    
    print(f"\n{'Rollback ID':<35} {'Timestamp':<25} {'From':<30} {'To':<30} {'User':<15}")
    print("-" * 135)
    
    for entry in reversed(entries):  # Most recent first
        status = "✅" if entry.success else "❌"
        print(f"{status} {entry.rollback_id:<33} {entry.timestamp:<25} {entry.from_snapshot_id:<30} {entry.to_snapshot_id:<30} {entry.user:<15}")
        if entry.reason:
            print(f"   Reason: {entry.reason}")
        if entry.error:
            print(f"   Error: {entry.error}")
    
    print(f"\nTotal: {len(entries)} rollback operations")


def main():
    parser = argparse.ArgumentParser(
        description="Rollback routing weights to previous snapshots",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List recent snapshots"
    )
    
    parser.add_argument(
        "--details",
        metavar="SNAPSHOT_ID",
        help="Show detailed information about a snapshot"
    )
    
    parser.add_argument(
        "--rollback",
        metavar="SNAPSHOT_ID",
        help="Rollback to specified snapshot"
    )
    
    parser.add_argument(
        "--snapshot",
        action="store_true",
        help="Create a manual snapshot of current weights"
    )
    
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Show audit log of rollback operations"
    )
    
    parser.add_argument(
        "--reason",
        default="Manual operation",
        help="Reason for rollback or snapshot"
    )
    
    parser.add_argument(
        "--user",
        default="cli",
        help="User performing the operation"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of entries to show (default: 10)"
    )
    
    parser.add_argument(
        "--storage-dir",
        default="data/rollback",
        help="Directory for rollback storage (default: data/rollback)"
    )
    
    parser.add_argument(
        "--weights-file",
        default="data/routing_weights.json",
        help="Routing weights file (default: data/routing_weights.json)"
    )
    
    args = parser.parse_args()
    
    # Initialize rollback manager
    manager = RollbackManager(storage_dir=args.storage_dir)
    
    # Execute command
    if args.list:
        list_snapshots(manager, limit=args.limit)
    
    elif args.details:
        show_snapshot_details(manager, args.details)
    
    elif args.rollback:
        rollback_to_snapshot(
            manager,
            args.rollback,
            reason=args.reason,
            user=args.user,
            weights_file=args.weights_file
        )
    
    elif args.snapshot:
        create_snapshot(
            manager,
            reason=args.reason,
            user=args.user,
            weights_file=args.weights_file
        )
    
    elif args.audit:
        show_audit_log(manager, limit=args.limit)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

