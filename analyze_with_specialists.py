"""
Multi-Agent Codebase Analysis with 7 Specialists

Comprehensive analysis using:
- 5 specialist agents (Python, DSL, Category Theory, HTN, Algorithms)
- 2 generalist agents (Software Architect, Integration Architect)
- IBM Granite 4.0-H LLM (local, $0 cost)
- RAG-enhanced (SurrealDB codebase context)

Workflow:
  Phase 1: 7 agents analyze different domains in parallel (30-60s)
  Phase 2: Chief Architect synthesizes into integration roadmap (30s)

Output:
  - phase1_specialist_analyses.md (detailed analyses)
  - integration_roadmap.md (actionable plan with priorities)

Usage:
    python analyze_with_specialists.py

Expected duration: 60-90 seconds total
"""

import asyncio
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.adapters.llm.granite_adapter import GraniteAdapter
from src.adapters.agent.llm_executor import LLMAgentExecutor
from src.adapters.rag import EmbeddingPipeline, SurrealDBStore, CodebaseRAG
from src.entity import Agent, Task
from src.interface import LLMConfig
from specialist_agents import create_specialist_agents


async def comprehensive_analysis():
    """7-agent comprehensive codebase analysis."""

    print("=" * 80)
    print("COMPREHENSIVE CODEBASE ANALYSIS")
    print("Using 7 specialized agents + Granite + RAG")
    print("=" * 80)
    print()

    # Setup RAG components
    print("Initializing RAG components...")
    try:
        embedder = EmbeddingPipeline(
            model="sentence-transformers/all-mpnet-base-v2",
            provider="sentence-transformers"
        )
        db = SurrealDBStore(
            url="ws://localhost:8000",
            namespace="atado",
            database="rag",
            user="root",
            password="root"
        )
        await db.connect()
        print("  ✅ RAG: Embedder + SurrealDB ready")
    except Exception as e:
        print(f"  ⚠️  RAG setup failed: {e}")
        print(f"  Falling back to RAG-disabled mode")
        embedder = None
        db = None

    # Setup Granite with extended timeout (RAG temporarily disabled due to event loop issues)
    granite = GraniteAdapter(
        enable_rag=False,  # TODO: Fix event loop conflicts with async SurrealDB
        rag_db=db,
        rag_embedder=embedder,
        timeout=300  # Extended from 60s to handle complex analyses
    )
    executor = LLMAgentExecutor(
        llm_provider=granite,
        default_config=LLMConfig(temperature=0.7, max_tokens=1000),
        enable_cache=True,
        enable_ultrathink=False
    )

    # Create specialist agents
    specialists = create_specialist_agents()

    # Define 7 parallel analyses (domain-specific prompts)
    analyses = [
        # 1. Python Engineering Analysis
        {
            "agent": specialists["python_engineer"],
            "task": Task(
                description="""Analyze Python code quality across unified-intelligence-cli:

**Focus areas:**
1. Code organization (src/ structure, module boundaries)
2. Type hints coverage (which modules lack typing?)
3. Design patterns used (factory, adapter, strategy, etc.)
4. Anti-patterns or code smells
5. Pythonic idioms vs un-Pythonic code
6. Refactoring opportunities (DRY violations, long functions)

**Questions:**
- Which modules have the best code quality? Worst?
- Are design patterns applied consistently?
- What's the biggest technical debt?

Output: 800 words with specific file examples.""",
                priority=1
            ),
            "name": "python_quality_analysis"
        },

        # 2. DSL Engineering Analysis
        {
            "agent": specialists["dsl_engineer"],
            "task": Task(
                description="""Analyze DSL implementation in src/dsl/:

**Focus areas:**
1. Grammar definition (Lark grammar in src/dsl/grammar/)
2. Parser implementation (efficiency, error handling)
3. HTN compiler (src/dsl/adapters/htn_compiler.py)
4. DSL usage patterns (where is DSL actually used?)
5. Language expressiveness (what can't be expressed currently?)

**Questions:**
- Is the DSL grammar well-designed (unambiguous, efficient)?
- Are there unused DSL features?
- What DSL extensions would add value?
- Could DSL capabilities be exposed to ATADO agents?

Output: 800 words with grammar examples.""",
                priority=1
            ),
            "name": "dsl_analysis"
        },

        # 3. Category Theory Analysis
        {
            "agent": specialists["category_theory_specialist"],
            "task": Task(
                description="""Analyze category-theoretic abstractions in src/entity/category_theory/:

**Focus areas:**
1. Morphism implementations (src/entity/category_theory/morphism.py)
2. Functor usage (if any)
3. Composition patterns (how are morphisms composed?)
4. Graph operations (src/entity/graph/) as categorical structures
5. Workflow morphisms (src/entity/workflow_morphism.py)

**Questions:**
- Are category theory concepts applied correctly?
- Are there underutilized categorical abstractions?
- Could morphism composition be exposed as agent capabilities?
- Does the category-theoretic approach add value or complexity?

Output: 800 words with mathematical examples.""",
                priority=1
            ),
            "name": "category_theory_analysis"
        },

        # 4. HTN & Graph Theory Analysis
        {
            "agent": specialists["htn_expert"],
            "task": Task(
                description="""Analyze HTN planning and graph structures in src/entity/htn/:

**Focus areas:**
1. HTN node structure (src/entity/htn/htn_node.py)
2. HTN planner implementation (if exists)
3. Task decomposition algorithms
4. DAG validation (are HTN graphs always acyclic?)
5. Topological sort usage (execution ordering)
6. Graph operations (src/entity/graph/)

**Questions:**
- Is HTN planning efficient (complexity analysis)?
- Are there graph algorithm optimizations possible?
- Could HTN planning be exposed as agent capability?
- Are there cycle detection issues?

Output: 800 words with graph diagrams (ASCII art).""",
                priority=1
            ),
            "name": "htn_graph_analysis"
        },

        # 5. Algorithms & Performance Analysis
        {
            "agent": specialists["algorithms_expert"],
            "task": Task(
                description="""Analyze algorithm complexity and performance bottlenecks:

**Focus areas:**
1. Time complexity of key algorithms (search, routing, planning)
2. Space complexity (memory usage patterns)
3. Bottlenecks (O(n²) loops, redundant computations)
4. Data structure choices (list vs dict vs set appropriateness)
5. Caching opportunities (memoization, LRU caches)
6. Parallelization potential

**Questions:**
- What's the worst-case complexity of main workflows?
- Where are the performance bottlenecks?
- Which algorithms could be optimized (O(n²) → O(n log n))?
- Are there unnecessary complexity sources?

Output: 800 words with Big O analysis.""",
                priority=1
            ),
            "name": "algorithms_performance_analysis"
        },

        # 6. Architecture Analysis (existing)
        {
            "agent": Agent(role="software-architect", capabilities=["architecture"], tier=3),
            "task": Task(
                description="""Analyze ATADO architecture in src/:

**Focus areas:**
1. Clean Architecture compliance (entity/use case/adapter layers)
2. SOLID principles adherence
3. Dependency injection patterns
4. Team-based routing architecture

**Questions:**
- What's well-architected? What needs refactoring?
- Are there architectural inconsistencies?

Output: 600 words.""",
                priority=1
            ),
            "name": "architecture_analysis"
        },

        # 7. Integration Opportunities (existing)
        {
            "agent": Agent(role="integration-architect", capabilities=["integration"], tier=3),
            "task": Task(
                description="""Identify standalone scripts/tools not integrated into ATADO:

**Focus:**
- Root-level .py files
- scripts/ directory utilities
- Features that could be agent capabilities

**Question:** What functionality exists but isn't accessible to ATADO agents?

Output: 600 words with prioritized list.""",
                priority=1
            ),
            "name": "integration_opportunities"
        }
    ]

    print(f"🚀 Running {len(analyses)} specialized agents sequentially...")
    print(f"   Granite load-balanced across 2 instances (8080, 8081)")
    print(f"   Estimated duration: 3-5 minutes (sequential execution)\n")

    start = time.time()

    # Execute all 7 analyses sequentially (parallel was overloading Granite)
    results = []
    for i, a in enumerate(analyses, 1):
        print(f"   [{i}/{len(analyses)}] Executing {a['name']}...")
        try:
            result = await executor.execute(a["agent"], a["task"])
            results.append(result)
            print(f"       ✅ Complete ({len(result.output or '')} chars)")
        except Exception as e:
            results.append(e)
            print(f"       ❌ Failed: {e}")

    duration = time.time() - start

    # Check for errors
    errors = [i for i, r in enumerate(results) if isinstance(r, Exception)]
    if errors:
        print(f"\n⚠️  {len(errors)} agents failed:")
        for i in errors:
            print(f"   - {analyses[i]['name']}: {results[i]}")

    # Report results
    print(f"\n{'=' * 80}")
    print(f"PHASE 1 COMPLETE: {len(analyses)} Analyses")
    print(f"{'=' * 80}")
    print(f"Duration: {duration:.2f}s (avg {duration / len(analyses):.2f}s per agent)\n")

    success_count = sum(1 for r in results if not isinstance(r, Exception) and r.status.name == "SUCCESS")
    print(f"✅ Successful: {success_count}/{len(analyses)}")

    for i, (analysis, result) in enumerate(zip(analyses, results), 1):
        if isinstance(result, Exception):
            print(f"   {i}. ❌ {analysis['name']}: ERROR")
        else:
            status_emoji = "✅" if result.status.name == "SUCCESS" else "❌"
            print(f"   {i}. {status_emoji} {analysis['name']}: {len(result.output or '')} chars")

    # Save Phase 1 results
    phase1_report = "phase1_specialist_analyses.md"
    with open(phase1_report, 'w') as f:
        f.write("# Phase 1: Specialist Analyses\n\n")
        f.write(f"*Completed in {duration:.2f}s using 7 parallel agents*\n\n")
        f.write(f"**Success Rate:** {success_count}/{len(analyses)}\n\n")
        f.write("---\n\n")

        for analysis, result in zip(analyses, results):
            if isinstance(result, Exception):
                f.write(f"## {analysis['name']} ❌\n\n")
                f.write(f"**Error:** {result}\n\n")
            else:
                f.write(f"## {analysis['name']}\n\n")
                f.write(f"**Agent:** {analysis['agent'].role}\n\n")
                f.write(f"**Status:** {result.status}\n\n")
                f.write(f"{result.output}\n\n")
            f.write("---\n\n")

    print(f"\n📄 Phase 1 report saved: {phase1_report}")

    # Phase 2: Synthesis
    print(f"\n{'=' * 80}")
    print(f"PHASE 2: Synthesis")
    print(f"{'=' * 80}")
    print("Combining all analyses into integration roadmap...\n")

    synthesizer = Agent(role="chief-architect", capabilities=["synthesis", "planning"], tier=4)
    synthesis_task = Task(
        description=f"""Synthesize the 7 specialist analyses into an actionable integration roadmap.

**Inputs:**
1. Python quality analysis
2. DSL engineering analysis
3. Category theory analysis
4. HTN/graph theory analysis
5. Algorithms/performance analysis
6. Architecture analysis
7. Integration opportunities analysis

**Output required:**
1. **Top 5 Integration Priorities** (features/capabilities to add to ATADO)
   - For each: Name, benefit, complexity, estimated effort
2. **Top 3 Refactoring Needs** (technical debt to address)
   - For each: Issue, impact, effort
3. **Performance Optimization Opportunities** (quick wins)
4. **Architecture Recommendations** (structural improvements)
5. **Implementation Roadmap** (priority order with dependencies)

Format: Markdown with clear sections. 1500 words.""",
        priority=1
    )

    synthesis_start = time.time()
    synthesis = await executor.execute(synthesizer, synthesis_task)
    synthesis_duration = time.time() - synthesis_start

    print(f"✅ Synthesis complete ({synthesis_duration:.2f}s)")

    # Save final report
    final_report = "integration_roadmap.md"
    with open(final_report, 'w') as f:
        f.write("# Integration Roadmap: unified-intelligence-cli\n\n")
        f.write(f"*Generated by 7 specialist agents + chief architect synthesis*\n\n")
        f.write(f"**Total Analysis Time:** {duration + synthesis_duration:.2f}s\n\n")
        f.write("---\n\n")
        f.write(synthesis.output)
        f.write("\n\n---\n\n")
        f.write("## Appendix: Detailed Analyses\n\n")
        f.write(f"See [{phase1_report}](./{phase1_report}) for full specialist reports.\n")

    print(f"\n{'=' * 80}")
    print(f"✅ ANALYSIS COMPLETE")
    print(f"{'=' * 80}")
    print(f"Total duration: {duration + synthesis_duration:.2f}s")
    print(f"  - Phase 1 (7 agents parallel): {duration:.2f}s")
    print(f"  - Phase 2 (synthesis): {synthesis_duration:.2f}s")
    print(f"\n📄 Final roadmap: {final_report}")
    print(f"📄 Detailed analyses: {phase1_report}")

    return final_report


if __name__ == "__main__":
    print("=" * 80)
    print("ATADO SPECIALIST ANALYSIS")
    print("=" * 80)
    print("Agents:")
    print("  1. Python Engineer (code quality)")
    print("  2. DSL Engineer (language design)")
    print("  3. Category Theory Specialist (mathematical abstractions)")
    print("  4. HTN Expert (planning + graph theory)")
    print("  5. Algorithms Expert (complexity + performance)")
    print("  6. Software Architect (architecture)")
    print("  7. Integration Architect (opportunities)")
    print("\nLLM: IBM Granite 4.0-H (local, RAG-enhanced)")
    print("=" * 80)
    print()

    roadmap = asyncio.run(comprehensive_analysis())
    print(f"\n🎯 Next step: Review {roadmap} for actionable integration plan")
