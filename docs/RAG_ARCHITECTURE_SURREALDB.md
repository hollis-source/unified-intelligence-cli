# RAG Architecture for Adaptive Agent Learning with SurrealDB

**Design Document**: Retrieval-Augmented Generation system for autonomous agent self-optimization  
**Target System**: ATADO (autonomous-task-agent-dev-orchestration)  
**Vector Store**: SurrealDB (GraphRAG-enabled multi-model database)  
**Version**: 1.0  
**Date**: 2025-10-14

---

## Executive Summary

This document presents a comprehensive RAG architecture that enables ATADO agents to learn from execution patterns and self-optimize through adaptive knowledge retrieval. By leveraging SurrealDB's GraphRAG capabilities, we unify vector embeddings, graph relationships, and execution metrics in a single database, eliminating the complexity of multi-service architectures.

**Key Innovation**: Agents query their own execution history as a living knowledge graph, retrieving contextually relevant patterns to improve routing decisions, task planning, and orchestration strategies.

---

## 1. RAG Architecture Pattern

### 1.1 Core Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ATADO Agent System                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ TaskPlanner  │  │ TeamRouter   │  │ Orchestrator │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                  │
│         └──────────────────┼──────────────────┘                  │
│                            │                                     │
│                    ┌───────▼────────┐                           │
│                    │  RAG Retriever │ ◄─── Query Context        │
│                    └───────┬────────┘                           │
└────────────────────────────┼──────────────────────────────────┘
                             │
                    ┌────────▼─────────┐
                    │   SurrealDB      │
                    │   GraphRAG       │
                    └──────────────────┘
                    │                  │
        ┌───────────┴────┐    ┌───────┴──────────┐
        │ Vector Index   │    │  Knowledge Graph │
        │ (Embeddings)   │    │  (Relationships) │
        └────────────────┘    └──────────────────┘
```

**Data Flow**:
1. **Agent Request** → Agent needs context for decision (routing, planning, orchestration)
2. **Query Formation** → Agent constructs semantic query + graph constraints
3. **RAG Retrieval** → SurrealDB executes hybrid vector + graph search
4. **Context Injection** → Retrieved patterns augment agent prompt
5. **Execution** → Agent makes informed decision based on historical patterns
6. **Feedback Loop** → Execution result stored back to knowledge graph

### 1.2 Embedding Strategy

**What to Embed**:

| Entity Type | Embedding Source | Dimensionality | Model |
|-------------|------------------|----------------|-------|
| **Task Descriptions** | `Task.description` | 1536 | OpenAI text-embedding-3-small |
| **Agent Capabilities** | `Agent.capabilities` + `Agent.specialization` | 1536 | OpenAI text-embedding-3-small |
| **Execution Patterns** | `ExecutionResult.output` + `metadata` | 1536 | OpenAI text-embedding-3-small |
| **HTN Nodes** | `HTNNode.description` + `preconditions` | 1536 | OpenAI text-embedding-3-small |
| **DSL Workflows** | DSL source code + comments | 1536 | Code-specific model (e.g., CodeBERT) |
| **Error Patterns** | `ExecutionResult.errors` + `error_details` | 1536 | OpenAI text-embedding-3-small |

**Embedding Pipeline**:
```python
# src/adapters/rag/embedding_pipeline.py
from typing import List, Dict, Any
from openai import AsyncOpenAI
import numpy as np

class EmbeddingPipeline:
    """
    Generates embeddings for ATADO entities.

    Clean Architecture: Adapter for external embedding service.
    SRP: Single responsibility - embedding generation only.
    """

    def __init__(self, client: AsyncOpenAI, model: str = "text-embedding-3-small"):
        self.client = client
        self.model = model
        self.dimension = 1536

    async def embed_task(self, task: Task) -> np.ndarray:
        """Embed task description with metadata context."""
        text = f"{task.description} [priority={task.priority}]"
        return await self._embed_text(text)

    async def embed_execution_pattern(
        self,
        task: Task,
        agent: Agent,
        result: ExecutionResult
    ) -> np.ndarray:
        """Embed execution pattern for retrieval."""
        pattern = (
            f"Task: {task.description}\n"
            f"Agent: {agent.role} (tier={agent.tier}, domain={agent.specialization})\n"
            f"Status: {result.status.value}\n"
            f"Output: {str(result.output)[:200]}"
        )
        return await self._embed_text(pattern)

    async def _embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for text."""
        response = await self.client.embeddings.create(
            model=self.model,
            input=text
        )
        return np.array(response.data[0].embedding)
```

### 1.3 Retrieval Strategy: Hybrid Search

**Approach**: Combine semantic vector search with graph traversal for context-aware retrieval.

**Query Pattern**:
```sql
-- SurrealQL: Hybrid search for similar task execution patterns
SELECT
    execution_id,
    task_description,
    agent_role,
    success_rate,
    avg_latency,
    -- Vector similarity (semantic search)
    vector::similarity::cosine(embedding, $query_embedding) AS similarity,
    -- Graph traversal (relationship context)
    <-executed_by<-agent.capabilities AS agent_capabilities,
    ->followed_by->execution AS next_executions,
    <-part_of<-team.domain AS team_context
FROM execution_pattern
WHERE
    -- Vector search: Top 10 semantically similar patterns
    embedding <|10|> $query_embedding
    -- Graph constraints: Same domain
    AND <-executed_by<-agent<-member_of<-team.domain = $target_domain
    -- Time window: Recent patterns (last 30 days)
    AND timestamp > time::now() - 30d
ORDER BY
    similarity DESC,
    success_rate DESC
LIMIT 5;
```

**Retrieval Modes**:

1. **Semantic Search** (Vector-only):
   - Use case: Find similar tasks regardless of structure
   - Query: `embedding <|N|> $query_embedding`
   - Best for: Novel tasks, exploratory routing

2. **Graph-Based Search** (Relationship-only):
   - Use case: Find patterns within known team/domain
   - Query: `->executed_by->agent->member_of->team WHERE team.domain = $domain`
   - Best for: Domain-specific optimization

3. **Hybrid Search** (Vector + Graph):
   - Use case: Contextually relevant patterns with relationship constraints
   - Query: Combine both (as shown above)
   - Best for: Production routing decisions

### 1.4 Context Injection

**Prompt Augmentation Strategy**:

```python
# src/use_cases/rag_augmented_planner.py
from typing import List, Optional
from src.entity import Task, Agent, ExecutionContext
from src.interface import ITaskPlanner, ExecutionPlan
from src.adapters.rag import RAGRetriever

class RAGAugmentedTaskPlanner(ITaskPlanner):
    """
    Task planner enhanced with RAG retrieval.

    Retrieves similar historical execution patterns to inform planning decisions.
    """

    def __init__(
        self,
        base_planner: ITaskPlanner,
        rag_retriever: RAGRetriever,
        top_k: int = 5
    ):
        self.base_planner = base_planner
        self.rag_retriever = rag_retriever
        self.top_k = top_k

    async def create_plan(
        self,
        tasks: List[Task],
        agents: List[Agent],
        context: Optional[ExecutionContext] = None
    ) -> ExecutionPlan:
        """Create plan with RAG-augmented context."""

        # 1. Retrieve similar execution patterns
        patterns = await self.rag_retriever.retrieve_similar_patterns(
            tasks=tasks,
            agents=agents,
            top_k=self.top_k
        )

        # 2. Augment execution context with retrieved patterns
        augmented_context = self._augment_context(context, patterns)

        # 3. Delegate to base planner with enriched context
        return await self.base_planner.create_plan(
            tasks, agents, augmented_context
        )

    def _augment_context(
        self,
        context: Optional[ExecutionContext],
        patterns: List[Dict]
    ) -> ExecutionContext:
        """Inject retrieved patterns into context."""
        if context is None:
            context = ExecutionContext()

        # Add historical patterns to metadata
        context.metadata["rag_patterns"] = [
            {
                "task": p["task_description"],
                "agent": p["agent_role"],
                "success_rate": p["success_rate"],
                "avg_latency": p["avg_latency"],
                "similarity": p["similarity"]
            }
            for p in patterns
        ]

        # Generate natural language summary for LLM prompt
        context.metadata["rag_summary"] = self._generate_summary(patterns)

        return context

    def _generate_summary(self, patterns: List[Dict]) -> str:
        """Generate human-readable summary of patterns."""
        if not patterns:
            return "No historical patterns found."

        summary = "Historical execution patterns:\n"
        for i, p in enumerate(patterns, 1):
            summary += (
                f"{i}. Similar task '{p['task_description'][:50]}...' "
                f"executed by {p['agent_role']} "
                f"(success rate: {p['success_rate']:.1%}, "
                f"avg latency: {p['avg_latency']:.2f}s)\n"
            )
        return summary
```

**Prompt Template** (injected into LLM):
```
You are a task planner for a multi-agent system.

CURRENT TASK:
{task.description}

AVAILABLE AGENTS:
{agents_list}

HISTORICAL PATTERNS (RAG-retrieved):
{rag_summary}

Based on historical patterns, which agent should handle this task?
Consider success rates and latency from similar past executions.
```

---

## 2. Adaptive Learning Loop

### 2.1 Learning Cycle

```
┌─────────────────────────────────────────────────────────────┐
│                   Adaptive Learning Loop                     │
└─────────────────────────────────────────────────────────────┘

1. EXECUTE
   ├─ Agent executes task
   ├─ Metrics collected (latency, success, errors)
   └─ Result stored

2. CAPTURE
   ├─ Execution pattern extracted
   ├─ Embedding generated
   └─ Graph relationships created

3. ANALYZE
   ├─ Pattern clustering (identify common failures)
   ├─ Success rate calculation per (task_type, agent, domain)
   └─ Anomaly detection (outlier executions)

4. OPTIMIZE
   ├─ Update routing weights
   ├─ Adjust agent selection heuristics
   └─ Re-embed changed patterns

5. RETRIEVE
   ├─ Next task queries knowledge graph
   ├─ RAG retrieves optimized patterns
   └─ Cycle repeats
```

### 2.2 Patterns to Capture

**Execution Patterns**:
```python
@dataclass
class ExecutionPattern:
    """
    Captured execution pattern for learning.

    Stored in SurrealDB with vector embedding + graph edges.
    """
    execution_id: str
    timestamp: datetime

    # Task context
    task_description: str
    task_priority: int
    task_domain: str

    # Agent context
    agent_role: str
    agent_tier: int
    agent_specialization: str
    team_name: str

    # Execution metrics
    status: ExecutionStatus
    latency_seconds: float
    success: bool
    error_type: Optional[str]
    retry_count: int

    # Routing decision
    routing_domain: str
    routing_confidence: float
    was_fallback: bool

    # Vector embedding
    embedding: np.ndarray  # 1536-dim

    # Graph relationships (edges in SurrealDB)
    # ->executed_by->agent
    # ->part_of->team
    # ->followed_by->next_execution
    # <-similar_to<-execution_pattern (vector neighbors)
```

**Routing Decision Patterns**:
```python
@dataclass
class RoutingDecisionPattern:
    """
    Routing decision for learning optimal routing strategies.
    """
    decision_id: str
    timestamp: datetime

    # Input
    task_description: str
    classified_domain: str
    domain_confidence: float

    # Decision
    selected_team: str
    selected_agent: str
    routing_strategy: str  # "team", "hierarchical", "direct"

    # Outcome
    execution_success: bool
    execution_latency: float
    was_optimal: bool  # Determined by post-execution analysis

    # Learning signal
    should_reinforce: bool  # True if decision was good
    alternative_agents: List[str]  # Agents that could have handled it
```

### 2.3 Feedback Mechanism

**Reinforcement Learning Approach** (Simplified):

```python
# src/use_cases/adaptive_learning.py
from typing import List, Dict
from src.entity import ExecutionResult, Task, Agent
from src.adapters.rag import SurrealDBStore

class AdaptiveLearningEngine:
    """
    Learns from execution patterns to optimize agent selection.

    Uses success rate and latency as reward signals.
    """

    def __init__(self, db_store: SurrealDBStore):
        self.db_store = db_store
        self.learning_rate = 0.1

    async def process_execution_result(
        self,
        task: Task,
        agent: Agent,
        result: ExecutionResult,
        routing_decision: Dict
    ) -> None:
        """
        Process execution result and update knowledge graph.

        Learning signals:
        - Success → Reinforce (task_type, agent) pairing
        - Failure → Penalize pairing, explore alternatives
        - High latency → Penalize, prefer faster agents
        """

        # 1. Calculate reward signal
        reward = self._calculate_reward(result)

        # 2. Store execution pattern
        pattern = await self._create_execution_pattern(
            task, agent, result, routing_decision, reward
        )
        await self.db_store.store_pattern(pattern)

        # 3. Update routing weights (if using weighted routing)
        await self._update_routing_weights(
            task_domain=routing_decision["classified_domain"],
            agent_role=agent.role,
            reward=reward
        )

        # 4. Trigger re-embedding if pattern changed significantly
        if abs(reward) > 0.5:  # Significant success or failure
            await self._trigger_reembedding(pattern)

    def _calculate_reward(self, result: ExecutionResult) -> float:
        """
        Calculate reward signal from execution result.

        Reward function:
        - Success: +1.0
        - Failure: -1.0
        - Latency penalty: -0.1 per second over threshold
        """
        if result.status == ExecutionStatus.SUCCESS:
            base_reward = 1.0
        else:
            base_reward = -1.0

        # Latency penalty (assume 5s threshold)
        latency = result.metadata.get("latency_seconds", 0)
        latency_penalty = max(0, (latency - 5.0) * 0.1)

        return base_reward - latency_penalty

    async def _update_routing_weights(
        self,
        task_domain: str,
        agent_role: str,
        reward: float
    ) -> None:
        """
        Update routing weights using exponential moving average.

        SurrealQL:
        UPDATE routing_weight
        SET weight = weight + $learning_rate * ($reward - weight)
        WHERE domain = $task_domain AND agent = $agent_role;
        """
        query = """
        UPDATE routing_weight
        SET weight = weight + $learning_rate * ($reward - weight),
            update_count = update_count + 1,
            last_updated = time::now()
        WHERE domain = $domain AND agent = $agent
        """

        await self.db_store.execute(
            query,
            {
                "learning_rate": self.learning_rate,
                "reward": reward,
                "domain": task_domain,
                "agent": agent_role
            }
        )
```

### 2.4 Knowledge Update Strategy

**Incremental Updates** (Preferred):
- **Trigger**: After each execution (real-time learning)
- **Operation**: Insert new pattern, update routing weights
- **Cost**: Low (single embedding + graph edge creation)
- **Benefit**: Immediate learning, no batch delay

**Batch Re-embedding** (Periodic):
- **Trigger**: Daily or when pattern drift detected
- **Operation**: Re-embed all patterns with updated context
- **Cost**: High (re-embed thousands of patterns)
- **Benefit**: Captures evolving semantics (e.g., new agent capabilities)

**Hybrid Approach** (Recommended):
```python
class KnowledgeUpdateStrategy:
    """
    Hybrid update strategy: Incremental + periodic batch.
    """

    async def update_knowledge(
        self,
        pattern: ExecutionPattern,
        force_reembed: bool = False
    ) -> None:
        """
        Update knowledge graph with new pattern.

        Strategy:
        1. Always: Insert pattern with embedding (incremental)
        2. Conditionally: Re-embed related patterns if drift detected
        3. Scheduled: Full re-embedding every 7 days
        """

        # Incremental: Insert new pattern
        await self.db_store.insert_pattern(pattern)

        # Conditional: Re-embed if significant change
        if force_reembed or await self._detect_drift(pattern):
            await self._reembed_related_patterns(pattern)

        # Scheduled: Check if batch re-embedding due
        if await self._is_batch_due():
            await self._schedule_batch_reembedding()

    async def _detect_drift(self, pattern: ExecutionPattern) -> bool:
        """
        Detect if pattern semantics have drifted.

        Method: Compare embedding to cluster centroid.
        If distance > threshold, drift detected.
        """
        cluster_centroid = await self.db_store.get_cluster_centroid(
            domain=pattern.task_domain,
            agent=pattern.agent_role
        )

        distance = np.linalg.norm(pattern.embedding - cluster_centroid)
        return distance > 0.3  # Threshold (tunable)
```

---

## 3. SurrealDB Schema Design

### 3.1 Core Tables

**Execution Pattern Table**:
```sql
-- execution_pattern: Stores execution history with embeddings
DEFINE TABLE execution_pattern SCHEMAFULL;

DEFINE FIELD execution_id ON execution_pattern TYPE string;
DEFINE FIELD timestamp ON execution_pattern TYPE datetime;

-- Task context
DEFINE FIELD task_description ON execution_pattern TYPE string;
DEFINE FIELD task_priority ON execution_pattern TYPE int;
DEFINE FIELD task_domain ON execution_pattern TYPE string;

-- Agent context
DEFINE FIELD agent_role ON execution_pattern TYPE string;
DEFINE FIELD agent_tier ON execution_pattern TYPE int;
DEFINE FIELD agent_specialization ON execution_pattern TYPE option<string>;
DEFINE FIELD team_name ON execution_pattern TYPE string;

-- Execution metrics
DEFINE FIELD status ON execution_pattern TYPE string;
DEFINE FIELD latency_seconds ON execution_pattern TYPE float;
DEFINE FIELD success ON execution_pattern TYPE bool;
DEFINE FIELD error_type ON execution_pattern TYPE option<string>;
DEFINE FIELD retry_count ON execution_pattern TYPE int DEFAULT 0;

-- Routing decision
DEFINE FIELD routing_domain ON execution_pattern TYPE string;
DEFINE FIELD routing_confidence ON execution_pattern TYPE float;
DEFINE FIELD was_fallback ON execution_pattern TYPE bool DEFAULT false;

-- Vector embedding (1536-dim for OpenAI text-embedding-3-small)
DEFINE FIELD embedding ON execution_pattern TYPE array<float>;
DEFINE FIELD embedding_model ON execution_pattern TYPE string DEFAULT "text-embedding-3-small";

-- Indexes
DEFINE INDEX idx_timestamp ON execution_pattern FIELDS timestamp;
DEFINE INDEX idx_domain_agent ON execution_pattern FIELDS task_domain, agent_role;
DEFINE INDEX idx_success ON execution_pattern FIELDS success, status;

-- Vector index (HNSW for fast similarity search)
DEFINE INDEX idx_embedding ON execution_pattern FIELDS embedding HNSW DIMENSION 1536 DIST COSINE;
```

**Agent Table** (Enhanced):
```sql
-- agent: Agent metadata with capabilities embedding
DEFINE TABLE agent SCHEMAFULL;

DEFINE FIELD role ON agent TYPE string;
DEFINE FIELD tier ON agent TYPE int;
DEFINE FIELD specialization ON agent TYPE option<string>;
DEFINE FIELD capabilities ON agent TYPE array<string>;

-- Vector embedding of capabilities
DEFINE FIELD capabilities_embedding ON agent TYPE array<float>;

-- Performance metrics (aggregated)
DEFINE FIELD avg_success_rate ON agent TYPE float DEFAULT 0.0;
DEFINE FIELD avg_latency ON agent TYPE float DEFAULT 0.0;
DEFINE FIELD total_executions ON agent TYPE int DEFAULT 0;

-- Indexes
DEFINE INDEX idx_role ON agent FIELDS role UNIQUE;
DEFINE INDEX idx_tier_spec ON agent FIELDS tier, specialization;
DEFINE INDEX idx_capabilities_embedding ON agent FIELDS capabilities_embedding HNSW DIMENSION 1536 DIST COSINE;
```

**Team Table**:
```sql
-- team: Team metadata
DEFINE TABLE team SCHEMAFULL;

DEFINE FIELD name ON team TYPE string;
DEFINE FIELD domain ON team TYPE string;
DEFINE FIELD tier ON team TYPE int DEFAULT 2;

-- Performance metrics
DEFINE FIELD avg_success_rate ON team TYPE float DEFAULT 0.0;
DEFINE FIELD total_tasks_handled ON team TYPE int DEFAULT 0;

-- Indexes
DEFINE INDEX idx_name ON team FIELDS name UNIQUE;
DEFINE INDEX idx_domain ON team FIELDS domain;
```

**Routing Weight Table** (For adaptive routing):
```sql
-- routing_weight: Learned weights for (domain, agent) pairs
DEFINE TABLE routing_weight SCHEMAFULL;

DEFINE FIELD domain ON routing_weight TYPE string;
DEFINE FIELD agent ON routing_weight TYPE string;
DEFINE FIELD weight ON routing_weight TYPE float DEFAULT 0.5;
DEFINE FIELD update_count ON routing_weight TYPE int DEFAULT 0;
DEFINE FIELD last_updated ON routing_weight TYPE datetime;

-- Indexes
DEFINE INDEX idx_domain_agent ON routing_weight FIELDS domain, agent UNIQUE;
```

### 3.2 Graph Relationships (Edges)

**Execution Relationships**:
```sql
-- executed_by: execution_pattern -> agent
DEFINE TABLE executed_by SCHEMAFULL TYPE RELATION FROM execution_pattern TO agent;
DEFINE FIELD timestamp ON executed_by TYPE datetime;

-- part_of: agent -> team
DEFINE TABLE part_of SCHEMAFULL TYPE RELATION FROM agent TO team;
DEFINE FIELD joined_at ON part_of TYPE datetime;

-- followed_by: execution_pattern -> execution_pattern (temporal sequence)
DEFINE TABLE followed_by SCHEMAFULL TYPE RELATION FROM execution_pattern TO execution_pattern;
DEFINE FIELD time_delta_seconds ON followed_by TYPE float;

-- similar_to: execution_pattern -> execution_pattern (vector neighbors)
DEFINE TABLE similar_to SCHEMAFULL TYPE RELATION FROM execution_pattern TO execution_pattern;
DEFINE FIELD similarity_score ON similar_to TYPE float;
DEFINE FIELD similarity_method ON similar_to TYPE string DEFAULT "cosine";
```

### 3.3 Query Patterns

**Pattern 1: Find Similar Successful Executions**:
```sql
-- Given a new task, find similar tasks that succeeded
SELECT
    execution_id,
    task_description,
    agent_role,
    latency_seconds,
    vector::similarity::cosine(embedding, $query_embedding) AS similarity,
    <-executed_by<-agent.avg_success_rate AS agent_success_rate
FROM execution_pattern
WHERE
    embedding <|10|> $query_embedding
    AND success = true
    AND timestamp > time::now() - 30d
ORDER BY similarity DESC, latency_seconds ASC
LIMIT 5;
```

**Pattern 2: Agent Performance by Domain**:
```sql
-- Aggregate agent performance for a specific domain
SELECT
    agent_role,
    count() AS total_executions,
    math::mean(latency_seconds) AS avg_latency,
    math::sum(success) / count() AS success_rate,
    <-executed_by<-agent->part_of->team.name AS team_name
FROM execution_pattern
WHERE task_domain = $domain
GROUP BY agent_role
ORDER BY success_rate DESC, avg_latency ASC;
```

**Pattern 3: GraphRAG - Contextual Retrieval**:
```sql
-- Hybrid: Vector search + graph context
SELECT
    ep.execution_id,
    ep.task_description,
    ep.agent_role,
    ep.success,
    ep.latency_seconds,
    vector::similarity::cosine(ep.embedding, $query_embedding) AS similarity,
    -- Graph context: Agent capabilities
    <-executed_by<-agent.capabilities AS agent_capabilities,
    -- Graph context: Team domain
    <-executed_by<-agent->part_of->team.domain AS team_domain,
    -- Graph context: Next execution in sequence
    ->followed_by->execution_pattern.task_description AS next_task
FROM execution_pattern AS ep
WHERE
    -- Vector search
    ep.embedding <|15|> $query_embedding
    -- Graph constraint: Same team domain
    AND <-executed_by<-agent->part_of->team.domain = $target_domain
    -- Time window
    AND ep.timestamp > time::now() - 14d
ORDER BY similarity DESC
LIMIT 5;
```

**Pattern 4: Temporal Pattern Analysis**:
```sql
-- Find execution sequences (task A → task B patterns)
SELECT
    ep1.task_description AS first_task,
    ep2.task_description AS second_task,
    count() AS sequence_count,
    math::mean(fb.time_delta_seconds) AS avg_time_between,
    math::sum(ep2.success) / count() AS second_task_success_rate
FROM execution_pattern AS ep1
    ->followed_by AS fb
    ->execution_pattern AS ep2
WHERE
    ep1.task_domain = $domain
    AND ep1.timestamp > time::now() - 30d
GROUP BY ep1.task_description, ep2.task_description
HAVING sequence_count > 3
ORDER BY sequence_count DESC;
```

---

## 4. Agent Optimization Strategy

### 4.1 Which Agents Benefit Most from RAG?

**Priority Ranking**:

| Agent/Component | RAG Benefit | Rationale |
|-----------------|-------------|-----------|
| **1. TeamRouter** | ⭐⭐⭐⭐⭐ | Routing decisions directly benefit from historical success patterns |
| **2. TaskPlanner** | ⭐⭐⭐⭐⭐ | Planning improved by retrieving similar task decompositions |
| **3. HierarchicalRouter** | ⭐⭐⭐⭐ | Tier selection optimized by past (task, tier) performance |
| **4. HybridOrchestrator** | ⭐⭐⭐⭐ | Orchestration mode selection (SDK vs simple) learned from patterns |
| **5. HTN Planner** | ⭐⭐⭐ | HTN decomposition strategies retrieved from successful plans |
| **6. Individual Agents** | ⭐⭐ | Execution agents benefit less (task-specific, not meta-level) |

### 4.2 RAG-Enhanced Components

**TeamRouter with RAG**:
```python
# src/routing/rag_team_router.py
from typing import List
from src.entity import Task, Agent, AgentTeam
from src.routing.team_router import TeamRouter
from src.adapters.rag import RAGRetriever

class RAGTeamRouter(TeamRouter):
    """
    Team router enhanced with RAG retrieval.

    Retrieves historical routing decisions to optimize team selection.
    """

    def __init__(
        self,
        domain_classifier,
        rag_retriever: RAGRetriever,
        top_k: int = 3
    ):
        super().__init__(domain_classifier)
        self.rag_retriever = rag_retriever
        self.top_k = top_k

    def route(self, task: Task, teams: List[AgentTeam]) -> Agent:
        """
        Route task to agent using RAG-augmented decision.

        Strategy:
        1. Retrieve similar historical routing decisions
        2. Weight team selection by historical success rates
        3. Fall back to base router if no patterns found
        """

        # Retrieve similar routing patterns
        patterns = await self.rag_retriever.retrieve_routing_patterns(
            task=task,
            top_k=self.top_k
        )

        if patterns:
            # Use RAG-informed routing
            team = self._select_team_from_patterns(task, teams, patterns)
        else:
            # Fall back to base routing
            team = self._select_team(task, teams)

        # Team's internal routing (unchanged)
        agent = team.route_internally(task)

        # Record decision for future learning
        await self._record_routing_decision(task, team, agent, patterns)

        return agent

    def _select_team_from_patterns(
        self,
        task: Task,
        teams: List[AgentTeam],
        patterns: List[Dict]
    ) -> AgentTeam:
        """
        Select team based on historical patterns.

        Weighted voting: Each pattern votes for a team,
        weighted by similarity * success_rate.
        """
        team_scores = {}

        for pattern in patterns:
            team_name = pattern["target_team"]
            weight = pattern["similarity"] * pattern["success_rate"]
            team_scores[team_name] = team_scores.get(team_name, 0) + weight

        # Select team with highest score
        best_team_name = max(team_scores, key=team_scores.get)

        # Find team object
        team = next((t for t in teams if t.name == best_team_name), None)

        if team:
            logger.info(
                f"RAG-selected team: {best_team_name} "
                f"(score: {team_scores[best_team_name]:.2f})"
            )
            return team
        else:
            # Fallback if team not found
            return self._select_team(task, teams)
```

**TaskPlanner with RAG**:
```python
# src/use_cases/rag_task_planner.py
class RAGTaskPlanner(ITaskPlanner):
    """
    Task planner that retrieves similar task decompositions.
    """

    async def create_plan(
        self,
        tasks: List[Task],
        agents: List[Agent],
        context: Optional[ExecutionContext] = None
    ) -> ExecutionPlan:
        """
        Create plan using RAG-retrieved decomposition strategies.
        """

        # Retrieve similar task decompositions
        decompositions = await self.rag_retriever.retrieve_decompositions(
            tasks=tasks,
            top_k=5
        )

        # Build prompt with retrieved examples
        prompt = self._build_rag_prompt(tasks, agents, decompositions)

        # Generate plan with LLM
        llm_response = await self.text_generator.generate(prompt)

        # Parse and return plan
        return self._parse_plan(llm_response, tasks, agents)

    def _build_rag_prompt(
        self,
        tasks: List[Task],
        agents: List[Agent],
        decompositions: List[Dict]
    ) -> str:
        """
        Build prompt with RAG-retrieved examples.
        """
        prompt = "You are a task planner. Create an execution plan.\n\n"

        # Add retrieved examples
        if decompositions:
            prompt += "SIMILAR SUCCESSFUL PLANS:\n"
            for i, decomp in enumerate(decompositions, 1):
                prompt += f"\nExample {i}:\n"
                prompt += f"Task: {decomp['task_description']}\n"
                prompt += f"Plan: {decomp['execution_plan']}\n"
                prompt += f"Success Rate: {decomp['success_rate']:.1%}\n"

        # Add current task
        prompt += "\n\nCURRENT TASKS:\n"
        for task in tasks:
            prompt += f"- {task.description}\n"

        prompt += "\n\nAVAILABLE AGENTS:\n"
        for agent in agents:
            prompt += f"- {agent.role} (tier={agent.tier}, capabilities={agent.capabilities})\n"

        prompt += "\n\nCreate an execution plan based on the examples above."

        return prompt
```

### 4.3 Fine-Tuning vs RAG vs Hybrid

**Decision Matrix**:

| Approach | Pros | Cons | Best For |
|----------|------|------|----------|
| **RAG Only** | - No model training<br>- Real-time updates<br>- Explainable (show retrieved patterns) | - Retrieval latency<br>- Depends on embedding quality | - Rapid iteration<br>- Changing codebase<br>- Explainability required |
| **Fine-Tuning Only** | - Faster inference<br>- No retrieval overhead<br>- Internalized knowledge | - Expensive training<br>- Stale knowledge<br>- Requires labeled data | - Stable codebase<br>- High-volume inference<br>- Low latency critical |
| **Hybrid (RAG + Fine-Tuning)** | - Best of both worlds<br>- Fine-tuned base + fresh context | - Complex architecture<br>- Higher cost | - Production systems<br>- High accuracy required<br>- Budget available |

**Recommendation for ATADO**: **RAG Only** (Phase 1) → **Hybrid** (Phase 2)

**Rationale**:
1. **Phase 1 (RAG Only)**:
   - Codebase evolving rapidly (Week 13+)
   - Need explainability for debugging routing decisions
   - No labeled dataset yet for fine-tuning
   - Cost-effective (no training costs)

2. **Phase 2 (Hybrid)**:
   - After 6 months of execution data collected
   - Fine-tune small model (e.g., GPT-3.5) on routing decisions
   - Use RAG for edge cases and recent patterns
   - Reduce inference latency for high-volume routing

### 4.4 Metrics: Measuring Optimization Improvement

**Key Performance Indicators (KPIs)**:

| Metric | Baseline (No RAG) | Target (With RAG) | Measurement |
|--------|-------------------|-------------------|-------------|
| **Routing Accuracy** | 85% | 95% | % of tasks routed to optimal agent |
| **Task Success Rate** | 78% | 90% | % of tasks completed successfully |
| **Avg Task Latency** | 12.5s | 8.0s | Mean execution time per task |
| **Routing Confidence** | 0.65 | 0.85 | Mean confidence score of routing decisions |
| **Fallback Rate** | 15% | 5% | % of tasks requiring fallback routing |
| **Agent Utilization Balance** | 0.45 | 0.75 | Gini coefficient (0=perfect balance, 1=imbalance) |

**Measurement Strategy**:
```python
# src/adapters/rag/rag_metrics.py
from dataclasses import dataclass
from typing import List
import numpy as np

@dataclass
class RAGMetrics:
    """
    Metrics for RAG-enhanced routing performance.
    """

    # Routing metrics
    routing_accuracy: float  # % correct agent selections
    routing_confidence: float  # Mean confidence score
    fallback_rate: float  # % fallback routing

    # Execution metrics
    task_success_rate: float  # % successful executions
    avg_task_latency: float  # Mean latency (seconds)

    # Retrieval metrics
    avg_retrieval_latency: float  # RAG retrieval time
    avg_patterns_retrieved: float  # Mean # patterns per query
    retrieval_relevance: float  # Mean similarity score

    # Learning metrics
    knowledge_graph_size: int  # # execution patterns stored
    embedding_freshness: float  # Days since last re-embedding

    def calculate_improvement(self, baseline: 'RAGMetrics') -> Dict[str, float]:
        """Calculate % improvement over baseline."""
        return {
            "routing_accuracy": (self.routing_accuracy - baseline.routing_accuracy) / baseline.routing_accuracy,
            "task_success_rate": (self.task_success_rate - baseline.task_success_rate) / baseline.task_success_rate,
            "avg_task_latency": (baseline.avg_task_latency - self.avg_task_latency) / baseline.avg_task_latency,
            "fallback_rate": (baseline.fallback_rate - self.fallback_rate) / baseline.fallback_rate,
        }

class RAGMetricsCollector:
    """
    Collects and analyzes RAG performance metrics.
    """

    async def collect_metrics(
        self,
        time_window_days: int = 7
    ) -> RAGMetrics:
        """
        Collect metrics over time window.

        Queries SurrealDB for aggregated statistics.
        """

        # Query routing accuracy
        routing_accuracy = await self._calculate_routing_accuracy(time_window_days)

        # Query execution metrics
        success_rate, avg_latency = await self._calculate_execution_metrics(time_window_days)

        # Query retrieval metrics
        retrieval_metrics = await self._calculate_retrieval_metrics(time_window_days)

        # Query knowledge graph stats
        kg_size = await self._get_knowledge_graph_size()

        return RAGMetrics(
            routing_accuracy=routing_accuracy,
            routing_confidence=retrieval_metrics["avg_confidence"],
            fallback_rate=retrieval_metrics["fallback_rate"],
            task_success_rate=success_rate,
            avg_task_latency=avg_latency,
            avg_retrieval_latency=retrieval_metrics["avg_latency"],
            avg_patterns_retrieved=retrieval_metrics["avg_patterns"],
            retrieval_relevance=retrieval_metrics["avg_similarity"],
            knowledge_graph_size=kg_size,
            embedding_freshness=await self._get_embedding_freshness()
        )

    async def _calculate_routing_accuracy(self, days: int) -> float:
        """
        Calculate routing accuracy.

        Accuracy = (# optimal routings) / (# total routings)
        Optimal = task succeeded with lowest latency agent
        """
        query = """
        SELECT
            count() AS total,
            math::sum(was_optimal) AS optimal_count
        FROM routing_decision
        WHERE timestamp > time::now() - $days * 1d
        """

        result = await self.db_store.execute(query, {"days": days})

        if result[0]["total"] == 0:
            return 0.0

        return result[0]["optimal_count"] / result[0]["total"]
```

**A/B Testing Strategy**:
```python
class RAGABTest:
    """
    A/B test RAG-enhanced routing vs baseline.
    """

    def __init__(self, rag_router, baseline_router, split_ratio=0.5):
        self.rag_router = rag_router
        self.baseline_router = baseline_router
        self.split_ratio = split_ratio
        self.results = {"rag": [], "baseline": []}

    async def route_with_ab_test(
        self,
        task: Task,
        teams: List[AgentTeam]
    ) -> Agent:
        """
        Route task using A/B test.

        Randomly assign to RAG or baseline router.
        """

        # Random assignment
        use_rag = random.random() < self.split_ratio

        if use_rag:
            agent = await self.rag_router.route(task, teams)
            variant = "rag"
        else:
            agent = self.baseline_router.route(task, teams)
            variant = "baseline"

        # Record assignment for analysis
        await self._record_ab_assignment(task, agent, variant)

        return agent

    async def analyze_results(self) -> Dict:
        """
        Analyze A/B test results.

        Returns:
            Statistical significance test results
        """
        rag_success_rate = np.mean([r["success"] for r in self.results["rag"]])
        baseline_success_rate = np.mean([r["success"] for r in self.results["baseline"]])

        # Two-proportion z-test
        z_score, p_value = self._two_proportion_z_test(
            self.results["rag"],
            self.results["baseline"]
        )

        return {
            "rag_success_rate": rag_success_rate,
            "baseline_success_rate": baseline_success_rate,
            "improvement": (rag_success_rate - baseline_success_rate) / baseline_success_rate,
            "z_score": z_score,
            "p_value": p_value,
            "significant": p_value < 0.05
        }
```

---

## 5. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)

**Deliverables**:
1. ✅ SurrealDB schema design (tables, indexes, relationships)
2. ✅ Embedding pipeline (OpenAI integration)
3. ✅ Basic RAG retriever (vector search only)
4. ✅ Execution pattern capture (post-execution hook)

**Tasks**:
- [ ] Install SurrealDB locally + Cloud instance
- [ ] Define schema (execution_pattern, agent, team, routing_weight tables)
- [ ] Implement `EmbeddingPipeline` adapter
- [ ] Implement `SurrealDBStore` adapter (CRUD operations)
- [ ] Add post-execution hook to `TaskCoordinator` to capture patterns
- [ ] Write unit tests for embedding + storage

**Success Criteria**:
- 100 execution patterns stored with embeddings
- Vector search returns top-5 similar patterns in <100ms
- Schema supports all planned queries

### Phase 2: RAG Integration (Weeks 3-4)

**Deliverables**:
1. ✅ RAG-augmented TeamRouter
2. ✅ RAG-augmented TaskPlanner
3. ✅ Hybrid search (vector + graph)
4. ✅ Context injection into LLM prompts

**Tasks**:
- [ ] Implement `RAGRetriever` use case (hybrid search)
- [ ] Implement `RAGTeamRouter` (extends TeamRouter)
- [ ] Implement `RAGTaskPlanner` (extends TaskPlanner)
- [ ] Add graph relationships (executed_by, part_of, followed_by)
- [ ] Test hybrid queries (vector + graph constraints)
- [ ] Integration tests with real LLM calls

**Success Criteria**:
- RAG router achieves 90%+ routing accuracy on test set
- Hybrid search combines vector + graph in single query
- LLM prompts include 3-5 relevant historical patterns

### Phase 3: Adaptive Learning (Weeks 5-6)

**Deliverables**:
1. ✅ Adaptive learning engine
2. ✅ Routing weight updates
3. ✅ Incremental knowledge updates
4. ✅ Drift detection

**Tasks**:
- [ ] Implement `AdaptiveLearningEngine` use case
- [ ] Implement reward calculation (success + latency)
- [ ] Implement routing weight updates (exponential moving average)
- [ ] Implement drift detection (cluster centroid comparison)
- [ ] Add scheduled batch re-embedding (cron job)
- [ ] Monitor learning metrics (routing accuracy over time)

**Success Criteria**:
- Routing weights converge after 500 executions
- Drift detection triggers re-embedding for 5% of patterns
- Routing accuracy improves 10% over 2 weeks

### Phase 4: Metrics & Optimization (Weeks 7-8)

**Deliverables**:
1. ✅ RAG metrics collector
2. ✅ A/B testing framework
3. ✅ Performance dashboard
4. ✅ Optimization recommendations

**Tasks**:
- [ ] Implement `RAGMetricsCollector`
- [ ] Implement A/B testing (RAG vs baseline)
- [ ] Build Grafana dashboard (routing accuracy, latency, success rate)
- [ ] Run 2-week A/B test with 50/50 split
- [ ] Analyze results, generate optimization report
- [ ] Document learnings and best practices

**Success Criteria**:
- A/B test shows statistically significant improvement (p < 0.05)
- Dashboard visualizes all KPIs in real-time
- Optimization report identifies top 3 improvement areas

---

## 6. Data Flow Diagrams

### 6.1 Execution Pattern Capture Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Task Execution                                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ TaskCoordinator.coordinate(tasks, agents)                    │
│   ├─ TaskPlanner.create_plan()                              │
│   ├─ AgentExecutor.execute(task, agent)                     │
│   └─ ExecutionResult returned                               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Post-Execution Hook                                       │
│ AdaptiveLearningEngine.process_execution_result()            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Pattern Extraction                                        │
│   ├─ Extract: task, agent, result, routing_decision         │
│   ├─ Calculate reward: success + latency penalty            │
│   └─ Create ExecutionPattern entity                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Embedding Generation                                      │
│ EmbeddingPipeline.embed_execution_pattern()                  │
│   └─ OpenAI API: text-embedding-3-small                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Storage (SurrealDB)                                       │
│ SurrealDBStore.store_pattern()                               │
│   ├─ INSERT INTO execution_pattern                          │
│   ├─ CREATE EDGE executed_by -> agent                       │
│   ├─ CREATE EDGE part_of -> team                            │
│   └─ UPDATE routing_weight (learning)                       │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 RAG Retrieval Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. New Task Arrives                                          │
│ TeamRouter.route(task, teams)                                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Query Formation                                           │
│ RAGRetriever.retrieve_routing_patterns(task)                 │
│   ├─ Embed task description                                 │
│   ├─ Classify domain                                        │
│   └─ Build hybrid query (vector + graph)                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. SurrealDB Query                                           │
│ SELECT ... FROM execution_pattern                            │
│ WHERE embedding <|10|> $query_embedding                      │
│   AND <-executed_by<-agent->part_of->team.domain = $domain  │
│ ORDER BY similarity DESC                                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Pattern Ranking                                           │
│   ├─ Rank by: similarity * success_rate                     │
│   ├─ Filter: latency < threshold                            │
│   └─ Return top-K patterns                                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Team Selection                                            │
│ RAGTeamRouter._select_team_from_patterns()                   │
│   ├─ Weighted voting by patterns                            │
│   ├─ Select team with highest score                         │
│   └─ Fallback to base router if no patterns                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Agent Selection                                           │
│ Team.route_internally(task)                                  │
│   └─ Return selected agent                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Security & Privacy Considerations

### 7.1 Data Privacy

**Sensitive Data in Embeddings**:
- **Risk**: Task descriptions may contain sensitive information (API keys, user data)
- **Mitigation**:
  - Sanitize task descriptions before embedding (remove secrets, PII)
  - Use local embedding models for sensitive data (e.g., sentence-transformers)
  - Implement data retention policies (delete patterns after 90 days)

**Access Control**:
```sql
-- SurrealDB: Define access control for execution patterns
DEFINE SCOPE agent_scope SESSION 24h
  SIGNUP ( CREATE user SET email = $email, pass = crypto::argon2::generate($pass) )
  SIGNIN ( SELECT * FROM user WHERE email = $email AND crypto::argon2::compare(pass, $pass) );

-- Row-level security: Agents can only read their own patterns
DEFINE FIELD execution_pattern.* PERMISSIONS
  FOR select WHERE $scope = "agent_scope" AND <-executed_by<-agent.role = $auth.role;
```

### 7.2 Embedding Security

**API Key Management**:
- Store OpenAI API keys in environment variables (`.env`)
- Use separate API keys for dev/staging/production
- Rotate keys every 90 days
- Monitor API usage for anomalies

**Embedding Poisoning**:
- **Risk**: Malicious patterns injected to bias routing
- **Mitigation**:
  - Validate execution results before storing patterns
  - Implement anomaly detection (outlier embeddings)
  - Require human approval for high-impact patterns

---

## 8. Cost Analysis

### 8.1 Embedding Costs

**OpenAI text-embedding-3-small Pricing** (as of 2024):
- $0.02 per 1M tokens
- Avg task description: 50 tokens
- Cost per embedding: $0.000001

**Monthly Cost Estimate**:
| Volume | Embeddings/Month | Cost |
|--------|------------------|------|
| **Low** (1K tasks/day) | 30K | $0.03 |
| **Medium** (10K tasks/day) | 300K | $0.30 |
| **High** (100K tasks/day) | 3M | $3.00 |

**Optimization**:
- Cache embeddings for identical task descriptions
- Use smaller models for non-critical embeddings
- Batch embedding requests (up to 2048 inputs per request)

### 8.2 SurrealDB Costs

**SurrealDB Cloud Pricing** (estimated):
- **Starter**: $25/month (1GB storage, 1M queries/month)
- **Pro**: $99/month (10GB storage, 10M queries/month)
- **Enterprise**: Custom pricing

**Storage Estimate**:
| Patterns | Storage (GB) | Tier |
|----------|--------------|------|
| 10K | 0.5 | Starter |
| 100K | 5.0 | Pro |
| 1M | 50.0 | Enterprise |

**Total Monthly Cost** (Medium volume):
- Embeddings: $0.30
- SurrealDB: $99.00
- **Total**: ~$100/month

---

## 9. Alternatives Considered

### 9.1 Vector Stores Comparison

| Vector Store | Pros | Cons | Verdict |
|--------------|------|------|---------|
| **SurrealDB** | ✅ GraphRAG (vector + graph)<br>✅ Multi-model (no separate DBs)<br>✅ Real-time updates | ❌ Newer (less mature)<br>❌ Smaller community | ✅ **Selected** |
| **Pinecone** | ✅ Mature, fast<br>✅ Managed service | ❌ Vector-only (no graph)<br>❌ Expensive ($70+/month) | ❌ No graph support |
| **Weaviate** | ✅ Hybrid search<br>✅ GraphQL API | ❌ Complex setup<br>❌ No native graph DB | ❌ Overkill for use case |
| **Qdrant** | ✅ Fast, open-source<br>✅ Good Python SDK | ❌ Vector-only<br>❌ Need separate graph DB | ❌ Multi-DB complexity |
| **PostgreSQL + pgvector** | ✅ Familiar SQL<br>✅ Free | ❌ Slow for large-scale vector search<br>❌ No graph support | ❌ Performance concerns |

**Why SurrealDB**:
1. **GraphRAG**: Combines vector + graph in single query (eliminates multi-DB joins)
2. **Multi-model**: Handles OLTP, graph, vector, full-text in one system
3. **Real-time**: LIVE SELECT for streaming updates
4. **Clean Architecture**: Single database simplifies adapter layer

### 9.2 Embedding Models Comparison

| Model | Dimensions | Cost | Performance | Verdict |
|-------|------------|------|-------------|---------|
| **OpenAI text-embedding-3-small** | 1536 | $0.02/1M tokens | ⭐⭐⭐⭐ | ✅ **Selected** |
| **OpenAI text-embedding-3-large** | 3072 | $0.13/1M tokens | ⭐⭐⭐⭐⭐ | ❌ Too expensive |
| **Sentence-Transformers (all-MiniLM-L6-v2)** | 384 | Free (local) | ⭐⭐⭐ | ✅ Fallback option |
| **Cohere embed-english-v3.0** | 1024 | $0.10/1M tokens | ⭐⭐⭐⭐ | ❌ More expensive |

**Why OpenAI text-embedding-3-small**:
- Best cost/performance ratio
- 1536 dimensions (good for semantic search)
- Fast API (<100ms latency)
- Fallback to local model (Sentence-Transformers) for privacy-sensitive data

---

## 10. Future Enhancements

### 10.1 Advanced RAG Techniques

**1. Multi-Vector Retrieval**:
- Store multiple embeddings per pattern (task, agent, output)
- Retrieve based on different aspects (e.g., "similar tasks" vs "similar agents")

**2. Hierarchical Retrieval**:
- Coarse retrieval: Find relevant domain/team
- Fine retrieval: Find specific execution patterns within domain

**3. Temporal Weighting**:
- Weight recent patterns higher (exponential decay)
- Detect concept drift (task semantics changing over time)

**4. Active Learning**:
- Identify low-confidence routing decisions
- Request human feedback for labeling
- Fine-tune routing model on labeled data

### 10.2 Agent Self-Improvement

**1. Automated Hyperparameter Tuning**:
- Optimize RAG retrieval parameters (top_k, similarity threshold)
- Use Bayesian optimization to find best settings

**2. Meta-Learning**:
- Learn which retrieval strategy works best for which task types
- Adaptive retrieval (switch between vector/graph/hybrid based on task)

**3. Causal Inference**:
- Identify causal relationships (e.g., "Agent X fails on Task Y because of Z")
- Use causal graphs to improve routing decisions

### 10.3 Multi-Agent Collaboration

**1. Shared Knowledge Graph**:
- Multiple agent systems share execution patterns
- Federated learning across deployments

**2. Agent Specialization**:
- Agents learn to specialize in specific task types
- Dynamic capability updates based on performance

**3. Collaborative Filtering**:
- "Agents who handled Task A also handled Task B"
- Recommend agent pairings for multi-agent tasks

---

## 11. Conclusion

This RAG architecture provides ATADO with a powerful adaptive learning system that:

1. **Unifies Knowledge**: SurrealDB's GraphRAG eliminates multi-database complexity
2. **Learns Continuously**: Incremental updates enable real-time learning
3. **Improves Routing**: Historical patterns optimize agent selection
4. **Scales Efficiently**: Hybrid search balances accuracy and performance
5. **Maintains Explainability**: Retrieved patterns provide transparent reasoning

**Key Innovations**:
- **Single-Query GraphRAG**: Vector + graph search in one SurrealQL query
- **Adaptive Routing Weights**: Exponential moving average for continuous learning
- **Hybrid Update Strategy**: Incremental + periodic batch re-embedding
- **Multi-Level Optimization**: RAG enhances routers, planners, and orchestrators

**Next Steps**:
1. Implement Phase 1 (Foundation) - 2 weeks
2. Run pilot with 1,000 tasks - 1 week
3. Measure baseline vs RAG performance - 1 week
4. Iterate based on metrics - Ongoing

**Expected Impact**:
- **+10-15%** routing accuracy
- **+12%** task success rate
- **-35%** average task latency
- **-67%** fallback routing rate

This architecture positions ATADO as a self-optimizing autonomous system that learns from every execution, continuously improving its decision-making capabilities.

---

## Appendix A: SurrealDB Setup

### Installation

**Local Development**:
```bash
# Install SurrealDB
curl -sSf https://install.surrealdb.com | sh

# Start server
surreal start --log trace --user root --pass root memory

# Or with file storage
surreal start --log trace --user root --pass root file://data/surrealdb
```

**Docker**:
```bash
docker run --rm --pull always -p 8000:8000 \
  surrealdb/surrealdb:latest start \
  --user root --pass root memory
```

**SurrealDB Cloud**:
```bash
# Sign up at https://surrealdb.com/cloud
# Create instance, get connection string
# Example: wss://your-instance.surrealdb.cloud
```

### Python SDK

```bash
pip install surrealdb
```

```python
# src/adapters/rag/surrealdb_store.py
from surrealdb import Surreal
import asyncio

class SurrealDBStore:
    """
    Adapter for SurrealDB storage.

    Clean Architecture: Adapter for external database.
    """

    def __init__(self, url: str, namespace: str, database: str):
        self.url = url
        self.namespace = namespace
        self.database = database
        self.db = None

    async def connect(self):
        """Connect to SurrealDB."""
        self.db = Surreal()
        await self.db.connect(self.url)
        await self.db.signin({"user": "root", "pass": "root"})
        await self.db.use(self.namespace, self.database)

    async def store_pattern(self, pattern: ExecutionPattern):
        """Store execution pattern with embedding."""
        await self.db.create("execution_pattern", {
            "execution_id": pattern.execution_id,
            "timestamp": pattern.timestamp.isoformat(),
            "task_description": pattern.task_description,
            "task_priority": pattern.task_priority,
            "task_domain": pattern.task_domain,
            "agent_role": pattern.agent_role,
            "agent_tier": pattern.agent_tier,
            "agent_specialization": pattern.agent_specialization,
            "team_name": pattern.team_name,
            "status": pattern.status.value,
            "latency_seconds": pattern.latency_seconds,
            "success": pattern.success,
            "error_type": pattern.error_type,
            "retry_count": pattern.retry_count,
            "routing_domain": pattern.routing_domain,
            "routing_confidence": pattern.routing_confidence,
            "was_fallback": pattern.was_fallback,
            "embedding": pattern.embedding.tolist(),
            "embedding_model": "text-embedding-3-small"
        })

    async def hybrid_search(
        self,
        query_embedding: np.ndarray,
        domain: str,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Hybrid search: vector + graph.

        Returns top-k similar patterns from same domain.
        """
        query = """
        SELECT
            execution_id,
            task_description,
            agent_role,
            success,
            latency_seconds,
            vector::similarity::cosine(embedding, $query_embedding) AS similarity,
            <-executed_by<-agent.capabilities AS agent_capabilities,
            <-executed_by<-agent->part_of->team.domain AS team_domain
        FROM execution_pattern
        WHERE
            embedding <|$top_k|> $query_embedding
            AND <-executed_by<-agent->part_of->team.domain = $domain
            AND timestamp > time::now() - 30d
        ORDER BY similarity DESC
        LIMIT $top_k
        """

        result = await self.db.query(query, {
            "query_embedding": query_embedding.tolist(),
            "domain": domain,
            "top_k": top_k
        })

        return result[0]["result"]
```

---

## Appendix B: Example Queries

### Query 1: Find Best Agent for Task Type

```sql
-- Find agent with highest success rate for specific task type
SELECT
    agent_role,
    count() AS total_executions,
    math::sum(success) / count() AS success_rate,
    math::mean(latency_seconds) AS avg_latency,
    <-executed_by<-agent.tier AS agent_tier
FROM execution_pattern
WHERE
    task_description CONTAINS $task_keyword
    AND timestamp > time::now() - 30d
GROUP BY agent_role
HAVING total_executions > 10
ORDER BY success_rate DESC, avg_latency ASC
LIMIT 3;
```

### Query 2: Identify Failing Patterns

```sql
-- Find common failure patterns
SELECT
    task_domain,
    agent_role,
    error_type,
    count() AS failure_count,
    math::mean(retry_count) AS avg_retries
FROM execution_pattern
WHERE
    success = false
    AND timestamp > time::now() - 7d
GROUP BY task_domain, agent_role, error_type
HAVING failure_count > 5
ORDER BY failure_count DESC;
```

### Query 3: Agent Utilization Heatmap

```sql
-- Agent utilization by hour of day
SELECT
    agent_role,
    time::hour(timestamp) AS hour,
    count() AS task_count,
    math::mean(latency_seconds) AS avg_latency
FROM execution_pattern
WHERE timestamp > time::now() - 7d
GROUP BY agent_role, hour
ORDER BY agent_role, hour;
```

---

## Appendix C: References

**Papers**:
1. Lewis et al. (2020). "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
2. Gao et al. (2023). "Retrieval-Augmented Generation for Large Language Models: A Survey"
3. Edge et al. (2024). "From Local to Global: A Graph RAG Approach to Query-Focused Summarization"

**SurrealDB Documentation**:
- GraphRAG Guide: https://surrealdb.com/solutions/graph-rag
- Vector Search: https://surrealdb.com/docs/surrealql/functions/vector
- HNSW Index: https://surrealdb.com/docs/surrealql/statements/define/indexes

**ATADO Documentation**:
- Week 12 Team Architecture: `docs/WEEK_12_TEAM_ARCHITECTURE.md`
- Week 13 Metrics: `docs/WEEK_13_METRICS.md`
- Clean Architecture: `docs/CLEAN_ARCHITECTURE.md`

---

**Document Version**: 1.0
**Last Updated**: 2025-10-14
**Author**: ATADO Research Team
**Status**: Design Complete - Ready for Implementation
