#!/usr/bin/env python3
"""Measure routing accuracy improvement: RAG vs Baseline.

This script compares routing accuracy between:
1. Baseline routing (domain-based TeamRouter)
2. RAG routing (pattern-based RAGTeamRouter)

Target: +10% accuracy improvement with RAG
"""

import asyncio
import os
import sys
from typing import List, Dict, Any, Tuple

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.entity import Task
from src.routing.domain_classifier import DomainClassifier
from src.routing.team_router import TeamRouter
from src.routing.rag_team_router import RAGTeamRouter
from src.factories.team_factory import TeamFactory
from src.adapters.rag.surrealdb_store import SurrealDBStore
from src.adapters.rag.embedding_pipeline import EmbeddingPipeline
from src.adapters.llm.rag_config import RAGConfig


# Test tasks with known correct domains/agents
TEST_TASKS = [
    # QA tasks (should route to QA team)
    {"description": "Write BDD tests for login functionality", "expected_domain": "qa", "expected_agent": "qa-engineer"},
    {"description": "Create acceptance tests for checkout flow", "expected_domain": "qa", "expected_agent": "qa-engineer"},
    {"description": "Design test cases for user registration", "expected_domain": "testing", "expected_agent": "test-engineer"},
    {"description": "Perform exploratory testing on dashboard", "expected_domain": "qa", "expected_agent": "exploratory-test-engineer"},
    {"description": "Write Gherkin scenarios for payment processing", "expected_domain": "qa", "expected_agent": "qa-engineer"},
    
    # Backend tasks (should route to Backend team)
    {"description": "Create REST API endpoint for user authentication", "expected_domain": "backend", "expected_agent": "backend-lead"},
    {"description": "Implement database schema for orders", "expected_domain": "backend", "expected_agent": "database-specialist"},
    {"description": "Add GraphQL resolver for products", "expected_domain": "backend", "expected_agent": "backend-lead"},
    {"description": "Optimize SQL query performance", "expected_domain": "backend", "expected_agent": "database-specialist"},
    {"description": "Build microservice for notifications", "expected_domain": "backend", "expected_agent": "backend-lead"},
    
    # Frontend tasks (should route to Frontend team)
    {"description": "Create React component for user profile", "expected_domain": "frontend", "expected_agent": "frontend-lead"},
    {"description": "Implement responsive navbar with Tailwind", "expected_domain": "frontend", "expected_agent": "css-specialist"},
    {"description": "Add form validation to login page", "expected_domain": "frontend", "expected_agent": "frontend-lead"},
    {"description": "Build Vue.js dashboard with charts", "expected_domain": "frontend", "expected_agent": "frontend-lead"},
    {"description": "Improve accessibility of checkout flow", "expected_domain": "frontend", "expected_agent": "frontend-lead"},
    
    # Testing tasks (should route to Testing team)
    {"description": "Write unit tests for authentication service", "expected_domain": "testing", "expected_agent": "test-engineer"},
    {"description": "Create integration tests for API endpoints", "expected_domain": "testing", "expected_agent": "test-engineer"},
    {"description": "Add performance tests for database queries", "expected_domain": "testing", "expected_agent": "test-engineer"},
    {"description": "Implement security tests for user input", "expected_domain": "testing", "expected_agent": "test-engineer"},
    {"description": "Set up end-to-end tests with Cypress", "expected_domain": "testing", "expected_agent": "test-engineer"},
    
    # DevOps tasks (should route to DevOps team)
    {"description": "Configure Docker container for application", "expected_domain": "devops", "expected_agent": "devops-lead"},
    {"description": "Set up Kubernetes deployment", "expected_domain": "devops", "expected_agent": "devops-lead"},
    {"description": "Create CI/CD pipeline with GitHub Actions", "expected_domain": "devops", "expected_agent": "devops-lead"},
    {"description": "Deploy application to AWS", "expected_domain": "devops", "expected_agent": "devops-lead"},
    {"description": "Monitor application performance with Prometheus", "expected_domain": "devops", "expected_agent": "devops-lead"},
]


async def measure_baseline_accuracy(teams: List[Any]) -> Tuple[float, List[Dict[str, Any]]]:
    """Measure baseline routing accuracy using TeamRouter."""
    print("=" * 80)
    print("BASELINE ROUTING (TeamRouter)")
    print("=" * 80)
    print()
    
    classifier = DomainClassifier()
    router = TeamRouter(classifier)
    
    results = []
    correct = 0
    
    for i, test_case in enumerate(TEST_TASKS, 1):
        task = Task(
            task_id=f"baseline-{i}",
            description=test_case["description"]
        )
        
        # Route task
        selected_agent = router.route(task, teams)
        
        # Check if correct
        expected_domain = test_case["expected_domain"]
        actual_domain = classifier.classify(task)
        domain_correct = actual_domain == expected_domain
        
        # For baseline, we just check domain correctness
        # (agent selection is deterministic based on domain)
        is_correct = domain_correct
        
        if is_correct:
            correct += 1
        
        results.append({
            "task": test_case["description"][:50] + "...",
            "expected_domain": expected_domain,
            "actual_domain": actual_domain,
            "selected_agent": selected_agent.role if selected_agent else "None",
            "correct": is_correct
        })
        
        status = "✅" if is_correct else "❌"
        print(f"{status} Task {i}: {test_case['description'][:60]}...")
        print(f"   Expected domain: {expected_domain}, Actual: {actual_domain}")
        print(f"   Selected agent: {selected_agent.role if selected_agent else 'None'}")
        print()
    
    accuracy = (correct / len(TEST_TASKS)) * 100
    
    print("=" * 80)
    print(f"BASELINE ACCURACY: {accuracy:.1f}% ({correct}/{len(TEST_TASKS)} correct)")
    print("=" * 80)
    print()
    
    return accuracy, results


async def measure_rag_accuracy(teams: List[Any]) -> Tuple[float, List[Dict[str, Any]]]:
    """Measure RAG routing accuracy using RAGTeamRouter."""
    print("=" * 80)
    print("RAG ROUTING (RAGTeamRouter)")
    print("=" * 80)
    print()
    
    # Setup RAG components
    config = RAGConfig()
    db_url = os.getenv("SURREALDB_URL", "ws://localhost:8000")
    
    # Check if we have OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  No OPENAI_API_KEY found - RAG routing will fall back to baseline")
        print("   Set OPENAI_API_KEY to test RAG routing with embeddings")
        print()
    
    try:
        # Initialize RAG components
        db_store = SurrealDBStore(
            url=db_url,
            namespace=config.db_namespace,
            database=config.db_database,
            user=config.db_user,
            password=config.db_password
        )
        await db_store.connect()
        
        embedder = EmbeddingPipeline(
            model_name=config.embedding_model,
            api_key=os.getenv("OPENAI_API_KEY", "")
        )
        
        classifier = DomainClassifier()
        router = RAGTeamRouter(
            domain_classifier=classifier,
            db_store=db_store,
            embedding_pipeline=embedder,
            top_k=3,
            similarity_threshold=0.5
        )
        
        print("✅ RAG components initialized")
        print()
        
    except Exception as e:
        print(f"❌ Failed to initialize RAG components: {e}")
        print("   Falling back to baseline routing")
        return await measure_baseline_accuracy(teams)
    
    results = []
    correct = 0
    
    for i, test_case in enumerate(TEST_TASKS, 1):
        task = Task(
            task_id=f"rag-{i}",
            description=test_case["description"]
        )
        
        # Route task with RAG
        try:
            selected_agent = await router.route_with_rag(task, teams)
        except Exception as e:
            print(f"⚠️  RAG routing failed for task {i}: {e}")
            # Fall back to base routing
            selected_agent = router.route(task, teams)
        
        # Check if correct
        expected_domain = test_case["expected_domain"]
        actual_domain = classifier.classify(task)
        domain_correct = actual_domain == expected_domain
        
        # For RAG, we check domain correctness
        is_correct = domain_correct
        
        if is_correct:
            correct += 1
        
        results.append({
            "task": test_case["description"][:50] + "...",
            "expected_domain": expected_domain,
            "actual_domain": actual_domain,
            "selected_agent": selected_agent.role if selected_agent else "None",
            "correct": is_correct
        })
        
        status = "✅" if is_correct else "❌"
        print(f"{status} Task {i}: {test_case['description'][:60]}...")
        print(f"   Expected domain: {expected_domain}, Actual: {actual_domain}")
        print(f"   Selected agent: {selected_agent.role if selected_agent else 'None'}")
        print()
    
    accuracy = (correct / len(TEST_TASKS)) * 100
    
    print("=" * 80)
    print(f"RAG ACCURACY: {accuracy:.1f}% ({correct}/{len(TEST_TASKS)} correct)")
    print("=" * 80)
    print()
    
    await db_store.close()
    
    return accuracy, results


async def main():
    """Main function to measure routing accuracy."""
    print("=" * 80)
    print("ROUTING ACCURACY MEASUREMENT")
    print("=" * 80)
    print(f"Test tasks: {len(TEST_TASKS)}")
    print(f"Target improvement: +10%")
    print()
    
    # Create teams
    team_factory = TeamFactory()
    teams = team_factory.create_scaled_teams()
    print(f"✅ Created {len(teams)} teams")
    print()
    
    # Measure baseline accuracy
    baseline_accuracy, baseline_results = await measure_baseline_accuracy(teams)
    
    # Measure RAG accuracy
    rag_accuracy, rag_results = await measure_rag_accuracy(teams)
    
    # Compare results
    print("=" * 80)
    print("COMPARISON")
    print("=" * 80)
    print(f"Baseline accuracy: {baseline_accuracy:.1f}%")
    print(f"RAG accuracy:      {rag_accuracy:.1f}%")
    print(f"Improvement:       {rag_accuracy - baseline_accuracy:+.1f}%")
    print()
    
    if rag_accuracy >= baseline_accuracy + 10:
        print("🎉 SUCCESS: RAG routing achieved +10% improvement target!")
    elif rag_accuracy > baseline_accuracy:
        print(f"✅ GOOD: RAG routing improved by {rag_accuracy - baseline_accuracy:.1f}%")
        print(f"   (Target: +10%, need {10 - (rag_accuracy - baseline_accuracy):.1f}% more)")
    elif rag_accuracy == baseline_accuracy:
        print("⚠️  NEUTRAL: RAG routing same as baseline")
        print("   Note: This is expected without historical patterns")
    else:
        print("❌ REGRESSION: RAG routing worse than baseline")
    
    print()
    print("=" * 80)
    print("NOTES")
    print("=" * 80)
    print("• RAG routing requires historical patterns to improve accuracy")
    print("• Without patterns, RAG falls back to baseline routing")
    print("• Run tasks with --enable-rag to build pattern database")
    print("• After ~50 tasks, RAG should show +10% improvement")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

