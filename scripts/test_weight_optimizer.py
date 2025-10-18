#!/usr/bin/env python3
"""Test weight optimizer for adaptive routing.

This script tests the weight optimization functionality.
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.routing.weight_optimizer import WeightOptimizer
from src.adapters.rag.surrealdb_store import SurrealDBStore
from src.adapters.llm.rag_config import RAGConfig


async def test_weight_optimizer():
    """Test weight optimizer."""
    
    print("=" * 80)
    print("WEIGHT OPTIMIZER TEST")
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
    
    # Create optimizer
    optimizer = WeightOptimizer(db_store=store, min_samples=3)
    
    # Test 1: Analyze routing performance
    print("TEST 1: Analyze Routing Performance")
    print("-" * 80)
    
    try:
        performance = await optimizer.analyze_routing_performance()
        
        print(f"Total decisions: {performance['total_decisions']}")
        print()
        
        if performance['total_decisions'] > 0:
            print("Performance by domain:")
            for domain, stats in performance['by_domain'].items():
                print(f"  • {domain}:")
                print(f"    Total: {stats['total']}")
                print(f"    Success: {stats['success']}")
                print(f"    Failure: {stats['failure']}")
                print(f"    Success rate: {stats['success_rate']:.1f}%")
            print()
            
            print("Performance by agent:")
            for agent, stats in list(performance['by_agent'].items())[:5]:
                print(f"  • {agent}:")
                print(f"    Total: {stats['total']}")
                print(f"    Success rate: {stats['success_rate']:.1f}%")
            print()
            
            print("Performance by strategy:")
            for strategy, stats in performance['by_strategy'].items():
                print(f"  • {strategy}:")
                print(f"    Total: {stats['total']}")
                print(f"    Success rate: {stats['success_rate']:.1f}%")
            print()
        else:
            print("⚠️  No completed routing decisions found")
            print("   Run tasks with routing to generate data")
            print()
        
        print("✅ Performance analysis complete")
        print()
        
    except Exception as e:
        print(f"❌ Performance analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Optimize domain weights
    print("TEST 2: Optimize Domain Weights")
    print("-" * 80)
    
    try:
        domain_weights = await optimizer.optimize_domain_weights()
        
        if domain_weights:
            print("Optimized domain weights:")
            for domain, weight in domain_weights.items():
                print(f"  • {domain}: {weight:.2f}x")
            print()
            print("✅ Domain weights optimized")
        else:
            print("⚠️  Insufficient data for weight optimization")
            print(f"   Need at least {optimizer.min_samples} samples per domain")
            print()
        
        print()
        
    except Exception as e:
        print(f"❌ Domain weight optimization failed: {e}")
        return False
    
    # Test 3: Optimize agent weights
    print("TEST 3: Optimize Agent Weights")
    print("-" * 80)
    
    try:
        agent_weights = await optimizer.optimize_agent_weights()
        
        if agent_weights:
            print("Optimized agent weights:")
            for agent, weight in list(agent_weights.items())[:10]:
                print(f"  • {agent}: {weight:.2f}x")
            print()
            print("✅ Agent weights optimized")
        else:
            print("⚠️  Insufficient data for weight optimization")
            print()
        
        print()
        
    except Exception as e:
        print(f"❌ Agent weight optimization failed: {e}")
        return False
    
    # Test 4: Get optimization recommendations
    print("TEST 4: Get Optimization Recommendations")
    print("-" * 80)
    
    try:
        recommendations = await optimizer.get_optimization_recommendations()
        
        print(f"Total decisions analyzed: {recommendations['total_decisions']}")
        print()
        
        if recommendations['recommendations']:
            print("Recommendations:")
            for i, rec in enumerate(recommendations['recommendations'], 1):
                print(f"{i}. {rec['type'].upper()}")
                print(f"   Message: {rec['message']}")
                if 'suggestion' in rec:
                    print(f"   Suggestion: {rec['suggestion']}")
                print()
        else:
            print("✅ No issues found - routing performance is good")
            print()
        
        print("✅ Recommendations generated")
        print()
        
    except Exception as e:
        print(f"❌ Recommendation generation failed: {e}")
        return False
    
    # Test 5: Run complete optimization cycle
    print("TEST 5: Run Complete Optimization Cycle")
    print("-" * 80)
    
    try:
        results = await optimizer.run_optimization_cycle()
        
        print("Optimization cycle complete:")
        print(f"  • Total decisions: {results['performance']['total_decisions']}")
        print(f"  • Domain weights: {len(results['domain_weights'])} optimized")
        print(f"  • Agent weights: {len(results['agent_weights'])} optimized")
        print(f"  • Recommendations: {len(results['recommendations']['recommendations'])}")
        print()
        
        print("✅ Optimization cycle complete")
        print()
        
    except Exception as e:
        print(f"❌ Optimization cycle failed: {e}")
        return False
    
    await store.close()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("✅ Performance analysis: PASS")
    print("✅ Domain weight optimization: PASS")
    print("✅ Agent weight optimization: PASS")
    print("✅ Recommendation generation: PASS")
    print("✅ Optimization cycle: PASS")
    print()
    print("🎉 WEIGHT OPTIMIZER TEST PASSED!")
    print()
    
    if performance['total_decisions'] < optimizer.min_samples:
        print("NOTE: Insufficient data for full optimization")
        print(f"      Run {optimizer.min_samples - performance['total_decisions']} more tasks to enable optimization")
        print()
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_weight_optimizer())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

