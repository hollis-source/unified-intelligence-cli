#!/usr/bin/env python3
"""Test performance feedback loop.

This script tests the performance feedback functionality.
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.routing.performance_feedback import PerformanceFeedback
from src.adapters.rag.surrealdb_store import SurrealDBStore
from src.adapters.llm.rag_config import RAGConfig


async def test_performance_feedback():
    """Test performance feedback loop."""
    
    print("=" * 80)
    print("PERFORMANCE FEEDBACK LOOP TEST")
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
    
    # Create feedback loop
    feedback = PerformanceFeedback(db_store=store, update_interval=5)
    
    # Test 1: Record task executions
    print("TEST 1: Record Task Executions")
    print("-" * 80)
    
    try:
        # Simulate some task executions
        test_agents = [
            ("backend-lead", True, 500.0),
            ("backend-lead", True, 450.0),
            ("backend-lead", False, 600.0),
            ("frontend-lead", True, 400.0),
            ("frontend-lead", True, 420.0),
            ("qa-engineer", True, 300.0),
            ("qa-engineer", True, 320.0),
            ("qa-engineer", True, 310.0),
        ]
        
        print(f"Recording {len(test_agents)} task executions...")
        for agent, success, latency in test_agents:
            await feedback.record_task_execution(agent, success, latency)
            print(f"  • {agent}: {'✅' if success else '❌'} ({latency:.0f}ms)")
        
        print()
        print("✅ Task executions recorded")
        print()
        
    except Exception as e:
        print(f"❌ Failed to record executions: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Update performance metrics
    print("TEST 2: Update Performance Metrics")
    print("-" * 80)
    
    try:
        await feedback.update_performance_metrics()
        
        print("✅ Performance metrics updated")
        print()
        
    except Exception as e:
        print(f"❌ Failed to update metrics: {e}")
        return False
    
    # Test 3: Get agent performance
    print("TEST 3: Get Agent Performance")
    print("-" * 80)
    
    try:
        performance = await feedback.get_agent_performance("backend-lead")
        
        if performance:
            print("Backend Lead Performance:")
            print(f"  • Total tasks: {performance.get('total_tasks', 0)}")
            print(f"  • Successful: {performance.get('successful_tasks', 0)}")
            print(f"  • Failed: {performance.get('failed_tasks', 0)}")
            print(f"  • Success rate: {performance.get('success_rate', 0):.1f}%")
            print(f"  • Avg latency: {performance.get('avg_latency_ms', 0):.0f}ms")
            print()
        else:
            print("⚠️  No performance data found")
            print()
        
        print("✅ Agent performance retrieved")
        print()
        
    except Exception as e:
        print(f"❌ Failed to get performance: {e}")
        return False
    
    # Test 4: Get all agent performance
    print("TEST 4: Get All Agent Performance")
    print("-" * 80)
    
    try:
        all_performance = await feedback.get_all_agent_performance()
        
        print(f"Total agents with performance data: {len(all_performance)}")
        print()
        
        if all_performance:
            print("Agent Performance Summary:")
            for perf in all_performance[:5]:
                print(f"  • {perf.get('agent_role', 'unknown')}:")
                print(f"    Success rate: {perf.get('success_rate', 0):.1f}%")
                print(f"    Total tasks: {perf.get('total_tasks', 0)}")
            print()
        
        print("✅ All agent performance retrieved")
        print()
        
    except Exception as e:
        print(f"❌ Failed to get all performance: {e}")
        return False
    
    # Test 5: Get top performers
    print("TEST 5: Get Top Performers")
    print("-" * 80)
    
    try:
        top_performers = await feedback.get_top_performers(limit=3)
        
        if top_performers:
            print("Top Performers:")
            for i, perf in enumerate(top_performers, 1):
                print(f"  {i}. {perf.get('agent_role', 'unknown')}")
                print(f"     Success rate: {perf.get('success_rate', 0):.1f}%")
                print(f"     Total tasks: {perf.get('total_tasks', 0)}")
            print()
        else:
            print("⚠️  No performance data available")
            print()
        
        print("✅ Top performers identified")
        print()
        
    except Exception as e:
        print(f"❌ Failed to get top performers: {e}")
        return False
    
    # Test 6: Calculate performance score
    print("TEST 6: Calculate Performance Score")
    print("-" * 80)
    
    try:
        score = await feedback.calculate_performance_score("qa-engineer")
        
        print(f"QA Engineer performance score: {score:.2f}")
        print()
        
        print("✅ Performance score calculated")
        print()
        
    except Exception as e:
        print(f"❌ Failed to calculate score: {e}")
        return False
    
    # Test 7: Get routing recommendations
    print("TEST 7: Get Routing Recommendations")
    print("-" * 80)
    
    try:
        recommendations = await feedback.get_routing_recommendations()
        
        print("Routing Recommendations:")
        print()
        
        if recommendations.get('top_performers'):
            print("Top Performers (prefer these):")
            for rec in recommendations['top_performers'][:3]:
                print(f"  • {rec['agent']}: {rec['success_rate']:.1f}% success")
            print()
        
        if recommendations.get('low_performers'):
            print("Low Performers (avoid these):")
            for rec in recommendations['low_performers'][:3]:
                print(f"  • {rec['agent']}: {rec['success_rate']:.1f}% success")
            print()
        
        print(f"Overall: {recommendations.get('overall_recommendation', 'N/A')}")
        print()
        
        print("✅ Routing recommendations generated")
        print()
        
    except Exception as e:
        print(f"❌ Failed to get recommendations: {e}")
        return False
    
    # Test 8: Run feedback cycle
    print("TEST 8: Run Complete Feedback Cycle")
    print("-" * 80)
    
    try:
        results = await feedback.run_feedback_cycle()
        
        print("Feedback Cycle Results:")
        print(f"  • Total agents: {results.get('total_agents', 0)}")
        print(f"  • Avg success rate: {results.get('avg_success_rate', 0):.1f}%")
        print(f"  • Median success rate: {results.get('median_success_rate', 0):.1f}%")
        print(f"  • Top performers: {results.get('top_performers', 0)}")
        print(f"  • Low performers: {results.get('low_performers', 0)}")
        print(f"  • Feedback applied: {results.get('feedback_applied', False)}")
        print()
        
        print("✅ Feedback cycle complete")
        print()
        
    except Exception as e:
        print(f"❌ Failed to run feedback cycle: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    await store.close()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("✅ Record task executions: PASS")
    print("✅ Update performance metrics: PASS")
    print("✅ Get agent performance: PASS")
    print("✅ Get all agent performance: PASS")
    print("✅ Get top performers: PASS")
    print("✅ Calculate performance score: PASS")
    print("✅ Get routing recommendations: PASS")
    print("✅ Run feedback cycle: PASS")
    print()
    print("🎉 PERFORMANCE FEEDBACK LOOP TEST PASSED!")
    print()
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_performance_feedback())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

