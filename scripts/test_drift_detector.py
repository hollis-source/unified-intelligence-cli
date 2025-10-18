#!/usr/bin/env python3
"""Test drift detector for pattern distribution monitoring.

This script tests the drift detection functionality.
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.routing.drift_detector import DriftDetector
from src.adapters.rag.surrealdb_store import SurrealDBStore
from src.adapters.llm.rag_config import RAGConfig


async def test_drift_detector():
    """Test drift detector."""
    
    print("=" * 80)
    print("DRIFT DETECTOR TEST")
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
    
    # Create drift detector
    detector = DriftDetector(
        db_store=store,
        drift_threshold=0.3,
        window_size=50,
        min_samples=5  # Lower for testing
    )
    
    # Test 1: Get task distribution
    print("TEST 1: Get Task Distribution")
    print("-" * 80)
    
    try:
        distribution = await detector.get_task_distribution(limit=100)
        
        print("Task distribution:")
        total = sum(distribution.values())
        for domain, count in sorted(distribution.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            print(f"  • {domain}: {count} ({percentage:.1f}%)")
        print()
        print(f"Total tasks: {total}")
        print()
        
        if total > 0:
            print("✅ Task distribution retrieved")
        else:
            print("⚠️  No tasks found in database")
            print("   Run tasks to generate distribution data")
        
        print()
        
    except Exception as e:
        print(f"❌ Failed to get distribution: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Detect drift
    print("TEST 2: Detect Drift")
    print("-" * 80)
    
    try:
        drift_result = await detector.detect_drift()
        
        print(f"Drift detected: {drift_result.get('drift_detected', False)}")
        
        if drift_result.get('reason') == 'insufficient_data':
            print(f"⚠️  {drift_result.get('message')}")
            print(f"   Current samples: {drift_result.get('current_samples', 0)}")
            print(f"   Min samples: {drift_result.get('min_samples', 0)}")
        else:
            print(f"Drift score: {drift_result.get('drift_score', 0):.2f}")
            print(f"Similarity: {drift_result.get('similarity', 0):.2f}")
            print(f"Threshold: {drift_result.get('threshold', 0):.2f}")
            print(f"Recommendation: {drift_result.get('recommendation', 'N/A')}")
            print()
            
            if drift_result.get('significant_changes'):
                print("Significant changes:")
                for change in drift_result['significant_changes']:
                    print(f"  • {change['domain']}:")
                    print(f"    Current: {change['current_percentage']:.1f}%")
                    print(f"    Baseline: {change['baseline_percentage']:.1f}%")
                    print(f"    Change: {change['change']:+.1f}%")
                print()
        
        print("✅ Drift detection complete")
        print()
        
    except Exception as e:
        print(f"❌ Drift detection failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Monitor domain shifts
    print("TEST 3: Monitor Domain Shifts")
    print("-" * 80)
    
    try:
        shift_result = await detector.monitor_domain_shifts()
        
        print(f"Shift detected: {shift_result.get('shift_detected', False)}")
        
        if shift_result.get('reason') == 'insufficient_data':
            print(f"⚠️  {shift_result.get('message')}")
        else:
            if shift_result.get('shifts'):
                print("Domain shifts:")
                for shift in shift_result['shifts']:
                    print(f"  • {shift['domain']}:")
                    print(f"    Recent: {shift['recent_percentage']:.1f}%")
                    print(f"    Older: {shift['older_percentage']:.1f}%")
                    print(f"    Shift: {shift['shift']:+.1f}% ({shift['trend']})")
                print()
            else:
                print("No significant domain shifts detected")
                print()
        
        print("✅ Domain shift monitoring complete")
        print()
        
    except Exception as e:
        print(f"❌ Domain shift monitoring failed: {e}")
        return False
    
    # Test 4: Check pattern staleness
    print("TEST 4: Check Pattern Staleness")
    print("-" * 80)
    
    try:
        staleness_result = await detector.check_pattern_staleness()
        
        print(f"Total patterns: {staleness_result.get('total_patterns', 0)}")
        print(f"Recommendation: {staleness_result.get('recommendation', 'N/A')}")
        print()
        
        print("✅ Pattern staleness check complete")
        print()
        
    except Exception as e:
        print(f"❌ Pattern staleness check failed: {e}")
        return False
    
    # Test 5: Generate drift report
    print("TEST 5: Generate Drift Report")
    print("-" * 80)
    
    try:
        report = await detector.get_drift_report()
        
        print("DRIFT REPORT:")
        print()
        
        print("1. Drift Detection:")
        drift = report['drift_detection']
        if drift.get('reason') == 'insufficient_data':
            print(f"   ⚠️  {drift.get('message')}")
        else:
            print(f"   Drift detected: {drift.get('drift_detected', False)}")
            print(f"   Drift score: {drift.get('drift_score', 0):.2f}")
        print()
        
        print("2. Domain Shifts:")
        shifts = report['domain_shifts']
        if shifts.get('reason') == 'insufficient_data':
            print(f"   ⚠️  {shifts.get('message')}")
        else:
            print(f"   Shifts detected: {shifts.get('shift_detected', False)}")
            print(f"   Number of shifts: {len(shifts.get('shifts', []))}")
        print()
        
        print("3. Pattern Staleness:")
        staleness = report['pattern_staleness']
        print(f"   Total patterns: {staleness.get('total_patterns', 0)}")
        print()
        
        print("OVERALL:")
        print(f"   Needs re-embedding: {report.get('needs_reembedding', False)}")
        print(f"   Recommendation: {report.get('overall_recommendation', 'N/A')}")
        print()
        
        print("✅ Drift report generated")
        print()
        
    except Exception as e:
        print(f"❌ Drift report generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    await store.close()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("✅ Task distribution: PASS")
    print("✅ Drift detection: PASS")
    print("✅ Domain shift monitoring: PASS")
    print("✅ Pattern staleness check: PASS")
    print("✅ Drift report generation: PASS")
    print()
    print("🎉 DRIFT DETECTOR TEST PASSED!")
    print()
    
    if total == 0:
        print("NOTE: No tasks in database")
        print("      Run tasks to test drift detection with real data")
        print()
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_drift_detector())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

