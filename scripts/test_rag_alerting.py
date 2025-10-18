#!/usr/bin/env python3
"""Test RAG alerting system.

This script tests the RAG alerting functionality.
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.monitoring.rag_alerting import RAGAlerting, Alert, AlertSeverity, console_alert_handler, log_alert_handler
from src.adapters.rag.surrealdb_store import SurrealDBStore
from src.adapters.llm.rag_config import RAGConfig


async def test_rag_alerting():
    """Test RAG alerting system."""
    
    print("=" * 80)
    print("RAG ALERTING SYSTEM TEST")
    print("=" * 80)
    print()
    
    # Setup
    config = RAGConfig()
    db_url = os.getenv("SURREALDB_URL", "ws://localhost:8000")
    
    print("Connecting to SurrealDB...")
    store = SurrealDBStore(
        url=db_url,
        namespace=config.db_namespace,
        database=config.db_database,
        user=config.db_user,
        password=config.db_password
    )
    
    try:
        await store.connect()
        print("✅ Connected to SurrealDB")
        print()
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return False
    
    # Create alerting system
    alerting = RAGAlerting(
        db_store=store,
        accuracy_threshold=70.0,
        latency_threshold_ms=1000.0,
        drift_threshold=0.3,
        min_patterns=50
    )
    
    # Add alert handlers
    alerting.add_alert_handler(console_alert_handler)
    
    # Test 1: Check database connection
    print("TEST 1: Check Database Connection")
    print("-" * 80)
    
    try:
        alerts = await alerting.check_database_connection()
        
        if alerts:
            print(f"⚠️  {len(alerts)} alert(s) generated:")
            for alert in alerts:
                print(f"   {alert}")
        else:
            print("✅ No database connection issues")
        
        print()
        
    except Exception as e:
        print(f"❌ Database connection check failed: {e}")
        return False
    
    # Test 2: Check accuracy
    print("TEST 2: Check Routing Accuracy")
    print("-" * 80)
    
    try:
        alerts = await alerting.check_accuracy()
        
        if alerts:
            print(f"⚠️  {len(alerts)} alert(s) generated:")
            for alert in alerts:
                print(f"   {alert}")
                print(f"   Details: {alert.details}")
        else:
            print("✅ Routing accuracy is acceptable")
        
        print()
        
    except Exception as e:
        print(f"❌ Accuracy check failed: {e}")
        return False
    
    # Test 3: Check pattern count
    print("TEST 3: Check Pattern Count")
    print("-" * 80)
    
    try:
        alerts = await alerting.check_pattern_count()
        
        if alerts:
            print(f"⚠️  {len(alerts)} alert(s) generated:")
            for alert in alerts:
                print(f"   {alert}")
                print(f"   Details: {alert.details}")
        else:
            print("✅ Pattern count is sufficient")
        
        print()
        
    except Exception as e:
        print(f"❌ Pattern count check failed: {e}")
        return False
    
    # Test 4: Check drift
    print("TEST 4: Check Pattern Drift")
    print("-" * 80)
    
    try:
        alerts = await alerting.check_drift()
        
        if alerts:
            print(f"⚠️  {len(alerts)} alert(s) generated:")
            for alert in alerts:
                print(f"   {alert}")
                print(f"   Details: {alert.details}")
        else:
            print("✅ No pattern drift detected")
        
        print()
        
    except Exception as e:
        print(f"❌ Drift check failed: {e}")
        return False
    
    # Test 5: Run all checks
    print("TEST 5: Run All Checks")
    print("-" * 80)
    
    try:
        results = await alerting.run_all_checks()
        
        print("Check results:")
        for check_name, check_alerts in results.items():
            status = "✅ OK" if not check_alerts else f"⚠️  {len(check_alerts)} alert(s)"
            print(f"  • {check_name}: {status}")
        
        print()
        
    except Exception as e:
        print(f"❌ All checks failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 6: Get alert summary
    print("TEST 6: Get Alert Summary")
    print("-" * 80)
    
    try:
        summary = await alerting.get_alert_summary()
        
        print(f"Total alerts: {summary['total_alerts']}")
        print(f"By severity:")
        for severity, count in summary['by_severity'].items():
            if count > 0:
                print(f"  • {severity}: {count}")
        
        print()
        
        if summary['alerts']:
            print("Alerts:")
            for alert_dict in summary['alerts']:
                print(f"  • [{alert_dict['severity'].upper()}] {alert_dict['alert_type']}: {alert_dict['message']}")
        
        print()
        
    except Exception as e:
        print(f"❌ Alert summary failed: {e}")
        return False
    
    # Test 7: Test alert handlers
    print("TEST 7: Test Alert Handlers")
    print("-" * 80)
    
    try:
        # Create a test alert
        test_alert = Alert(
            alert_type="test_alert",
            severity=AlertSeverity.INFO,
            message="This is a test alert",
            details={"test": True}
        )
        
        print("Emitting test alert...")
        await alerting._emit_alert(test_alert)
        
        print("✅ Alert handlers working")
        print()
        
    except Exception as e:
        print(f"❌ Alert handler test failed: {e}")
        return False
    
    await store.close()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("✅ Database connection check: PASS")
    print("✅ Accuracy check: PASS")
    print("✅ Pattern count check: PASS")
    print("✅ Drift check: PASS")
    print("✅ Run all checks: PASS")
    print("✅ Alert summary: PASS")
    print("✅ Alert handlers: PASS")
    print()
    print("🎉 RAG ALERTING SYSTEM TEST PASSED!")
    print()
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_rag_alerting())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

