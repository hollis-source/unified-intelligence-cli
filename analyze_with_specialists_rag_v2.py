"""
Multi-Agent Codebase Analysis with 7 Specialists + RAG V2

Comprehensive analysis using:
- 5 specialist agents (Python, DSL, Category Theory, HTN, Algorithms)
- 2 generalist agents (Software Architect, Integration Architect)
- IBM Granite 4.0-H LLM (local, $0 cost)
- RAG V2 (fixed event loop issues with lazy initialization)

Workflow:
  Phase 1: 7 agents analyze different domains in parallel (30-60s each)
  Phase 2: Chief Architect synthesizes into integration roadmap (30s)

Output:
  - phase1_specialist_analyses_rag_v2.md (detailed analyses)
  - integration_roadmap_rag_v2.md (actionable plan with priorities)

Usage:
    python analyze_with_specialists_rag_v2.py

Expected duration: 60-90 seconds total (with RAG context injection)
"""

import asyncio
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.adapters.llm.granite_adapter_v2 import GraniteAdapterV2
from src.adapters.llm.rag_config import RAGConfig
from src.adapters.agent.llm_executor import LLMAgentExecutor
from src.entity import Agent, Task
from src.interface import LLMConfig
from specialist_agents import create_specialist_agents


async def comprehensive_analysis():
    """7-agent comprehensive codebase analysis with RAG V2."""

    print("=" * 80)
    print("COMPREHENSIVE CODEBASE ANALYSIS WITH RAG V2")
    print("Using 7 specialized agents + Granite + RAG (event loop fixed)")
    print("=" * 80)
    print()

    # Setup RAG configuration (lazy initialization - no event loop issues)
    print("Initializing RAG configuration...")
    rag_config = RAGConfig(
        db_url="ws://localhost:8000",
        db_namespace="atado",
        database="rag",
        db_user="root",
        db_password="root",
        embedding_model="sentence-transformers/all-mpnet-base-v2",
        embedding_provider="sentence-transformers",
        top_k=3,
        similarity_threshold=0.5,
        snippet_max_length=800
    )
    print(f"  ✅ RAG Config: {rag_config}")
    print()

    # Setup Granite with RAG V2 (300s timeout, lazy RAG)
    print("Initializing Granite with RAG V2...")
    granite = GraniteAdapterV2(
        enable_rag=True,
        rag_config=rag_config,
        timeout=300
    )
    executor = LLMAgentExecutor(
        llm_provider=granite,
        default_config=LLMConfig(temperature=0.7, max_tokens=1000),
        enable_cache=True,
        enable_ultrathink=False
    )
    print("  ✅ Granite ready (RAG will initialize on first use)")
    print()

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

**Output:** Detailed report with specific file:line references and improvement recommendations."""
            ),
            "id": "python_quality_analysis"
        },

        # 2. DSL Analysis
        {
            "agent": specialists["dsl_engineer"],
            "task": Task(
                description="""Analyze the DSL (Domain-Specific Language) implementation:

**Focus areas:**
1. Grammar completeness (src/dsl/grammar/)
2. Parser robustness (error handling in src/dsl/adapters/parser.py)
3. DSL expressiveness (what workflows are easy/hard to express?)
4. Compiler optimizations (src/dsl/adapters/htn_compiler.py)
5. Type system coverage (src/dsl/types/)
6. Missing language features or primitives

**Output:** Analysis with concrete examples from the grammar and suggestions for DSL improvements."""
            ),
            "id": "dsl_analysis"
        },

        # 3. Category Theory Analysis
        {
            "agent": specialists["category_theory"],
            "task": Task(
                description="""Analyze category theory implementation:

**Focus areas:**
1. Morphism composition correctness (src/entity/category_theory/)
2. Functor implementations
3. Category laws enforcement (identity, associativity)
4. Workflow morphisms (src/entity/category_theory/workflow_morphism.py)
5. Type safety in composition
6. Missing categorical abstractions

**Output:** Assessment of mathematical correctness and practical usability."""
            ),
            "id": "category_theory_analysis"
        },

        # 4. HTN & Graph Analysis
        {
            "agent": specialists["htn_expert"],
            "task": Task(
                description="""Analyze HTN (Hierarchical Task Network) and graph algorithms:

**Focus areas:**
1. HTN decomposition strategies (src/entity/htn/)
2. Graph traversal algorithms (src/entity/graph/)
3. Topological sort correctness
4. Task planning efficiency (src/use_cases/task_planner.py)
5. Cycle detection and handling
6. Performance bottlenecks

**Output:** Technical analysis with complexity analysis and optimization suggestions."""
            ),
            "id": "htn_graph_analysis"
        },

        # 5. Algorithms & Performance
        {
            "agent": specialists["algorithms_expert"],
            "task": Task(
                description="""Analyze algorithms and performance across the codebase:

**Focus areas:**
1. Time complexity of critical paths
2. Memory usage patterns
3. Caching strategies (LLM cache, result caching)
4. Concurrency & parallelism (parallel agent execution)
5. I/O bottlenecks
6. Scalability limits

**Output:** Performance report with profiling recommendations and optimization targets."""
            ),
            "id": "algorithms_performance_analysis"
        },

        # 6. Software Architecture Review
        {
            "agent": specialists["software_architect"],
            "task": Task(
                description="""Review overall software architecture:

**Focus areas:**
1. Clean Architecture adherence (entities, use cases, adapters, interfaces)
2. Dependency inversion and boundaries
3. Module coupling and cohesion
4. Interface design quality (src/interface/)
5. Factory patterns usage
6. Testability and extensibility

**Output:** Architectural assessment with specific file references and refactoring suggestions."""
            ),
            "id": "architecture_analysis"
        },

        # 7. Integration Opportunities
        {
            "agent": specialists["integration_architect"],
            "task": Task(
                description="""Identify integration opportunities and gaps:

**Focus areas:**
1. Root-level .py files not integrated into ATADO
2. Scripts in scripts/ directory that could become agent capabilities
3. Features implemented but not exposed to agents
4. External tools/APIs not yet integrated
5. Priority-ranked integration roadmap
6. Quick wins vs long-term integrations

**Output:** Prioritized list of integration opportunities with effort estimates."""
            ),
            "id": "integration_opportunities"
        },
    ]

    # Phase 1: Parallel specialist analyses
    print("=" * 80)
    print("PHASE 1: SPECIALIST ANALYSES (7 agents in parallel)")
    print("=" * 80)
    print()

    phase1_start = time.time()
    results = []

    # Execute all analyses in parallel
    async def run_analysis(analysis):
        agent = analysis["agent"]
        task = analysis["task"]
        analysis_id = analysis["id"]

        print(f"Starting: {analysis_id} ({agent.name})...")
        start = time.time()

        try:
            result = await executor.execute(agent, task)
            duration = time.time() - start
            print(f"  ✅ Completed: {analysis_id} in {duration:.1f}s")
            return {
                "id": analysis_id,
                "agent": agent.name,
                "result": result,
                "duration": duration,
                "status": result.status
            }
        except Exception as e:
            duration = time.time() - start
            print(f"  ❌ Failed: {analysis_id} after {duration:.1f}s - {e}")
            return {
                "id": analysis_id,
                "agent": agent.name,
                "result": None,
                "duration": duration,
                "status": "ERROR",
                "error": str(e)
            }

    results = await asyncio.gather(*[run_analysis(a) for a in analyses])

    phase1_duration = time.time() - phase1_start
    successful = sum(1 for r in results if r["status"] == "SUCCESS")

    print()
    print(f"Phase 1 complete: {successful}/{len(results)} analyses succeeded in {phase1_duration:.1f}s")
    print()

    # Write Phase 1 results
    with open("phase1_specialist_analyses_rag_v2.md", "w") as f:
        f.write("# Phase 1: Specialist Analyses (RAG V2)\n\n")
        f.write(f"*Completed in {phase1_duration:.2f}s using 7 parallel agents*\n\n")
        f.write(f"**Success Rate:** {successful}/{len(results)}\n\n")
        f.write("---\n\n")

        for result in results:
            f.write(f"## {result['id']}\n\n")
            f.write(f"**Agent:** {result['agent']}\n\n")
            f.write(f"**Status:** {result['status']}\n\n")

            if result.get("error"):
                f.write(f"Error: {result['error']}\n\n")
            elif result["result"]:
                f.write(f"{result['result'].output}\n\n")

            f.write("---\n\n")

    print("Phase 1 results written to: phase1_specialist_analyses_rag_v2.md")
    print()

    # Phase 2: Chief architect synthesis
    print("=" * 80)
    print("PHASE 2: INTEGRATION ROADMAP SYNTHESIS")
    print("=" * 80)
    print()

    phase2_start = time.time()

    # Aggregate all analysis outputs for synthesis
    all_analyses = "\n\n".join([
        f"=== {r['id']} ===\n{r['result'].output if r['result'] else 'ERROR'}"
        for r in results
    ])

    synthesis_task = Task(
        description=f"""Based on the 7 specialist analyses below, synthesize a comprehensive integration roadmap.

**Specialist Analyses:**

{all_analyses}

---

**Your Task:**
Create a prioritized integration roadmap with:
1. High-impact quick wins (1-2 days effort)
2. Medium-term enhancements (1-2 weeks)
3. Long-term architectural improvements (1+ months)
4. For each item: specific files to modify, expected benefit, effort estimate

**Output Format:**
- Executive summary (3-5 sentences)
- Quick wins list (prioritized)
- Medium-term roadmap
- Long-term vision

Be specific, reference actual file paths, and provide actionable recommendations."""
    )

    print("Running chief architect synthesis...")
    synthesis_start = time.time()

    try:
        synthesis_result = await executor.execute(
            specialists["software_architect"],  # Chief architect
            synthesis_task
        )
        synthesis_duration = time.time() - synthesis_start
        print(f"  ✅ Synthesis complete in {synthesis_duration:.1f}s")

        # Write integration roadmap
        with open("integration_roadmap_rag_v2.md", "w") as f:
            f.write("# Integration Roadmap: unified-intelligence-cli (RAG V2)\n\n")
            f.write("*Generated by 7 specialist agents + chief architect synthesis*\n\n")
            f.write(f"**Total Analysis Time:** {phase1_duration + synthesis_duration:.2f}s\n\n")
            f.write("---\n\n")
            f.write(synthesis_result.output)
            f.write("\n\n---\n\n")
            f.write("## Appendix: Detailed Analyses\n\n")
            f.write("See [phase1_specialist_analyses_rag_v2.md](./phase1_specialist_analyses_rag_v2.md) for full specialist reports.\n")

        print()
        print("Integration roadmap written to: integration_roadmap_rag_v2.md")

    except Exception as e:
        print(f"  ❌ Synthesis failed: {e}")

    phase2_duration = time.time() - phase2_start
    total_duration = phase1_duration + phase2_duration

    print()
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"Total time: {total_duration:.1f}s")
    print(f"Phase 1 (specialists): {phase1_duration:.1f}s")
    print(f"Phase 2 (synthesis): {phase2_duration:.1f}s")
    print()
    print("Output files:")
    print("  - phase1_specialist_analyses_rag_v2.md")
    print("  - integration_roadmap_rag_v2.md")
    print()


if __name__ == "__main__":
    asyncio.run(comprehensive_analysis())
