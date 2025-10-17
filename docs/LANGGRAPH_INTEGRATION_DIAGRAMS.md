# LangGraph Integration Architecture Diagrams

**Visual reference for understanding the integration**

---

## 1. Current System Architecture (Before LangGraph)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLI Layer                                   │
│                          (src/main.py)                                   │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Composition Root                                 │
│                      (src/composition.py)                                │
│  - Wires dependencies                                                    │
│  - Creates orchestrator via factory                                      │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      OrchestrationFactory                                │
│                (src/factories/orchestration_factory.py)                  │
│                                                                           │
│  create_orchestrator(mode) → IAgentCoordinator                          │
│    ├─ "simple"  → TaskCoordinatorUseCase                                │
│    ├─ "hybrid"  → HybridOrchestrator                                    │
│    └─ "openai-agents" → OpenAIAgentsSDKAdapter                          │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                 ┌───────────────┼───────────────┐
                 ▼               ▼               ▼
        ┌────────────────┐ ┌─────────────┐ ┌──────────────┐
        │ TaskCoordinator│ │   Hybrid    │ │  OpenAI SDK  │
        │   UseCase      │ │Orchestrator │ │   Adapter    │
        └────────┬───────┘ └──────┬──────┘ └──────┬───────┘
                 │                │                │
                 └────────────────┼────────────────┘
                                  ▼
                 ┌────────────────────────────────┐
                 │   IAgentCoordinator Interface  │
                 │   coordinate(tasks, agents)    │
                 └────────────────┬───────────────┘
                                  │
                  ┌───────────────┼───────────────┐
                  ▼               ▼               ▼
         ┌────────────────┐ ┌──────────┐ ┌──────────────┐
         │  TaskPlanner   │ │  Agent   │ │    Team      │
         │   UseCase      │ │ Executor │ │   Router     │
         └────────────────┘ └──────────┘ └──────────────┘
```

---

## 2. With LangGraph Integration (After)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      OrchestrationFactory                                │
│                                                                           │
│  create_orchestrator(mode) → IAgentCoordinator                          │
│    ├─ "simple"     → TaskCoordinatorUseCase                             │
│    ├─ "hybrid"     → HybridOrchestrator                                 │
│    ├─ "openai-agents" → OpenAIAgentsSDKAdapter                          │
│    └─ "langgraph"  → LangGraphOrchestrator  ← NEW!                      │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────┬──────────────┐
         ▼                       ▼                   ▼              ▼
┌────────────────┐      ┌─────────────┐    ┌──────────────┐  ┌──────────────┐
│ TaskCoordinator│      │   Hybrid    │    │  OpenAI SDK  │  │  LangGraph   │
│   UseCase      │      │Orchestrator │    │   Adapter    │  │ Orchestrator │
└────────────────┘      └─────────────┘    └──────────────┘  └──────┬───────┘
                                                                     │
                                                                     ▼
                                              ┌──────────────────────────────┐
                                              │  State Conversion Layer      │
                                              │  ExecutionContext ↔ GraphState│
                                              └──────────────┬───────────────┘
                                                             │
                                                             ▼
                                              ┌──────────────────────────────┐
                                              │   LangGraph StateGraph       │
                                              │   - Nodes (agents)           │
                                              │   - Edges (routing)          │
                                              │   - Checkpointing            │
                                              │   - Human-in-loop            │
                                              └──────────────┬───────────────┘
                                                             │
                                         ┌───────────────────┼───────────────┐
                                         ▼                   ▼               ▼
                                    ┌─────────┐        ┌─────────┐    ┌─────────┐
                                    │ Agent 1 │        │ Agent 2 │    │ Agent N │
                                    │  Node   │        │  Node   │    │  Node   │
                                    └────┬────┘        └────┬────┘    └────┬────┘
                                         │                  │              │
                                         └──────────────────┼──────────────┘
                                                            ▼
                                              ┌──────────────────────────────┐
                                              │   Our AgentExecutor          │
                                              │   (reuses existing logic)    │
                                              └──────────────────────────────┘
```

---

## 3. LangGraph Orchestrator Internal Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    LangGraphOrchestrator.coordinate()                    │
│                                                                           │
│  Input: tasks, agents, context                                           │
│  Output: List[ExecutionResult]                                           │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  1. Build Graph        │
                    │  _build_graph(agents)  │
                    └────────┬───────────────┘
                             │
                             ▼
        ┌────────────────────────────────────────────┐
        │  2. Create StateGraph                      │
        │     - Define GraphState schema             │
        │     - Add supervisor node                  │
        │     - Add agent nodes                      │
        │     - Add edges (routing logic)            │
        │     - Compile graph                        │
        └────────┬───────────────────────────────────┘
                 │
                 ▼
    ┌────────────────────────────────────────────────┐
    │  3. For each task:                             │
    │     - Convert to GraphState                    │
    │     - Execute graph.ainvoke()                  │
    │     - Convert result to ExecutionResult        │
    └────────┬───────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────┐
│  4. Return List[ExecutionResult]                   │
└────────────────────────────────────────────────────┘
```

---

## 4. State Conversion Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Our ExecutionContext                             │
│  {                                                                        │
│    session_id: "abc123",                                                 │
│    history: [{"role": "user", "content": "task"}],                      │
│    llm_state: {"temperature": 0.7},                                     │
│    user_data: {"user_id": "user1"}                                      │
│  }                                                                        │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 │ execution_context_to_langgraph_state()
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         LangGraph GraphState                             │
│  {                                                                        │
│    messages: [{"role": "user", "content": "task"}],                     │
│    session_id: "abc123",                                                │
│    current_task_id: "task1",                                            │
│    agent_outputs: {},                                                   │
│    needs_human_approval: false                                          │
│  }                                                                        │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 │ Graph Execution
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      LangGraph Output State                              │
│  {                                                                        │
│    messages: [...],                                                      │
│    session_id: "abc123",                                                │
│    current_task_id: "task1",                                            │
│    agent_outputs: {"agent1": "result"},                                │
│    needs_human_approval: false                                          │
│  }                                                                        │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 │ langgraph_state_to_execution_result()
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Our ExecutionResult                              │
│  {                                                                        │
│    status: ExecutionStatus.SUCCESS,                                     │
│    output: {"agent1": "result"},                                        │
│    metadata: {"orchestrator": "langgraph", "graph_state": {...}}       │
│  }                                                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. LangGraph StateGraph Structure

```
                              START
                                │
                                ▼
                        ┌───────────────┐
                        │  Supervisor   │
                        │     Node      │
                        └───────┬───────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
        ┌───────────┐   ┌───────────┐   ┌───────────┐
        │  Agent 1  │   │  Agent 2  │   │  Agent N  │
        │   Node    │   │   Node    │   │   Node    │
        └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
              │               │               │
              └───────────────┼───────────────┘
                              │
                              ▼
                        ┌───────────────┐
                        │  Supervisor   │
                        │     Node      │
                        └───────┬───────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
                  END                  (loop back)
```

**Node Details**:
- **Supervisor Node**: Decides which agent to call next
- **Agent Nodes**: Execute tasks using our AgentExecutor
- **Edges**: Routing logic (conditional or normal)

---

## 6. Hybrid Orchestrator with LangGraph

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         HybridOrchestrator                               │
│                                                                           │
│  Intelligent routing between orchestration strategies                    │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  OrchestratorRouter    │
                    │  Analyzes task:        │
                    │  - Has cycles?         │
                    │  - Needs human input?  │
                    │  - Needs checkpointing?│
                    │  - Uses HTN?           │
                    │  - Uses DSL?           │
                    └────────┬───────────────┘
                             │
             ┌───────────────┼───────────────┐
             ▼               ▼               ▼
    ┌────────────────┐ ┌──────────────┐ ┌──────────────┐
    │   LangGraph    │ │    Simple    │ │     HTN      │
    │  Orchestrator  │ │ Orchestrator │ │ Orchestrator │
    └────────────────┘ └──────────────┘ └──────────────┘
             │               │               │
             └───────────────┼───────────────┘
                             ▼
                    ┌────────────────────────┐
                    │  ExecutionResult       │
                    └────────────────────────┘
```

**Routing Logic**:
```python
if task.has_cycles or task.needs_human_input or task.needs_checkpointing:
    return "langgraph"
elif task.uses_htn or task.uses_dsl:
    return "simple"
else:
    return "simple"  # Default
```

---

## 7. Data Flow: Task Execution with LangGraph

```
┌─────────────────────────────────────────────────────────────────────────┐
│  1. User Input                                                           │
│  $ python3 -m src.main --orchestrator langgraph --task "Debug issue"    │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  2. CLI Parsing                                                          │
│  - Parse arguments                                                       │
│  - Create Task entity                                                    │
│  - Load agents                                                           │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  3. Orchestrator Creation                                                │
│  orchestrator = OrchestrationFactory.create_orchestrator("langgraph")   │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  4. Graph Building                                                       │
│  graph = orchestrator._build_graph(agents)                              │
│  - Create StateGraph                                                     │
│  - Add nodes (supervisor + agents)                                       │
│  - Add edges (routing logic)                                             │
│  - Compile graph                                                         │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  5. State Conversion                                                     │
│  graph_input = {                                                         │
│    "messages": [{"role": "user", "content": task.description}],         │
│    "session_id": context.session_id,                                    │
│    "current_task_id": task.task_id,                                     │
│    "agent_outputs": {}                                                  │
│  }                                                                        │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  6. Graph Execution                                                      │
│  graph_output = await graph.ainvoke(graph_input)                        │
│                                                                           │
│  Execution Flow:                                                         │
│  START → supervisor → agent_1 → supervisor → agent_2 → supervisor → END │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  7. Result Conversion                                                    │
│  result = ExecutionResult(                                               │
│    status=ExecutionStatus.SUCCESS,                                      │
│    output=graph_output["agent_outputs"],                                │
│    metadata={"orchestrator": "langgraph"}                               │
│  )                                                                        │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  8. Output to User                                                       │
│  Print results, metrics, etc.                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Comparison: Simple vs LangGraph Execution

### Simple Orchestrator Flow
```
Task → TaskPlanner → ExecutionPlan → AgentExecutor → Result
  (100ms)   (50ms)       (10ms)          (200ms)      (360ms total)
```

### LangGraph Orchestrator Flow
```
Task → Build Graph → Convert State → Execute Graph → Convert Result → Result
  (0ms)    (100ms)      (10ms)          (250ms)         (10ms)      (370ms total)
```

**Overhead**: ~10ms (3% slower)  
**Trade-off**: Worth it for cycles, human-in-loop, checkpointing

---

## 9. Integration Patterns

### Pattern 1: Adapter (Recommended)
```
Our System ─────┐
                ├─→ IAgentCoordinator ←─ LangGraph Adapter
LangGraph ──────┘
```
**Pros**: Clean separation, easy to remove  
**Cons**: Conversion overhead

### Pattern 2: Core Replacement (Not Recommended)
```
Our System ──X──> Removed
LangGraph ─────→ Core Orchestration
```
**Pros**: Full LangGraph features  
**Cons**: Loses our unique capabilities, high risk

### Pattern 3: Hybrid (Best)
```
Our System ─────┐
                ├─→ HybridOrchestrator ─→ Intelligent Routing
LangGraph ──────┘
```
**Pros**: Best of both worlds  
**Cons**: More complexity

---

## 10. Decision Tree: Which Orchestrator?

```
                        Start
                          │
                          ▼
                  ┌───────────────┐
                  │  Task Type?   │
                  └───────┬───────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
  ┌──────────┐      ┌──────────┐      ┌──────────┐
  │  Simple  │      │  Cycles  │      │   HTN    │
  │   Task   │      │  Needed? │      │  Needed? │
  └────┬─────┘      └────┬─────┘      └────┬─────┘
       │                 │                  │
       ▼                 ▼                  ▼
  ┌──────────┐      ┌──────────┐      ┌──────────┐
  │  Simple  │      │LangGraph │      │  Simple  │
  │Orchestr. │      │Orchestr. │      │Orchestr. │
  └──────────┘      └──────────┘      └──────────┘
```

---

## Summary

These diagrams show:
1. **Current architecture** - Clean, modular, DIP-compliant
2. **With LangGraph** - Adds new orchestrator as adapter
3. **Internal flow** - How LangGraph orchestrator works
4. **State conversion** - Bridge between our entities and LangGraph
5. **Graph structure** - LangGraph's supervisor pattern
6. **Hybrid routing** - Intelligent orchestrator selection
7. **Data flow** - End-to-end task execution
8. **Performance** - Comparison of execution paths
9. **Integration patterns** - Different approaches
10. **Decision tree** - When to use which orchestrator

**Key Insight**: LangGraph integrates cleanly as an adapter, preserving our Clean Architecture while adding powerful new capabilities.

