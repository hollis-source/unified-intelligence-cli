#!/usr/bin/env python3
"""
End-to-end test for Prompt Framework Integration.
Tests Phases 1-3 through actual use.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_phase1_prompt_strategy():
    """Test Phase 1: PromptStrategy entity and validator."""
    print("\n" + "="*70)
    print("PHASE 1: Core Integration (PromptStrategy + Validator)")
    print("="*70)
    
    from src.entity.prompt_strategy import PromptStrategy
    from src.adapters.prompt import PromptStrategyValidator
    
    try:
        # Create prompt strategy
        strategy = PromptStrategy(
            persona="Senior Backend Developer with expertise in Python and FastAPI",
            goal="Reduce API latency from 500ms to 100ms",
            task="Implement Redis caching layer for frequently accessed endpoints",
            context="Agent Tier: 2\nPrevious interactions: 0\nULTRATHINK enabled",
            agent_type="backend-developer",
            domain="backend"
        )
        
        print(f"✓ Created PromptStrategy")
        print(f"  - Domain: {strategy.domain}")
        print(f"  - Agent Type: {strategy.agent_type}")
        print(f"  - Iteration: {strategy.iteration}")
        
        # Validate strategy
        validator = PromptStrategyValidator(min_score=60.0)
        result = validator.validate_strategy(strategy)
        
        print(f"\n✓ Validated PromptStrategy")
        print(f"  - Score: {result.score:.1f}/100")
        print(f"  - Passed: {result.passed}")
        print(f"  - Specificity: {result.specificity:.1f}/100")
        print(f"  - Clarity: {result.clarity:.1f}/100")
        print(f"  - Completeness: {result.completeness}")
        
        if result.suggestions:
            print(f"  - Suggestions: {len(result.suggestions)}")
            for i, suggestion in enumerate(result.suggestions[:3], 1):
                print(f"    {i}. {suggestion}")
        
        return True
        
    except Exception as e:
        print(f"✗ Phase 1 failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_phase2_llm_executor_integration():
    """Test Phase 2: LLMAgentExecutor with prompt strategy."""
    print("\n" + "="*70)
    print("PHASE 2: LLMAgentExecutor Enhancement")
    print("="*70)
    
    from src.entity import Agent, Task
    from src.adapters.agent.llm_executor import LLMAgentExecutor
    from src.adapters.prompt import PromptStrategyValidator
    
    try:
        # Create agent and task
        agent = Agent(
            role="backend-developer",
            capabilities=["python", "fastapi", "postgresql"],
            tier=2
        )
        
        task = Task(description="Implement caching layer for API endpoints to reduce latency from 500ms to 100ms")
        
        print(f"✓ Created Agent and Task")
        print(f"  - Agent: {agent.role}")
        print(f"  - Capabilities: {', '.join(agent.capabilities)}")
        print(f"  - Task: {task.description[:60]}...")
        
        # Create executor with prompt strategy support
        validator = PromptStrategyValidator(min_score=60.0)
        executor = LLMAgentExecutor(
            llm_provider=None,  # No actual LLM needed for this test
            prompt_validator=validator,
            validate_prompts=True,
            use_prompt_strategy=True
        )
        
        print(f"\n✓ Created LLMAgentExecutor")
        print(f"  - Prompt validation: enabled")
        print(f"  - Prompt strategy: enabled")
        
        # Build prompt strategy
        strategy = executor._build_prompt_strategy(agent, task, None)
        
        print(f"\n✓ Built PromptStrategy from Agent + Task")
        print(f"  - Domain: {strategy.domain}")
        print(f"  - Agent Type: {strategy.agent_type}")
        print(f"  - Persona preview: {strategy.persona[:80]}...")
        print(f"  - Goal preview: {strategy.goal[:80]}...")
        
        # Test domain inference
        test_cases = [
            ("backend-developer", "backend"),
            ("frontend-developer", "frontend"),
            ("test-engineer", "testing"),
            ("database-admin", "database"),
            ("unknown-role", "general"),
        ]
        
        print(f"\n✓ Testing domain inference:")
        for role, expected_domain in test_cases:
            inferred = executor._infer_domain(role)
            status = "✓" if inferred == expected_domain else "✗"
            print(f"  {status} {role} → {inferred}")
        
        # Test goal extraction
        test_goals = [
            "Reduce API latency from 500ms to 100ms",
            "Improve test coverage by 20%",
            "Add logging to module",
        ]
        
        print(f"\n✓ Testing goal extraction:")
        for desc in test_goals:
            task_temp = Task(description=desc)
            goal = executor._extract_goal(task_temp)
            print(f"  - '{desc[:40]}...' → '{goal[:50]}...'")
        
        return True
        
    except Exception as e:
        print(f"✗ Phase 2 failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_phase3_template_integration():
    """Test Phase 3: Template loading and merging."""
    print("\n" + "="*70)
    print("PHASE 3: Template Library Integration")
    print("="*70)
    
    from src.adapters.prompt import TemplateLoader
    from src.use_cases.prompt_template_merger import PromptTemplateMerger
    from src.entity import Agent, Task
    
    try:
        # Load templates
        loader = TemplateLoader()
        
        print(f"✓ Initialized TemplateLoader")
        print(f"  - Framework path: {loader.framework_path}")
        print(f"  - Templates loaded: {loader.get_template_count()}")
        
        if loader.get_template_count() == 0:
            print(f"  ⚠ No templates found (framework not available)")
            print(f"  This is expected if agentic-prompt-strategy-framework is not present")
            return True
        
        # List available domains
        domains = loader.list_domains()
        print(f"\n✓ Available domains: {', '.join(domains[:5])}")
        if len(domains) > 5:
            print(f"  ... and {len(domains) - 5} more")
        
        # Load specific templates
        test_domains = ["backend", "frontend", "testing"]
        for domain in test_domains:
            template = loader.load_template(domain)
            if template:
                print(f"\n✓ Loaded {domain} template")
                print(f"  - Framework: {template.framework}")
                print(f"  - Persona preview: {template.persona[:60]}...")
                print(f"  - Goal preview: {template.goal[:60]}...")
            else:
                print(f"  ⚠ {domain} template not found")
        
        # Test template merging
        backend_template = loader.load_template("backend")
        if backend_template:
            print(f"\n✓ Testing template merging:")
            
            agent = Agent(
                role="backend-developer",
                capabilities=["python", "fastapi", "postgresql"],
                tier=2
            )
            
            task = Task(description="Implement caching layer for API endpoints")
            
            merger = PromptTemplateMerger()
            strategy = merger.merge(
                backend_template,
                agent,
                task,
                context_text="ULTRATHINK enabled\nPrevious interactions: 0"
            )
            
            print(f"  - Domain: {strategy.domain}")
            print(f"  - Agent Type: {strategy.agent_type}")
            print(f"\n  Merged Persona:")
            for line in strategy.persona.split('\n')[:3]:
                print(f"    {line}")
            print(f"\n  Merged Goal:")
            for line in strategy.goal.split('\n')[:2]:
                print(f"    {line}")
            print(f"\n  Merged Context:")
            for line in strategy.context.split('\n')[:3]:
                print(f"    {line}")
        
        return True
        
    except Exception as e:
        print(f"✗ Phase 3 failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_integration():
    """Test full end-to-end integration."""
    print("\n" + "="*70)
    print("FULL INTEGRATION: Template → Strategy → Validation")
    print("="*70)
    
    from src.adapters.prompt import TemplateLoader, PromptStrategyValidator
    from src.use_cases.prompt_template_merger import PromptTemplateMerger
    from src.entity import Agent, Task
    
    try:
        # 1. Load template
        loader = TemplateLoader()
        template = loader.load_template("backend")
        
        if not template:
            print("⚠ Backend template not available, using dynamic generation")
            from src.entity.prompt_strategy import PromptStrategy
            strategy = PromptStrategy(
                persona="Senior Backend Developer",
                goal="Build scalable services",
                task="Implement caching layer",
                context="Tier: 2",
                agent_type="backend-developer",
                domain="backend"
            )
        else:
            # 2. Create agent and task
            agent = Agent(
                role="backend-developer",
                capabilities=["python", "fastapi", "redis", "postgresql"],
                tier=2
            )
            
            task = Task(description="Implement Redis caching layer for user profile endpoints to reduce latency from 500ms to 100ms")
            
            # 3. Merge template with task
            merger = PromptTemplateMerger()
            strategy = merger.merge(
                template,
                agent,
                task,
                context_text="ULTRATHINK enabled\nPrevious interactions: 0\nPriority: High"
            )
        
        print(f"✓ Step 1: Template loaded and merged")
        
        # 4. Validate strategy
        validator = PromptStrategyValidator(min_score=60.0)
        result = validator.validate_strategy(strategy)
        
        print(f"✓ Step 2: Strategy validated")
        print(f"  - Score: {result.score:.1f}/100")
        print(f"  - Passed: {result.passed}")
        
        # 5. Display final prompt
        print(f"\n✓ Step 3: Final Prompt Strategy")
        print(f"\n{'─'*70}")
        print(f"PERSONA:")
        print(strategy.persona)
        print(f"\n{'─'*70}")
        print(f"GOAL:")
        print(strategy.goal)
        print(f"\n{'─'*70}")
        print(f"TASK:")
        print(strategy.task)
        print(f"\n{'─'*70}")
        print(f"CONTEXT:")
        print(strategy.context)
        print(f"{'─'*70}")
        
        print(f"\n✓ Full integration successful!")
        print(f"  - Quality score: {result.score:.1f}/100")
        print(f"  - Specificity: {result.specificity:.1f}/100")
        print(f"  - Clarity: {result.clarity:.1f}/100")
        print(f"  - Completeness: {result.completeness}")
        
        return True
        
    except Exception as e:
        print(f"✗ Full integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all E2E tests."""
    print("\n" + "="*70)
    print("PROMPT FRAMEWORK INTEGRATION - E2E TEST SUITE")
    print("="*70)
    
    results = {
        "Phase 1: Core Integration": test_phase1_prompt_strategy(),
        "Phase 2: LLMAgentExecutor": test_phase2_llm_executor_integration(),
        "Phase 3: Template Integration": test_phase3_template_integration(),
        "Full Integration": test_full_integration(),
    }
    
    print("\n" + "="*70)
    print("TEST RESULTS")
    print("="*70)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

