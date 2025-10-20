# RAG Architecture Pattern for Adaptive Agent Learning

**Context**: Python autonomous agent system (HTN planning, multi-agent teams)  
**Goal**: Agents learn from execution patterns to self-optimize  
**Focus**: Architecture patterns and data flow (NOT implementation)

---

## Executive Summary

This document defines the **RAG (Retrieval-Augmented Generation) architecture pattern** for enabling adaptive learning in the autonomous-task-agent-dev-orchestration (ATADO) system. The pattern leverages codebase embeddings and execution history to inform routing, planning, and agent selection decisions.

**Key Design Principles**:
1. **Embedding Granularity**: Multi-level (entity, use case, execution pattern)
2. **Retrieval Strategy**: Hybrid (semantic + graph-based + metadata filtering)
3. **Context Injection**: Strategic placement in TaskPlanner and TeamRouter
4. **Clean Architecture**: RAG as adapter layer, preserving DIP and SRP

---

## 1. Embedding Granularity Strategy

### 1.1 What to Embed

The system embeds **three distinct layers** aligned with Clean Architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    EMBEDDING LAYERS                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Layer 1: CODEBASE ENTITIES (Static Knowledge)              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ • Agent definitions (role, capabilities, tier)      │    │
│  │ • Task entities (HTNNode, Task, dependencies)       │    │
│  │ • Team structures (domain, routing logic)           │    │
│  │ • DSL workflows (functors, compositions)            │    │
│  │                                                      │    │
│  │ Granularity: Function/Class level                   │    │
│  │ Update Frequency: On code changes (incremental)     │    │
│  │ Storage: SurrealDB `code_entity` table              │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  Layer 2: USE CASE PATTERNS (Behavioral Knowledge)          │
│  ┌────────────────────────────────────────────────────┐    │
│  │ • Routing decisions (task → domain → team → agent) │    │
│  │ • Planning strategies (parallel groups, tiers)      │    │
│  │ • Agent selection logic (capability matching)       │    │
│  │ • HTN decomposition patterns                        │    │
│  │                                                      │    │
│  │ Granularity: Method/Algorithm level                 │    │
│  │ Update Frequency: On logic changes                  │    │
│  │ Storage: SurrealDB `optimization_pattern` table     │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  Layer 3: EXECUTION LOGS (Empirical Knowledge)              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ • Task description + domain + agent + outcome       │    │
│  │ • Success/failure patterns                          │    │
│  │ • Latency metrics                                   │    │
│  │ • Error patterns                                    │    │
│  │                                                      │    │
│  │ Granularity: Per-execution record                   │    │
│  │ Update Frequency: Real-time (post-execution)        │    │
│  │ Storage: SurrealDB `execution_log` table            │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Embedding Content Format

**Layer 1 (Codebase Entities)**:
```python
# Example: Agent entity embedding
content = f"""
Agent: {agent.role}
Capabilities: {', '.join(agent.capabilities)}
Tier: {agent.tier} ({tier_description})
Specialization: {agent.specialization}
Parent: {agent.parent_agent}

Docstring:
{agent_class_docstring}

Usage Context:
{extract_usage_examples_from_tests()}
"""
```

**Layer 2 (Use Case Patterns)**:
```python
# Example: Routing pattern embedding
content = f"""
Pattern: Team-based routing for {domain} domain
Strategy: {routing_strategy_description}
Keywords: {domain_keywords}
Success Rate: {historical_success_rate}

Code Snippet:
{routing_method_source_code}

When to Use:
{pattern_applicability_rules}
"""
```

**Layer 3 (Execution Logs)**:
```python
# Example: Execution log embedding
content = f"""
Task: {task.description}
Domain: {classified_domain}
Routed To: {team.name} → {agent.role}
Outcome: {'SUCCESS' if success else 'FAILURE'}
Latency: {latency_seconds}s

Output Excerpt:
{output[:500]}

Error Context:
{error_details if failure else 'N/A'}
"""
```

### 1.3 Granularity Trade-offs

| Granularity | Pros | Cons | Recommendation |
|-------------|------|------|----------------|
| **File-level** | Simple, fast indexing | Too coarse, loses context | ❌ Not recommended |
| **Class-level** | Captures entity semantics | Misses method-specific logic | ✅ Use for Layer 1 (entities) |
| **Method-level** | Precise behavioral matching | Higher storage cost | ✅ Use for Layer 2 (use cases) |
| **Line-level** | Maximum precision | Fragmentation, noise | ❌ Too granular |
| **Execution-level** | Empirical learning | Requires runtime data | ✅ Use for Layer 3 (logs) |

**Chosen Strategy**: **Hybrid multi-level granularity**
- Layer 1: Class-level (entities)
- Layer 2: Method-level (use cases)
- Layer 3: Execution-level (runtime logs)

---

## 2. Retrieval Strategy Comparison

### 2.1 Strategy Matrix

| Strategy | Strengths | Weaknesses | Use Case in ATADO |
|----------|-----------|------------|-------------------|
| **Semantic (Vector-only)** | Captures intent similarity | Misses structural relationships | Initial task classification |
| **Hybrid (Vector + Metadata)** | Balances semantics + filters | Requires schema design | Routing decisions (domain + success rate) |
| **Graph-based** | Preserves dependencies | Complex queries, slower | HTN decomposition, workflow optimization |
| **Keyword (BM25)** | Fast, explainable | Brittle, no semantic understanding | Fallback for exact matches |

### 2.2 Recommended Hybrid Strategy

**Architecture**:
```
┌─────────────────────────────────────────────────────────────┐
│              HYBRID RETRIEVAL PIPELINE                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Step 1: SEMANTIC SEARCH (Vector Similarity)                │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Input: Task description embedding                   │    │
│  │ Query: Cosine similarity in vector space            │    │
│  │ Output: Top-K candidates (K=20-50)                  │    │
│  │                                                      │    │
│  │ SurrealDB Query:                                    │    │
│  │   SELECT * FROM execution_log                       │    │
│  │   WHERE embedding <|> $query_vector                 │    │
│  │   ORDER BY similarity DESC                          │    │
│  │   LIMIT 50                                          │    │
│  └────────────────────────────────────────────────────┘    │
│                          ↓                                   │
│  Step 2: METADATA FILTERING (Structured Constraints)        │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Filters:                                            │    │
│  │ • Domain match (exact or related)                   │    │
│  │ • Success = true (learn from successes)             │    │
│  │ • Latency < threshold (performance filter)          │    │
│  │ • Recency (prefer recent patterns)                  │    │
│  │                                                      │    │
│  │ SurrealDB Query:                                    │    │
│  │   ... WHERE task_domain IN $domains                 │    │
│  │       AND success = true                            │    │
│  │       AND latency_seconds < 10.0                    │    │
│  │       AND timestamp > $cutoff_date                  │    │
│  └────────────────────────────────────────────────────┘    │
│                          ↓                                   │
│  Step 3: GRAPH TRAVERSAL (Relationship Expansion)           │
│  ┌────────────────────────────────────────────────────┐    │
│  │ For HTN/workflow tasks:                             │    │
│  │ • Traverse dependency edges                         │    │
│  │ • Find related subtasks                             │    │
│  │ • Discover composition patterns                     │    │
│  │                                                      │    │
│  │ SurrealDB Query:                                    │    │
│  │   SELECT * FROM execution_log                       │    │
│  │   WHERE id IN (                                     │    │
│  │     SELECT ->depends_on->execution_log FROM $ids    │    │
│  │   )                                                 │    │
│  └────────────────────────────────────────────────────┘    │
│                          ↓                                   │
│  Step 4: RERANKING (Relevance Scoring)                      │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Weighted scoring:                                   │    │
│  │ • Semantic similarity: 40%                          │    │
│  │ • Success rate: 30%                                 │    │
│  │ • Recency: 20%                                      │    │
│  │ • Latency (inverse): 10%                            │    │
│  │                                                      │    │
│  │ Final Score = 0.4*sim + 0.3*success + 0.2*recency  │    │
│  │               - 0.1*normalized_latency              │    │
│  └────────────────────────────────────────────────────┘    │
│                          ↓                                   │
│  Output: Top-5 most relevant patterns                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Strategy Selection by Use Case

| Component | Primary Strategy | Fallback | Rationale |
|-----------|------------------|----------|-----------|
| **TeamRouter** | Hybrid (semantic + domain filter) | Keyword (domain exact match) | Balance intent understanding with domain constraints |
| **TaskPlanner** | Graph-based (dependency traversal) | Semantic (similar plans) | HTN decomposition requires structural awareness |
| **AgentSelector** | Hybrid (semantic + capability filter) | Metadata (capability exact match) | Match task requirements to agent capabilities |
| **HTN Decomposition** | Graph-based (composition patterns) | Semantic (similar workflows) | Preserve category theory semantics |

---

## 3. Context Injection Points

### 3.1 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  RAG-AUGMENTED PIPELINE                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐                                           │
│  │  User Task   │                                           │
│  └──────┬───────┘                                           │
│         │                                                    │
│         ↓                                                    │
│  ┌──────────────────────────────────────────────────┐      │
│  │  INJECTION POINT 1: TeamRouter.route()           │      │
│  ├──────────────────────────────────────────────────┤      │
│  │  RAG Query: "Similar routing decisions"          │      │
│  │  Retrieval: execution_log (task_domain match)    │      │
│  │  Context: Top-5 successful routings              │      │
│  │                                                   │      │
│  │  Decision Logic:                                 │      │
│  │  1. Base classification (DomainClassifier)       │      │
│  │  2. RAG-informed weighting (success rates)       │      │
│  │  3. Final team selection                         │      │
│  └──────────────────┬───────────────────────────────┘      │
│                     │                                        │
│                     ↓                                        │
│  ┌──────────────────────────────────────────────────┐      │
│  │  INJECTION POINT 2: TaskPlanner.create_plan()    │      │
│  ├──────────────────────────────────────────────────┤      │
│  │  RAG Query: "Similar task decompositions"        │      │
│  │  Retrieval: optimization_pattern (HTN patterns)  │      │
│  │  Context: Parallel grouping strategies           │      │
│  │                                                   │      │
│  │  Decision Logic:                                 │      │
│  │  1. LLM-based planning (existing)                │      │
│  │  2. RAG-augmented prompt (inject patterns)       │      │
│  │  3. Validate against historical success          │      │
│  └──────────────────┬───────────────────────────────┘      │
│                     │                                        │
│                     ↓                                        │
│  ┌──────────────────────────────────────────────────┐      │
│  │  INJECTION POINT 3: AgentExecutor.execute()      │      │
│  ├──────────────────────────────────────────────────┤      │
│  │  RAG Query: "Similar task executions"            │      │
│  │  Retrieval: execution_log (agent_role match)     │      │
│  │  Context: Error patterns, optimization hints     │      │
│  │                                                   │      │
│  │  Decision Logic:                                 │      │
│  │  1. Execute task (existing)                      │      │
│  │  2. Log execution pattern (capture)              │      │
│  │  3. Update embeddings (async)                    │      │
│  └──────────────────┬───────────────────────────────┘      │
│                     │                                        │
│                     ↓                                        │
│  ┌──────────────────────────────────────────────────┐      │
│  │  INJECTION POINT 4: HTNNode.decompose()          │      │
│  ├──────────────────────────────────────────────────┤      │
│  │  RAG Query: "Similar workflow decompositions"    │      │
│  │  Retrieval: code_entity (HTN patterns)           │      │
│  │  Context: Category theory compositions           │      │
│  │                                                   │      │
│  │  Decision Logic:                                 │      │
│  │  1. Default decomposition (existing)             │      │
│  │  2. RAG-suggested optimizations (graph-based)    │      │
│  │  3. Apply morphism transformations               │      │
│  └──────────────────────────────────────────────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Injection Point Details

#### 3.2.1 TeamRouter RAG Integration

**Location**: `src/routing/team_router.py::TeamRouter.route()`

**Current Flow**:
```python
def route(self, task: Task, teams: List[AgentTeam]) -> Agent:
    # Phase 1: Domain classification (keyword-based)
    domain = self.domain_classifier.classify(task)

    # Phase 2: Team selection (domain mapping)
    team = self._select_team(task, teams)

    # Phase 3: Internal routing
    agent = team.route_internally(task)

    return agent
```

**RAG-Augmented Flow**:
```python
def route(self, task: Task, teams: List[AgentTeam]) -> Agent:
    # Phase 1: Base classification
    domain = self.domain_classifier.classify(task)

    # Phase 2: RAG retrieval (NEW)
    similar_routings = await self.rag_retriever.retrieve_routing_patterns(
        task_description=task.description,
        domain=domain,
        top_k=5
    )

    # Phase 3: RAG-informed team selection (ENHANCED)
    team = self._select_team_with_rag(
        task=task,
        teams=teams,
        base_domain=domain,
        historical_patterns=similar_routings
    )

    # Phase 4: Internal routing (unchanged)
    agent = team.route_internally(task)

    return agent

def _select_team_with_rag(
    self,
    task: Task,
    teams: List[AgentTeam],
    base_domain: str,
    historical_patterns: List[Dict]
) -> AgentTeam:
    """
    Select team using weighted combination of:
    1. Base domain classification (40%)
    2. Historical success rates (40%)
    3. Latency optimization (20%)
    """
    # Calculate team scores
    team_scores = {}
    for team in teams:
        # Base score from domain match
        base_score = 1.0 if team.domain == base_domain else 0.5

        # RAG score from historical patterns
        rag_score = self._calculate_rag_score(team, historical_patterns)

        # Combined score
        team_scores[team.name] = 0.4 * base_score + 0.6 * rag_score

    # Select highest scoring team
    best_team = max(teams, key=lambda t: team_scores[t.name])
    return best_team

def _calculate_rag_score(
    self,
    team: AgentTeam,
    patterns: List[Dict]
) -> float:
    """
    Calculate RAG-based score from historical patterns.

    Scoring:
    - Success rate: 60%
    - Recency: 20%
    - Latency (inverse): 20%
    """
    team_patterns = [p for p in patterns if p['target_team'] == team.name]

    if not team_patterns:
        return 0.5  # Neutral score for unseen teams

    # Success rate
    success_rate = sum(p['success'] for p in team_patterns) / len(team_patterns)

    # Recency (exponential decay)
    avg_age_days = sum(p['age_days'] for p in team_patterns) / len(team_patterns)
    recency_score = math.exp(-avg_age_days / 30)  # 30-day half-life

    # Latency (inverse, normalized)
    avg_latency = sum(p['latency_seconds'] for p in team_patterns) / len(team_patterns)
    latency_score = 1.0 / (1.0 + avg_latency / 10.0)  # Normalize to [0, 1]

    return 0.6 * success_rate + 0.2 * recency_score + 0.2 * latency_score
```

**Benefits**:
- **Adaptive**: Learns from successful routings over time
- **Explainable**: Scores are transparent and debuggable
- **Fallback-safe**: Defaults to base classification if no patterns found

---

#### 3.2.2 TaskPlanner RAG Integration

**Location**: `src/use_cases/task_planner.py::TaskPlannerUseCase.create_plan()`

**Current Flow**:
```python
async def create_plan(
    self,
    tasks: List[Task],
    agents: List[Agent],
    context: Optional[ExecutionContext] = None
) -> ExecutionPlan:
    # LLM-based planning
    llm_response = await self._invoke_llm_planner(tasks, agents)
    plan = self._parse_llm_response(llm_response, tasks, agents)

    return plan
```

**RAG-Augmented Flow**:
```python
async def create_plan(
    self,
    tasks: List[Task],
    agents: List[Agent],
    context: Optional[ExecutionContext] = None
) -> ExecutionPlan:
    # RAG retrieval: Similar planning scenarios (NEW)
    similar_plans = await self.rag_retriever.retrieve_planning_patterns(
        tasks=tasks,
        top_k=3
    )

    # Augment LLM prompt with RAG context (ENHANCED)
    augmented_prompt = self._build_rag_augmented_prompt(
        tasks=tasks,
        agents=agents,
        historical_plans=similar_plans
    )

    # LLM-based planning with RAG context
    llm_response = await self._invoke_llm_planner_with_context(
        prompt=augmented_prompt,
        tasks=tasks,
        agents=agents
    )

    plan = self._parse_llm_response(llm_response, tasks, agents)

    return plan

def _build_rag_augmented_prompt(
    self,
    tasks: List[Task],
    agents: List[Agent],
    historical_plans: List[Dict]
) -> str:
    """
    Build LLM prompt augmented with RAG-retrieved planning patterns.

    Prompt Structure:
    1. Task descriptions (existing)
    2. Agent capabilities (existing)
    3. Historical planning patterns (NEW)
    4. Success metrics from patterns (NEW)
    """
    base_prompt = self._build_base_prompt(tasks, agents)

    if not historical_plans:
        return base_prompt

    rag_context = "## Historical Planning Patterns\n\n"
    rag_context += "Learn from these successful task decompositions:\n\n"

    for i, pattern in enumerate(historical_plans, 1):
        rag_context += f"### Pattern {i} (Success Rate: {pattern['success_rate']:.1%})\n"
        rag_context += f"**Tasks**: {pattern['task_summary']}\n"
        rag_context += f"**Parallel Groups**: {pattern['parallel_groups']}\n"
        rag_context += f"**Tier Strategy**: {pattern['tier_strategy']}\n"
        rag_context += f"**Latency**: {pattern['avg_latency']:.2f}s\n\n"

    return f"{base_prompt}\n\n{rag_context}"
```

**Benefits**:
- **Informed Planning**: LLM learns from historical decomposition strategies
- **Performance Optimization**: Prioritizes patterns with low latency
- **Tier-Aware**: Preserves hierarchical delegation patterns

---

#### 3.2.3 HTNNode RAG Integration

**Location**: `src/entity/htn/htn_node.py::HTNNode.decompose()`

**Current Flow**:
```python
def decompose(
    self,
    state: Dict[str, Any],
    decomposition_fn: Optional[Callable] = None
) -> List["HTNNode"]:
    # Default decomposition
    if self.is_primitive():
        return [self]

    # Recursive decomposition
    decomposed = []
    for subtask in self.subtasks:
        decomposed.extend(subtask.decompose(state, decomposition_fn))

    return decomposed
```

**RAG-Augmented Flow**:
```python
def decompose(
    self,
    state: Dict[str, Any],
    decomposition_fn: Optional[Callable] = None,
    rag_retriever: Optional[RAGRetriever] = None  # NEW
) -> List["HTNNode"]:
    # RAG retrieval: Similar HTN decompositions (NEW)
    if rag_retriever:
        similar_htns = await rag_retriever.retrieve_htn_patterns(
            task_id=self.task_id,
            description=self.description,
            top_k=3
        )

        # Apply RAG-suggested optimizations
        if similar_htns:
            optimized_fn = self._create_rag_optimized_decomposer(similar_htns)
            decomposition_fn = decomposition_fn or optimized_fn

    # Default decomposition (existing logic)
    if self.is_primitive():
        return [self]

    # Use custom or RAG-optimized decomposition
    if decomposition_fn:
        return decomposition_fn(self, state)

    # Recursive decomposition
    decomposed = []
    for subtask in self.subtasks:
        decomposed.extend(
            subtask.decompose(state, decomposition_fn, rag_retriever)
        )

    return decomposed

def _create_rag_optimized_decomposer(
    self,
    patterns: List[Dict]
) -> Callable:
    """
    Create decomposition function optimized by RAG patterns.

    Optimizations:
    1. Reorder subtasks for better parallelization
    2. Apply category theory morphisms (flatten, simplify)
    3. Prune redundant nodes
    """
    def optimized_decomposer(node: HTNNode, state: Dict) -> List[HTNNode]:
        # Extract optimization hints from patterns
        best_pattern = max(patterns, key=lambda p: p['success_rate'])

        # Apply morphism transformations
        if best_pattern.get('apply_flatten'):
            from src.entity.category_theory import WorkflowMorphism
            flatten_morphism = WorkflowMorphism.create_flatten()
            node = flatten_morphism(node)

        # Reorder for parallelization
        if best_pattern.get('parallel_order'):
            node.subtasks = self._reorder_for_parallelism(
                node.subtasks,
                best_pattern['parallel_order']
            )

        # Default decomposition with optimizations applied
        return node.subtasks if not node.is_primitive() else [node]

    return optimized_decomposer
```

**Benefits**:
- **Workflow Optimization**: Learns optimal decomposition strategies
- **Category Theory Aware**: Applies morphisms based on historical success
- **Parallelization**: Reorders subtasks for better concurrency

---

## 4. RAG Pattern Diagram

### 4.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RAG-AUGMENTED ATADO SYSTEM                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                      PRESENTATION LAYER (CLI)                       │    │
│  │  ┌──────────────────────────────────────────────────────────────┐  │    │
│  │  │  src/main.py: Task submission, result display                │  │    │
│  │  └──────────────────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    ↓                                         │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    USE CASE LAYER (Business Logic)                  │    │
│  │  ┌──────────────────────────────────────────────────────────────┐  │    │
│  │  │  TaskCoordinator                                             │  │    │
│  │  │  ├─ coordinate() ──→ TaskPlanner.create_plan()              │  │    │
│  │  │  │                   ↑ RAG INJECTION POINT 2                 │  │    │
│  │  │  │                   │ (Planning patterns)                   │  │    │
│  │  │  └─ execute_plan() ──→ AgentExecutor.execute()              │  │    │
│  │  │                        ↑ RAG INJECTION POINT 3               │  │    │
│  │  │                        │ (Execution patterns)                │  │    │
│  │  └──────────────────────────────────────────────────────────────┘  │    │
│  │  ┌──────────────────────────────────────────────────────────────┐  │    │
│  │  │  TeamRouter                                                  │  │    │
│  │  │  └─ route() ──→ DomainClassifier + RAG                      │  │    │
│  │  │                 ↑ RAG INJECTION POINT 1                      │  │    │
│  │  │                 │ (Routing patterns)                         │  │    │
│  │  └──────────────────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    ↓                                         │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    ENTITY LAYER (Domain Models)                     │    │
│  │  ┌──────────────────────────────────────────────────────────────┐  │    │
│  │  │  Agent, Task, AgentTeam, HTNNode                             │  │    │
│  │  │  └─ HTNNode.decompose() ──→ RAG-optimized decomposition      │  │    │
│  │  │                              ↑ RAG INJECTION POINT 4          │  │    │
│  │  │                              │ (HTN patterns)                 │  │    │
│  │  └──────────────────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    ↓                                         │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    ADAPTER LAYER (External Systems)                 │    │
│  │  ┌──────────────────────────────────────────────────────────────┐  │    │
│  │  │  RAG SUBSYSTEM (NEW)                                         │  │    │
│  │  │  ├─ EmbeddingPipeline (sentence-transformers/OpenAI)         │  │    │
│  │  │  ├─ SurrealDBStore (vector + graph storage)                  │  │    │
│  │  │  ├─ CodebaseIndexer (AST extraction, incremental updates)    │  │    │
│  │  │  └─ RAGRetriever (hybrid retrieval orchestrator)             │  │    │
│  │  └──────────────────────────────────────────────────────────────┘  │    │
│  │  ┌──────────────────────────────────────────────────────────────┐  │    │
│  │  │  LLM Providers (OpenAI, Anthropic, Grok, local)              │  │    │
│  │  └──────────────────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    ↓                                         │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    INFRASTRUCTURE LAYER (Storage)                   │    │
│  │  ┌──────────────────────────────────────────────────────────────┐  │    │
│  │  │  SurrealDB                                                   │  │    │
│  │  │  ├─ code_entity (codebase embeddings)                        │  │    │
│  │  │  ├─ execution_log (runtime patterns)                         │  │    │
│  │  │  ├─ optimization_pattern (use case patterns)                 │  │    │
│  │  │  └─ agent_learning (hypotheses, confidence scores)           │  │    │
│  │  └──────────────────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Data Flow Sequence

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    RAG RETRIEVAL & LEARNING CYCLE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PHASE 1: TASK SUBMISSION                                                   │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  User submits task: "Implement OAuth2 authentication"              │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    ↓                                         │
│  PHASE 2: RAG RETRIEVAL (Parallel)                                          │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────┐│    │
│  │  │ Routing Patterns    │  │ Planning Patterns   │  │ Code Patterns││    │
│  │  │ (execution_log)     │  │ (optimization_pat.) │  │ (code_entity)││    │
│  │  │                     │  │                     │  │              ││    │
│  │  │ Query: "OAuth2"     │  │ Query: "auth impl"  │  │ Query: "auth"││    │
│  │  │ Filter: backend     │  │ Filter: tier 2/3    │  │ Filter: .py  ││    │
│  │  │ Top-K: 5            │  │ Top-K: 3            │  │ Top-K: 10    ││    │
│  │  └─────────────────────┘  └─────────────────────┘  └─────────────┘│    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    ↓                                         │
│  PHASE 3: CONTEXT INJECTION                                                 │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  TeamRouter receives:                                              │    │
│  │  • Base domain: "backend"                                          │    │
│  │  • RAG patterns: [                                                 │    │
│  │      {team: "Backend", agent: "backend-specialist", success: 0.95},│    │
│  │      {team: "Backend", agent: "backend-lead", success: 0.88}       │    │
│  │    ]                                                               │    │
│  │  Decision: Route to Backend Team → backend-specialist (95% success)│    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    ↓                                         │
│  PHASE 4: EXECUTION                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  AgentExecutor.execute()                                           │    │
│  │  • Agent: backend-specialist                                       │    │
│  │  • RAG context: Similar OAuth2 implementations                     │    │
│  │  • LLM prompt augmented with code patterns                         │    │
│  │  • Execution: SUCCESS (latency: 3.2s)                              │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    ↓                                         │
│  PHASE 5: PATTERN CAPTURE (Async)                                           │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  RAGTaskCoordinator.capture_execution_pattern()                    │    │
│  │  1. Extract output excerpt (first 500 chars)                       │    │
│  │  2. Generate embedding (EmbeddingPipeline)                         │    │
│  │  3. Store in SurrealDB:                                            │    │
│  │     • task_description: "Implement OAuth2 authentication"          │    │
│  │     • task_domain: "backend"                                       │    │
│  │     • agent_role: "backend-specialist"                             │    │
│  │     • success: true                                                │    │
│  │     • latency_seconds: 3.2                                         │    │
│  │     • embedding: [0.12, -0.34, ..., 0.56] (384-dim)                │    │
│  │  4. Update agent_learning table (confidence scores)                │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    ↓                                         │
│  PHASE 6: ADAPTIVE LEARNING                                                 │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  Next similar task benefits from this execution:                   │    │
│  │  • Routing: Higher confidence in backend-specialist                │    │
│  │  • Planning: Learns OAuth2 decomposition strategy                  │    │
│  │  • Execution: Reuses successful code patterns                      │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Retrieval Strategy Comparison (Detailed)

### 5.1 Semantic Search (Vector-Only)

**Mechanism**: Cosine similarity in embedding space

**Pros**:
- ✅ Captures semantic intent (e.g., "OAuth2" ≈ "authentication" ≈ "login")
- ✅ Handles synonyms and paraphrasing
- ✅ Fast with approximate nearest neighbor (ANN) indexes
- ✅ Language-agnostic (works across natural language and code)

**Cons**:
- ❌ Ignores structural relationships (dependencies, composition)
- ❌ No domain constraints (may retrieve irrelevant but similar text)
- ❌ Sensitive to embedding model quality
- ❌ "Semantic drift" (similar text, different context)

**Use Cases in ATADO**:
- Initial task classification (broad intent matching)
- Code snippet retrieval (find similar functions)
- Error pattern matching (similar error messages)

**Example Query**:
```python
# Retrieve similar task descriptions
query_embedding = await embedder.embed_text("Implement OAuth2 authentication")
results = await db.search_similar_execution(
    query_embedding,
    top_k=10,
    similarity_threshold=0.7
)
# Returns: Tasks about "login", "JWT", "session management", etc.
```

---

### 5.2 Hybrid Search (Vector + Metadata)

**Mechanism**: Semantic search + structured filtering

**Pros**:
- ✅ Balances semantic understanding with domain constraints
- ✅ Filters out irrelevant results (e.g., wrong domain, failed executions)
- ✅ Supports complex queries (semantic + temporal + performance)
- ✅ Explainable (can trace why a result was retrieved)

**Cons**:
- ❌ Requires schema design (metadata fields must be predefined)
- ❌ More complex query logic (vector + SQL)
- ❌ Potential for over-filtering (too strict constraints)

**Use Cases in ATADO**:
- **Routing decisions** (semantic + domain filter)
- **Planning** (semantic + tier filter + success rate)
- **Agent selection** (semantic + capability filter)

**Example Query**:
```python
# Retrieve successful backend routing decisions
query_embedding = await embedder.embed_text("Implement OAuth2 authentication")
results = await db.query("""
    SELECT * FROM execution_log
    WHERE embedding <|> $query_vector
      AND task_domain = 'backend'
      AND success = true
      AND latency_seconds < 10.0
      AND timestamp > $cutoff_date
    ORDER BY similarity DESC
    LIMIT 5
""", {
    "query_vector": query_embedding.tolist(),
    "cutoff_date": (datetime.now() - timedelta(days=90)).isoformat()
})
# Returns: Only successful backend tasks from last 90 days
```

---

### 5.3 Graph-Based Search

**Mechanism**: Traverse dependency edges in knowledge graph

**Pros**:
- ✅ Preserves structural relationships (HTN hierarchy, task dependencies)
- ✅ Discovers transitive patterns (A → B → C)
- ✅ Supports category theory semantics (composition, morphisms)
- ✅ Enables workflow optimization (find parallel paths)

**Cons**:
- ❌ Slower than vector search (graph traversal complexity)
- ❌ Requires explicit relationship modeling (edges must be defined)
- ❌ Less effective for unstructured queries
- ❌ Complex query syntax (graph query languages)

**Use Cases in ATADO**:
- **HTN decomposition** (find subtask patterns)
- **Workflow optimization** (discover parallel execution paths)
- **Dependency analysis** (trace task chains)
- **Category theory operations** (composition, functor application)

**Example Query**:
```python
# Find all subtasks of successful OAuth2 implementations
results = await db.query("""
    SELECT * FROM execution_log
    WHERE id IN (
        SELECT ->depends_on->execution_log FROM (
            SELECT id FROM execution_log
            WHERE task_description CONTAINS 'OAuth2'
              AND success = true
        )
    )
    ORDER BY latency_seconds ASC
    LIMIT 10
""")
# Returns: Subtasks like "setup JWT", "configure middleware", etc.
```

---

### 5.4 Keyword Search (BM25)

**Mechanism**: Term frequency-inverse document frequency (TF-IDF) ranking

**Pros**:
- ✅ Fast and deterministic
- ✅ Explainable (exact keyword matches)
- ✅ No embedding model required
- ✅ Works well for exact technical terms (e.g., "OAuth2", "JWT")

**Cons**:
- ❌ No semantic understanding (misses synonyms)
- ❌ Brittle to typos and variations
- ❌ Requires manual keyword engineering
- ❌ Poor for natural language queries

**Use Cases in ATADO**:
- **Fallback** when vector search fails
- **Exact match** for technical terms (library names, error codes)
- **Debugging** (find exact error messages)

**Example Query**:
```python
# Exact match for "OAuth2" in task descriptions
results = await db.query("""
    SELECT * FROM execution_log
    WHERE task_description CONTAINS 'OAuth2'
    ORDER BY timestamp DESC
    LIMIT 10
""")
# Returns: Only tasks with exact "OAuth2" keyword
```

---


