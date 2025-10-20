#!/usr/bin/env python3
"""
End-to-end test for M3 components.
Tests context analysis, task generation, prioritization, validation without LLM.
"""
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_context_snapshot():
    """Test context snapshot generation."""
    print("\n" + "="*70)
    print("TEST 1: Context Snapshot")
    print("="*70)
    
    from src.analysis.git_analyzer import GitAnalyzer
    from src.analysis.health_scorer import HealthScorer
    
    try:
        # Test git analyzer
        git_analyzer = GitAnalyzer(repo_path=".")
        git_analysis = git_analyzer.analyze(days=30)
        
        print(f"✓ Git analysis: {git_analysis.total_commits} commits")
        print(f"  - High-churn files: {len(git_analysis.high_churn_files)}")
        print(f"  - Patterns: {len(git_analysis.commit_patterns)}")
        
        # Test health scorer
        health_scorer = HealthScorer()
        health_score = health_scorer.compute_health(
            git_analysis=git_analysis,
            coverage_analysis=None,
            metrics_analysis=None,
            test_pass_rate=1.0,
        )
        
        print(f"✓ Health score: {health_score.overall_score:.1f}/100 (Grade: {health_score.grade})")
        print(f"  - Top opportunities: {len(health_score.top_opportunities)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Context snapshot failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_generation():
    """Test task generation with heuristics."""
    print("\n" + "="*70)
    print("TEST 2: Task Generation (Heuristic)")
    print("="*70)
    
    from src.claude_orchestrator.adapters.heuristic_task_generator import HeuristicTaskGenerator
    from src.claude_orchestrator.entities.task_context import TaskContext
    
    try:
        # Create mock context
        context = TaskContext.create(
            snapshot_time=datetime.now(),
            recent_commits=["abc123", "def456"],
            modified_files=["src/main.py", "src/adapters/agent/llm_executor.py"],
            current_branch="main",
            test_pass_rate=0.95,
            coverage_percentage=65.0,
        )
        
        # Generate task
        generator = HeuristicTaskGenerator()
        task = generator.generate_task(context, goal=None)
        
        print(f"✓ Generated task: {task.id}")
        print(f"  - Priority: {task.priority}")
        print(f"  - Complexity: {task.complexity}")
        print(f"  - Estimated: {task.estimated_minutes} min")
        print(f"  - Instruction preview: {task.instruction[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"✗ Task generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_prioritization():
    """Test task prioritization."""
    print("\n" + "="*70)
    print("TEST 3: Task Prioritization")
    print("="*70)
    
    from src.claude_orchestrator.use_cases.task_prioritizer import TaskPrioritizer
    from src.claude_orchestrator.entities.generated_task import GeneratedTask
    
    try:
        # Create mock tasks
        tasks = [
            GeneratedTask.create(
                id="task-1",
                instruction="Fix failing test: test_user_login\n\nSteps:\n1. Run test\n2. Fix issue",
                rationale="Critical: test is failing",
                goal_id="test-fixes",
                estimated_minutes=30,
                priority="P0",
                complexity="low",
            ),
            GeneratedTask.create(
                id="task-2",
                instruction="Improve coverage for src/main.py\n\nSteps:\n1. Identify uncovered lines\n2. Write tests",
                rationale="Coverage is 65%, target is 80%",
                goal_id="coverage",
                estimated_minutes=60,
                priority="P2",
                complexity="medium",
            ),
            GeneratedTask.create(
                id="task-3",
                instruction="Refactor high-churn file: src/adapters/agent/llm_executor.py\n\nSteps:\n1. Review code\n2. Extract methods",
                rationale="File has 33 commits in 30 days",
                goal_id="tech-debt",
                estimated_minutes=120,
                priority="P3",
                complexity="high",
            ),
        ]
        
        # Prioritize
        prioritizer = TaskPrioritizer()
        scored = prioritizer.rank_tasks(tasks)
        
        print(f"✓ Ranked {len(scored)} tasks:")
        for i, score in enumerate(scored[:3], 1):
            print(f"  {i}. {score.task.id} - Total: {score.total_score:.1f} (Impact: {score.impact_score:.1f}, Effort: {score.effort_score:.1f}, Urgency: {score.urgency_score:.1f})")
        
        return True
        
    except Exception as e:
        print(f"✗ Task prioritization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_validation():
    """Test task validation."""
    print("\n" + "="*70)
    print("TEST 4: Task Validation")
    print("="*70)
    
    from src.claude_orchestrator.use_cases.task_validator import TaskValidator
    from src.claude_orchestrator.entities.generated_task import GeneratedTask
    
    try:
        # Create tasks (some valid, some invalid)
        tasks = [
            GeneratedTask.create(
                id="valid-1",
                instruction="Add unit tests for user authentication\n\nSteps:\n1. Write tests\n2. Run tests\n3. Verify coverage",
                rationale="Improve test coverage",
                goal_id="coverage",
                estimated_minutes=45,
                priority="P2",
                complexity="medium",
            ),
            GeneratedTask.create(
                id="invalid-1",
                instruction="rm -rf /tmp/*",  # Dangerous!
                rationale="Clean up",
                goal_id="cleanup",
                estimated_minutes=5,
                priority="P3",
                complexity="low",
            ),
            GeneratedTask.create(
                id="invalid-2",
                instruction="Do stuff",  # Too short, no steps
                rationale="Fix",
                goal_id="general",
                estimated_minutes=30,
                priority="P2",
                complexity="medium",
            ),
        ]
        
        # Validate
        validator = TaskValidator()
        valid = validator.filter_valid(tasks)
        
        print(f"✓ Validated tasks: {len(valid)}/{len(tasks)} passed")
        for task in valid:
            print(f"  - {task.id}: VALID")
        
        for task in tasks:
            if task not in valid:
                result = validator.validate(task)
                print(f"  - {task.id}: REJECTED - {', '.join(result.reasons)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Task validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_active_learning():
    """Test active learning."""
    print("\n" + "="*70)
    print("TEST 5: Active Learning")
    print("="*70)
    
    from src.claude_orchestrator.use_cases.active_learning import ActiveLearning, WeakDomain
    
    try:
        # Create mock weak domains
        weak_domains = [
            WeakDomain(
                domain="database",
                accuracy=0.55,
                pattern_count=8,
                weakness_score=0.056,
                priority=1,
                recommendation="CRITICAL: Accuracy 55.0% is very low. Collect 50+ high-quality patterns.",
            ),
            WeakDomain(
                domain="frontend",
                accuracy=0.68,
                pattern_count=15,
                weakness_score=0.021,
                priority=2,
                recommendation="Accuracy 68.0% is below target. Collect 20+ patterns and review quality.",
            ),
        ]
        
        # Test prioritization
        active_learning = ActiveLearning()
        priorities = active_learning.prioritize_collection(weak_domains, max_domains=2)
        
        print(f"✓ Identified {len(weak_domains)} weak domains")
        for domain in weak_domains:
            print(f"  - {domain.domain}: {domain.accuracy:.1%} accuracy, {domain.pattern_count} patterns (P{domain.priority})")
        
        print(f"✓ Collection priorities:")
        for domain, target in priorities:
            print(f"  - {domain}: Collect to {target} patterns")
        
        return True
        
    except Exception as e:
        print(f"✗ Active learning failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_scheduler():
    """Test task scheduler."""
    print("\n" + "="*70)
    print("TEST 6: Task Scheduler")
    print("="*70)

    from src.claude_orchestrator.use_cases.task_scheduler import TaskScheduler
    from src.claude_orchestrator.entities.generated_task import GeneratedTask

    try:
        # Create mock tasks
        tasks = [
            GeneratedTask.create(
                id=f"task-{i}",
                instruction=f"Task {i}\n\nSteps:\n1. Do step 1\n2. Do step 2",
                rationale=f"Task {i} rationale",
                goal_id="test",
                estimated_minutes=30 + i*10,
                priority=f"P{i%3}",
                complexity=["low", "medium", "high"][i%3],
            )
            for i in range(10)
        ]

        # Schedule
        scheduler = TaskScheduler(max_concurrent=3, max_tasks_per_hour=5)
        schedule = scheduler.schedule_tasks(tasks)

        print(f"✓ Scheduled {len(schedule)}/{len(tasks)} tasks")

        summary = scheduler.get_schedule_summary()
        print(f"  - Total duration: {summary['total_duration_minutes']} minutes")
        print(f"  - Priority breakdown: {summary['priority_breakdown']}")

        # Show first 3 slots
        for i, slot in enumerate(schedule[:3], 1):
            print(f"  {i}. {slot.task.id} @ {slot.scheduled_time.strftime('%H:%M')} ({slot.task.estimated_minutes}min)")

        return True

    except Exception as e:
        print(f"✗ Task scheduler failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("M3 END-TO-END TEST SUITE")
    print("="*70)

    results = {
        "Context Snapshot": test_context_snapshot(),
        "Task Generation": test_task_generation(),
        "Task Prioritization": test_task_prioritization(),
        "Task Validation": test_task_validation(),
        "Active Learning": test_active_learning(),
        "Task Scheduler": test_task_scheduler(),
    }
    
    print("\n" + "="*70)
    print("TEST RESULTS")
    print("="*70)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

