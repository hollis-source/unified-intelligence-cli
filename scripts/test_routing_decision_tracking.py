#!/usr/bin/env python3
"""Test routing decision tracking.

This script tests that routing decisions are properly tracked in the
routing_decisions table for feedback learning.
"""

import asyncio
import os
import sys
import uuid

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.adapters.rag.surrealdb_store import SurrealDBStore
from src.adapters.llm.rag_config import RAGConfig


async def test_routing_decision_tracking():
    """Test routing decision tracking."""
    
    print("=" * 80)
    print("ROUTING DECISION TRACKING TEST")
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
    
    # Test 1: Store routing decision
    print("TEST 1: Store Routing Decision")
    print("-" * 80)
    
    task_id = str(uuid.uuid4())
    
    try:
        await store.store_routing_decision(
            task_id=task_id,
            task_description="Write BDD tests for login functionality",
            task_domain="qa",
            selected_agent="qa-engineer",
            selected_team="QA",
            routing_strategy="rag",
            confidence=0.85,
            success=None,  # Will be updated after execution
            actual_agent="qa-engineer",
            fallback_used=False,
            metadata={
                "pattern_count": 3,
                "routing_hints": {
                    "suggested_agent": "qa-engineer",
                    "confidence": 0.85
                },
                "top_patterns": [
                    {"agent": "qa-engineer", "similarity": 0.92},
                    {"agent": "qa-engineer", "similarity": 0.87},
                    {"agent": "qa-lead", "similarity": 0.78}
                ]
            }
        )
        
        print("✅ Routing decision stored successfully")
        print(f"   Task ID: {task_id}")
        print(f"   Agent: qa-engineer")
        print(f"   Confidence: 0.85")
        print()
        
    except Exception as e:
        print(f"❌ Failed to store routing decision: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Retrieve routing decision
    print("TEST 2: Retrieve Routing Decision")
    print("-" * 80)
    
    try:
        sql = "SELECT * FROM routing_decisions WHERE task_id = $task_id LIMIT 1;"
        result = await store.query(sql, {"task_id": task_id})

        # Handle different result formats
        decision = None
        if result:
            if isinstance(result, list) and len(result) > 0:
                if isinstance(result[0], dict):
                    # Direct result format
                    decision = result[0]
                elif hasattr(result[0], 'get') and result[0].get("result"):
                    # Nested result format
                    decisions = result[0]["result"]
                    if decisions:
                        decision = decisions[0]

        if decision:
            print("✅ Routing decision retrieved successfully")
            print(f"   Task: {decision.get('task_description', 'N/A')[:50]}...")
            print(f"   Domain: {decision.get('task_domain')}")
            print(f"   Selected Agent: {decision.get('selected_agent')}")
            print(f"   Strategy: {decision.get('routing_strategy')}")
            print(f"   Confidence: {decision.get('confidence')}")
            print(f"   Fallback Used: {decision.get('fallback_used')}")
            print()
        else:
            print("❌ Routing decision not found")
            print(f"   Result: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to retrieve routing decision: {e}")
        return False
    
    # Test 3: Get routing accuracy
    print("TEST 3: Get Routing Accuracy")
    print("-" * 80)
    
    try:
        accuracy = await store.get_routing_accuracy(strategy="rag", limit=100)
        print(f"✅ Routing accuracy calculated")
        print(f"   Strategy: rag")
        print(f"   Accuracy: {accuracy:.1f}%")
        print(f"   Note: Accuracy is 0% because success field is None (not yet updated)")
        print()
        
    except Exception as e:
        print(f"❌ Failed to get routing accuracy: {e}")
        return False
    
    # Test 4: Get recent routing decisions
    print("TEST 4: Get Recent Routing Decisions")
    print("-" * 80)
    
    try:
        decisions = await store.get_recent_routing_decisions(limit=5)
        print(f"✅ Retrieved {len(decisions)} recent routing decisions")
        
        for i, decision in enumerate(decisions, 1):
            print(f"   {i}. {decision.get('task_description', 'N/A')[:40]}...")
            print(f"      Agent: {decision.get('selected_agent')}, Strategy: {decision.get('routing_strategy')}")
        print()
        
    except Exception as e:
        print(f"❌ Failed to get recent decisions: {e}")
        return False
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print("✅ Routing decision storage: PASS")
    print("✅ Routing decision retrieval: PASS")
    print("✅ Routing accuracy calculation: PASS")
    print("✅ Recent decisions query: PASS")
    print()
    print("🎉 ROUTING DECISION TRACKING TEST PASSED!")
    print()
    print("Next steps:")
    print("1. Integrate tracking into RAGTaskCoordinator")
    print("2. Update success field after task execution")
    print("3. Use routing decisions for feedback learning")
    print()
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_routing_decision_tracking())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

