# UNIFIED_ARCHITECTURE_BASELINE.md

## Overview
This document synthesizes the architectural discussion between the user and assistant, focusing on evolving the system from disconnected components (DSL, CLI, Priority Workers) to a unified, graph-theoretic HTN-based framework. It captures key concepts, models, and strategies discussed, serving as a conceptual foundation for all future planning and implementation.

## 1. Key Architectural Concepts Discussed
The conversation addressed several core concepts to address system fragmentation:
- **System Problems**: The current setup suffers from disconnected subsystems, including DSL parsing issues, CLI instability, and Priority Workers failing to maintain connections, leading to unreliable task execution and resource allocation.
- **Proposals**: A shift to a graph-theoretic HTN (Hierarchical Task Network) model for project building, emphasizing recursive decomposition and compound graphs.
- **Coordination**: A meta-operational lifecycle for operations (Plan → Verify → Decompose → Execute) to ensure iterative refinement.
- **Formalism Debate**: Category theory provides semantic structure (e.g., morphisms for transformations), while graph theory handles implementation (e.g., nodes and edges for dependencies).
- **Resource Management**: A pool architecture for detection, planning, optimization, and learning, but deemed optional to avoid core complexity.
- **Abstraction and Integration**: Executor interfaces for task coordination, with strategies to migrate from legacy systems.

These concepts aim to create a composable, scalable architecture without over-engineering.

## 2. Graph-Theoretic HTN Model with Recursive Compound Graphs
The proposed HTN model uses graph theory for implementation, modeling tasks as directed acyclic graphs (DAGs) with nodes representing tasks and edges denoting dependencies or compositions.
- **Recursive Compound Graphs**: Tasks are compound structures where a Project contains Tasks, Tasks contain Todos, and Tasks can recursively contain sub-Tasks. This allows hierarchical decomposition: a high-level Project graph decomposes into finer-grained subgraphs.
- **HTN Mechanics**: Operators define task transformations (e.g., decompose a Task into Todos). Preconditions ensure validity (e.g., resources available), and effects update the graph state.
- **Benefits**: Enables dynamic planning, where graphs adapt via recursive refinement. For example, a Project graph might initially be coarse, then decomposed into executable subgraphs during runtime.
- **Implementation**: Graphs are stored as JSON-like structures or in a graph database, with algorithms for traversal, validation, and optimization.

This model contrasts with linear task lists by supporting parallel execution and complex dependencies.

## 3. Meta-Operational Lifecycle and Its Role
The meta-operational lifecycle coordinates system operations through four phases:
- **Plan**: Generate initial plans based on goals and constraints (e.g., using HTN graphs).
- **Verify**: Check plan feasibility against rules (e.g., category-theoretic laws for composition).
- **Decompose**: Break down plans into executable units (e.g., recursive task graphs).
- **Execute**: Run units via executors, monitoring for feedback loops.

Its role is to provide a control loop for reliability: failures in Execute trigger replanning, ensuring adaptive behavior. This lifecycle applies at multiple levels (project, task, todo), promoting composability and error resilience.

## 4. Category Theory as Semantic Formalism, Graph Theory as Implementation
- **Category Theory (Semantic Layer)**: Used for abstract semantics, defining morphisms (transformations) between objects (e.g., Tasks). Concepts like functors ensure composability, monads handle side effects, and natural transformations validate equivalences. It provides "laws" for correctness, e.g., associativity in task composition.
- **Graph Theory (Implementation Layer)**: Realizes semantics as concrete graphs: nodes for entities, edges for morphisms. This allows algorithmic processing (e.g., shortest-path for optimization).
- **Clarification**: The debate resolved that category theory guides design (e.g., proving task invariants), while graph theory enables execution. Hybrid approach: Use category theory for DSL semantics, graph theory for runtime graphs.

## 5. Unified Task Model (Project/Task/Todo Entities)
The model defines a hierarchical entity structure:
- **Project**: Top-level container with metadata (e.g., goals, deadlines). Contains multiple Tasks.
- **Task**: Decomposable unit with sub-Tasks or Todos. Supports recursion (a Task can contain Tasks).
- **Todo**: Atomic, executable leaf node (e.g., a single command or API call).

Entities are unified via shared interfaces (e.g., status: pending/executing/complete). Recursion allows nesting, enabling complex workflows (e.g., a Task "Build Feature" decomposes into sub-Tasks "Design" and "Implement", each with Todos).

## 6. Executor Abstraction and Coordination Protocol
- **Executor Interface**: Abstracts execution environments (e.g., local CLI, remote workers). Defines methods like `execute(task)`, `status()`, and `cancel()`. Supports polymorphism for different backends (e.g., Docker containers, cloud VMs).
- **Coordination Protocol**: A message-passing system (e.g., via queues or events) for lifecycle phases. Executors register, receive decomposed tasks, report progress, and handle failures. Protocol ensures load balancing and fault tolerance (e.g., retry on disconnect).

This abstraction decouples planning from execution, allowing integration with existing systems.

## 7. Resource Pool as Future Optional Module (with Rationale)
- **Architecture**: A pool manages resources via submodules: Detection (monitor availability), Planning (allocate based on needs), Optimization (rebalance for efficiency), Learning (adapt via ML for predictions).
- **Optionality Decision**: Made optional, not core, to avoid initial complexity. Rationale: Core system focuses on task execution; resource pool adds scalability but requires mature infrastructure. Defer to future phases to prevent scope creep.
- **Integration**: When enabled, pools feed into HTN graphs (e.g., resource nodes constrain decompositions).

## 8. Migration Strategy from Current Disconnected Systems
- **Assessment**: Identify gaps (e.g., CLI instability, worker disconnections) and map to new architecture (e.g., replace CLI with executor abstractions).
- **Phased Migration**:
  1. **Audit**: Catalog existing components (DSL parsers, workers).
  2. **Prototype**: Build HTN graphs for sample projects, integrating executors.
  3. **Incremental Rollout**: Migrate subsystems (e.g., start with Task decomposition, then Projects).
  4. **Fallbacks**: Maintain legacy during transition; use feature flags.
- **Tools**: Use CI/CD for testing, with rollback plans. Target: Unified system in 3–6 months, minimizing downtime.

## 9. Conceptual Foundation for Future Planning
This document establishes invariants (e.g., recursive graphs, lifecycle phases) and guidelines (e.g., category-graph hybrid) for extensions. Future planning should prioritize:
- Prototyping HTN graphs.
- Defining executor APIs.
- Evaluating resource pool pilots.
- Ensuring composability via category-theoretic proofs.

All decisions build on this baseline, promoting a coherent, evolvable architecture.
