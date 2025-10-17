# RAG Integration Action Plan

**Date**: 2025-10-17  
**Status**: Ready to Execute  
**Timeline**: 8 weeks  
**Priority**: HIGH

---

## Executive Summary

This action plan details the 8-week RAG integration to transform the agent system from static routing (78% success) to adaptive, learning-based routing (90%+ success).

**Goal**: Enable agents to learn from execution patterns and self-optimize routing decisions.

---

## Week 1-2: Foundation

### Objectives

- Set up SurrealDB Cloud Pro
- Implement execution pattern storage
- Create vector embeddings pipeline
- Build basic retrieval system

---

### Day 1-2: SurrealDB Setup

**Tasks**:
1. Create SurrealDB Cloud Pro account ($99.80/month)
2. Set up database schema
3. Configure authentication
4. Test connectivity

**Schema Design**:
```sql
-- Execution patterns
DEFINE TABLE execution_patterns SCHEMAFULL;
DEFINE FIELD task_description ON execution_patterns TYPE string;
DEFINE FIELD agent_role ON execution_patterns TYPE string;
DEFINE FIELD team_name ON execution_patterns TYPE string;
DEFINE FIELD success ON execution_patterns TYPE bool;
DEFINE FIELD latency_ms ON execution_patterns TYPE number;
DEFINE FIELD timestamp ON execution_patterns TYPE datetime;
DEFINE FIELD embedding ON execution_patterns TYPE array;

-- Agent performance
DEFINE TABLE agent_performance SCHEMAFULL;
DEFINE FIELD agent_role ON agent_performance TYPE string;
DEFINE FIELD total_tasks ON agent_performance TYPE number;
DEFINE FIELD successful_tasks ON agent_performance TYPE number;
DEFINE FIELD avg_latency_ms ON agent_performance TYPE number;
DEFINE FIELD success_rate ON agent_performance TYPE number;

-- Routing decisions
DEFINE TABLE routing_decisions SCHEMAFULL;
DEFINE FIELD task_id ON routing_decisions TYPE string;
DEFINE FIELD task_description ON routing_decisions TYPE string;
DEFINE FIELD selected_agent ON routing_decisions TYPE string;
DEFINE FIELD selected_team ON routing_decisions TYPE string;
DEFINE FIELD confidence ON routing_decisions TYPE number;
DEFINE FIELD timestamp ON routing_decisions TYPE datetime;

-- Vector index for similarity search
DEFINE INDEX embedding_idx ON execution_patterns FIELDS embedding MTREE DIMENSION 1536;
```

**Deliverable**: SurrealDB operational with schema

---

### Day 3-4: Execution Pattern Recorder

**Tasks**:
1. Create `ExecutionPatternRecorder` use case
2. Integrate with `TaskCoordinator`
3. Implement OpenAI embeddings
4. Store first 100 patterns

**Implementation**:
```python
# src/use_cases/execution_pattern_recorder.py

from dataclasses import dataclass
from typing import Optional
import openai
from src.interface.pattern_recorder import IPatternRecorder
from src.adapters.rag.surrealdb_adapter import SurrealDBAdapter

@dataclass
class ExecutionPatternRecorder(IPatternRecorder):
    """Records execution patterns for RAG learning."""
    
    db: SurrealDBAdapter
    openai_client: openai.Client
    
    async def record_pattern(
        self,
        task_description: str,
        agent_role: str,
        team_name: str,
        success: bool,
        latency_ms: float
    ) -> None:
        """Record execution pattern with embedding."""
        
        # Generate embedding
        embedding = await self._generate_embedding(task_description)
        
        # Store pattern
        await self.db.create("execution_patterns", {
            "task_description": task_description,
            "agent_role": agent_role,
            "team_name": team_name,
            "success": success,
            "latency_ms": latency_ms,
            "timestamp": datetime.now(),
            "embedding": embedding
        })
    
    async def _generate_embedding(self, text: str) -> list:
        """Generate OpenAI embedding."""
        response = await self.openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
```

**Integration with TaskCoordinator**:
```python
# src/use_cases/task_coordinator.py

async def coordinate(self, tasks, agents, context, enable_rag=False):
    """Coordinate with optional RAG recording."""
    
    results = await self._execute_plan(plan, tasks, agents, context)
    
    # Record patterns if RAG enabled
    if enable_rag and self.pattern_recorder:
        for result in results:
            await self.pattern_recorder.record_pattern(
                task_description=result.task.description,
                agent_role=result.agent.role,
                team_name=result.team.name,
                success=result.status == ExecutionStatus.SUCCESS,
                latency_ms=result.execution_time * 1000
            )
    
    return results
```

**Deliverable**: 100+ patterns stored with embeddings

---

### Day 5: Validation

**Tasks**:
1. Verify patterns stored correctly
2. Test vector search performance (<100ms)
3. Validate embedding quality
4. Team review

**Validation Queries**:
```sql
-- Count patterns
SELECT count() FROM execution_patterns;

-- Test vector search
SELECT * FROM execution_patterns
WHERE embedding <|1536|> $query_embedding
LIMIT 5;

-- Agent performance
SELECT agent_role, success_rate 
FROM agent_performance
ORDER BY success_rate DESC;
```

**Success Criteria**:
- ✅ 100+ patterns stored
- ✅ Vector search <100ms
- ✅ Embeddings generated correctly

---

## Week 3-4: RAG-Enhanced Routing

### Objectives

- Integrate RAG with TeamRouter
- Implement hybrid search (vector + graph)
- Add LLM-based routing with historical context
- Build feedback loop

---

### Day 6-8: RAG Team Router

**Tasks**:
1. Create `RAGTeamRouter`
2. Implement hybrid search
3. Add LLM-based routing
4. Test with historical patterns

**Implementation**:
```python
# src/routing/rag_team_router.py

from dataclasses import dataclass
from typing import List, Dict, Any
from src.routing.team_router import TeamRouter
from src.adapters.rag.surrealdb_adapter import SurrealDBAdapter
from src.interface.text_generator import ITextGenerator

@dataclass
class RAGTeamRouter(TeamRouter):
    """Team router enhanced with RAG."""
    
    db: SurrealDBAdapter
    llm: ITextGenerator
    
    async def route(self, task, teams):
        """Route with RAG context."""
        
        # 1. Retrieve similar patterns (vector search)
        patterns = await self._retrieve_similar_patterns(task.description)
        
        # 2. Get agent performance (graph query)
        performance = await self._get_agent_performance(patterns)
        
        # 3. LLM-based routing with context
        team = await self._llm_route_with_context(
            task, teams, patterns, performance
        )
        
        return team
    
    async def _retrieve_similar_patterns(self, task_desc: str, k=5):
        """Retrieve k most similar patterns."""
        
        # Generate embedding
        embedding = await self._generate_embedding(task_desc)
        
        # Vector search
        query = """
        SELECT task_description, agent_role, team_name, success, latency_ms
        FROM execution_patterns
        WHERE embedding <|1536|> $embedding
        LIMIT $k
        """
        
        return await self.db.query(query, {
            "embedding": embedding,
            "k": k
        })
    
    async def _llm_route_with_context(self, task, teams, patterns, performance):
        """LLM-based routing with historical context."""
        
        prompt = f"""
        Route this task to the best team based on historical patterns.
        
        Task: {task.description}
        
        Available teams: {[t.name for t in teams]}
        
        Historical patterns (similar tasks):
        {self._format_patterns(patterns)}
        
        Agent performance:
        {self._format_performance(performance)}
        
        Select the best team and explain why.
        """
        
        response = await self.llm.generate(prompt)
        
        # Parse response and select team
        selected_team = self._parse_team_selection(response, teams)
        
        return selected_team
```

**Deliverable**: RAG routing achieves 85%+ accuracy

---

### Day 9-10: Feedback Loop

**Tasks**:
1. Implement routing feedback collection
2. Add confidence scoring
3. Build re-ranking mechanism
4. Test feedback loop

**Implementation**:
```python
# src/use_cases/routing_feedback_collector.py

async def collect_feedback(self, routing_decision, execution_result):
    """Collect feedback on routing decision."""
    
    # Calculate confidence
    confidence = self._calculate_confidence(
        routing_decision,
        execution_result
    )
    
    # Store decision with outcome
    await self.db.create("routing_decisions", {
        "task_id": execution_result.task_id,
        "task_description": execution_result.task.description,
        "selected_agent": routing_decision.agent.role,
        "selected_team": routing_decision.team.name,
        "confidence": confidence,
        "success": execution_result.status == ExecutionStatus.SUCCESS,
        "timestamp": datetime.now()
    })
    
    # Update agent performance
    await self._update_agent_performance(
        routing_decision.agent.role,
        execution_result
    )
```

**Deliverable**: Feedback loop operational

---

## Week 5-6: Adaptive Learning

### Objectives

- Implement routing weight optimization
- Add drift detection
- Build performance feedback loop
- Create learning rate scheduler

---

### Day 11-13: Weight Optimization

**Tasks**:
1. Create `RoutingWeightOptimizer`
2. Implement Bayesian optimization
3. Add A/B testing framework
4. Test convergence

**Implementation**:
```python
# src/use_cases/routing_weight_optimizer.py

from scipy.optimize import minimize
import numpy as np

class RoutingWeightOptimizer:
    """Optimize routing weights using Bayesian optimization."""
    
    def __init__(self, db: SurrealDBAdapter):
        self.db = db
        self.weights = self._initialize_weights()
    
    async def optimize(self, n_iterations=100):
        """Optimize weights over n iterations."""
        
        for i in range(n_iterations):
            # Get recent patterns
            patterns = await self._get_recent_patterns(limit=1000)
            
            # Calculate loss
            loss = self._calculate_loss(patterns, self.weights)
            
            # Update weights
            self.weights = self._update_weights(loss)
            
            # Log progress
            if i % 10 == 0:
                accuracy = await self._calculate_accuracy(patterns)
                print(f"Iteration {i}: accuracy={accuracy:.2%}")
    
    def _calculate_loss(self, patterns, weights):
        """Calculate routing loss."""
        
        total_loss = 0
        for pattern in patterns:
            # Predict team
            predicted_team = self._predict_team(pattern, weights)
            
            # Compare with actual
            actual_team = pattern["team_name"]
            
            # Add to loss if mismatch
            if predicted_team != actual_team:
                total_loss += 1
        
        return total_loss / len(patterns)
```

**Deliverable**: Weights converge after 500 executions

---

### Day 14-15: Drift Detection

**Tasks**:
1. Implement drift detector
2. Add re-embedding triggers
3. Build monitoring dashboard
4. Test drift scenarios

**Implementation**:
```python
# src/adapters/rag/drift_detector.py

class DriftDetector:
    """Detect distribution drift in task patterns."""
    
    def __init__(self, threshold=0.1):
        self.threshold = threshold
        self.baseline_distribution = None
    
    async def detect_drift(self, recent_patterns):
        """Detect if task distribution has drifted."""
        
        # Calculate current distribution
        current_dist = self._calculate_distribution(recent_patterns)
        
        # Compare with baseline
        if self.baseline_distribution is None:
            self.baseline_distribution = current_dist
            return False
        
        # KL divergence
        drift_score = self._kl_divergence(
            self.baseline_distribution,
            current_dist
        )
        
        # Trigger re-embedding if drift detected
        if drift_score > self.threshold:
            await self._trigger_reembedding()
            self.baseline_distribution = current_dist
            return True
        
        return False
```

**Deliverable**: Drift detection triggers re-embedding

---

## Week 7-8: Production & Monitoring

### Objectives

- A/B testing (RAG vs baseline)
- Performance monitoring dashboard
- Documentation and runbooks
- Production deployment

---

### Day 16-18: A/B Testing

**Tasks**:
1. Implement A/B test framework
2. Run baseline vs RAG comparison
3. Collect statistical significance
4. Analyze results

**A/B Test Design**:
```python
# 50/50 split
if random.random() < 0.5:
    # Control: Baseline routing
    team = baseline_router.route(task, teams)
else:
    # Treatment: RAG routing
    team = rag_router.route(task, teams)

# Record which variant
record_variant(task_id, variant="control" or "treatment")
```

**Success Criteria**:
- ✅ RAG routing shows statistically significant improvement (p < 0.05)
- ✅ +10% success rate over baseline
- ✅ -20% latency reduction

---

### Day 19-20: Monitoring Dashboard

**Tasks**:
1. Create Grafana dashboard
2. Add KPI visualizations
3. Set up alerts
4. Document dashboard

**KPIs to Monitor**:
- Task success rate (overall, per agent, per team)
- Routing accuracy
- Average latency
- Cache hit rate
- Drift detection events
- Re-embedding frequency

**Deliverable**: Dashboard operational

---

## Success Metrics

| Metric | Baseline | Target | Status |
|--------|----------|--------|--------|
| Success Rate | 78% | 90%+ | TBD |
| Latency | 12.5s | 8-10s | TBD |
| Fallback Rate | 15% | <5% | TBD |
| Routing Accuracy | 85% | 95%+ | TBD |

---

## Budget

**Infrastructure** (8 weeks):
- SurrealDB Cloud Pro: $99.80/month × 2 = $199.60
- OpenAI embeddings: $10/month × 2 = $20
- **Total**: $219.60

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| SurrealDB performance | Benchmark early (Day 2) |
| OpenAI rate limits | Batch embeddings, cache |
| Learning not converging | Bayesian optimization, tuning |
| Integration complexity | Phased rollout, A/B testing |

---

## Next Steps

**This Week**:
1. Decision: Approve RAG integration
2. Budget: Approve $220
3. Team: Assign backend engineer
4. Kickoff: Review this action plan

**Week 1 Day 1**:
- Create SurrealDB account
- Set up schema
- Test connectivity

---

**Status**: Ready to Execute  
**Timeline**: 8 weeks  
**Budget**: $220  
**Expected ROI**: Positive within 3 months

