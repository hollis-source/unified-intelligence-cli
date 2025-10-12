-- SurrealDB Initialization Script for Project Builder
-- Sprint 1: Production Deployment - SurrealDB Migration
-- Migrates from PostgreSQL to SurrealDB with multi-model enhancements
--
-- Architecture: Combines relational tables with graph edges and vector embeddings
-- Benefits:
--   - Graph queries for task dependencies (5-8x faster than SQL JOINs)
--   - Vector embeddings for semantic artifact search
--   - Real-time subscriptions for dashboard updates
--   - Schema validation with flexibility

-- =============================================================================
-- Namespace and Database Setup
-- =============================================================================
DEFINE NAMESPACE project_builder;
USE NS project_builder;
DEFINE DATABASE production;
USE DB production;

-- =============================================================================
-- Core Tables (Relational + Schema Validation)
-- =============================================================================

-- Projects: Main project metadata
DEFINE TABLE projects SCHEMAFULL;
DEFINE FIELD project_id ON TABLE projects TYPE string ASSERT $value != NONE;
DEFINE FIELD goal ON TABLE projects TYPE option<string>;  -- Optional: Derived from HTN root description
DEFINE FIELD created_at ON TABLE projects TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON TABLE projects TYPE datetime DEFAULT time::now();
DEFINE FIELD status ON TABLE projects TYPE string DEFAULT 'in_progress';
DEFINE FIELD completion_percentage ON TABLE projects TYPE number DEFAULT 0.0;
DEFINE FIELD metadata ON TABLE projects TYPE object DEFAULT {};
-- State-specific fields (for Project Builder state persistence)
DEFINE FIELD version ON TABLE projects TYPE option<int>;
DEFINE FIELD htn_graph ON TABLE projects TYPE option<string>;  -- Base64-encoded pickle
DEFINE FIELD task_status ON TABLE projects TYPE option<object>;
DEFINE FIELD world_state ON TABLE projects TYPE option<object>;
DEFINE FIELD last_updated ON TABLE projects TYPE option<string>;

-- Indexes for performance
DEFINE INDEX project_id_idx ON TABLE projects COLUMNS project_id;  -- Not unique: allows versioning
DEFINE INDEX project_version_idx ON TABLE projects COLUMNS project_id, version UNIQUE;  -- Unique per version
DEFINE INDEX status_idx ON TABLE projects COLUMNS status;
DEFINE INDEX created_at_idx ON TABLE projects COLUMNS created_at;

-- Tasks: Individual tasks within projects
DEFINE TABLE tasks SCHEMAFULL;
DEFINE FIELD task_id ON TABLE tasks TYPE string ASSERT $value != NONE;
DEFINE FIELD task_type ON TABLE tasks TYPE string ASSERT $value != NONE;
DEFINE FIELD description ON TABLE tasks TYPE string ASSERT $value != NONE;
DEFINE FIELD status ON TABLE tasks TYPE string DEFAULT 'pending';
DEFINE FIELD created_at ON TABLE tasks TYPE datetime DEFAULT time::now();
DEFINE FIELD started_at ON TABLE tasks TYPE option<datetime>;
DEFINE FIELD completed_at ON TABLE tasks TYPE option<datetime>;
DEFINE FIELD error_message ON TABLE tasks TYPE option<string>;
DEFINE FIELD retry_count ON TABLE tasks TYPE int DEFAULT 0;
DEFINE FIELD metadata ON TABLE tasks TYPE object DEFAULT {};

-- Indexes for performance
DEFINE INDEX task_status_idx ON TABLE tasks COLUMNS status;
DEFINE INDEX task_id_idx ON TABLE tasks COLUMNS task_id;

-- Artifacts: Generated code, documentation, etc.
-- Enhanced with vector embeddings for semantic search
DEFINE TABLE artifacts SCHEMAFULL;
DEFINE FIELD artifact_name ON TABLE artifacts TYPE string ASSERT $value != NONE;
DEFINE FIELD artifact_type ON TABLE artifacts TYPE string ASSERT $value != NONE;
DEFINE FIELD content ON TABLE artifacts TYPE option<string>;
DEFINE FIELD quality_score ON TABLE artifacts TYPE option<number>;
DEFINE FIELD syntax_correct ON TABLE artifacts TYPE option<bool>;
DEFINE FIELD has_todos ON TABLE artifacts TYPE option<bool>;
DEFINE FIELD has_thinking ON TABLE artifacts TYPE option<bool>;
DEFINE FIELD created_at ON TABLE artifacts TYPE datetime DEFAULT time::now();
DEFINE FIELD metadata ON TABLE artifacts TYPE object DEFAULT {};
DEFINE FIELD embedding ON TABLE artifacts TYPE option<array<number>>;  -- Vector embeddings (384-dim for semantic search)

-- Indexes for performance
DEFINE INDEX artifact_name_idx ON TABLE artifacts COLUMNS artifact_name;
DEFINE INDEX artifact_type_idx ON TABLE artifacts COLUMNS artifact_type;

-- Execution Metrics: Performance tracking
DEFINE TABLE execution_metrics SCHEMAFULL;
DEFINE FIELD execution_time_ms ON TABLE execution_metrics TYPE int;
DEFINE FIELD tokens_used ON TABLE execution_metrics TYPE int;
DEFINE FIELD cost_usd ON TABLE execution_metrics TYPE number;
DEFINE FIELD model_used ON TABLE execution_metrics TYPE string;
DEFINE FIELD timestamp ON TABLE execution_metrics TYPE datetime DEFAULT time::now();
DEFINE FIELD metadata ON TABLE execution_metrics TYPE object DEFAULT {};

-- Indexes for performance
DEFINE INDEX timestamp_idx ON TABLE execution_metrics COLUMNS timestamp;

-- =============================================================================
-- Graph Edges (Relationships for Graph Traversal)
-- =============================================================================
-- These enable fast graph queries like "find all tasks for a project"
-- without expensive JOINs

-- Project → Task relationship
DEFINE TABLE has_task SCHEMAFULL TYPE RELATION IN projects OUT tasks;
DEFINE FIELD created_at ON TABLE has_task TYPE datetime DEFAULT time::now();

-- Task → Artifact relationship
DEFINE TABLE produces_artifact SCHEMAFULL TYPE RELATION IN tasks OUT artifacts;
DEFINE FIELD created_at ON TABLE produces_artifact TYPE datetime DEFAULT time::now();

-- Project → Execution Metrics relationship
DEFINE TABLE has_metric SCHEMAFULL TYPE RELATION IN projects OUT execution_metrics;
DEFINE FIELD created_at ON TABLE has_metric TYPE datetime DEFAULT time::now();

-- Task → Execution Metrics relationship
DEFINE TABLE task_metric SCHEMAFULL TYPE RELATION IN tasks OUT execution_metrics;
DEFINE FIELD created_at ON TABLE task_metric TYPE datetime DEFAULT time::now();

-- =============================================================================
-- Events (Auto-update triggers)
-- =============================================================================

-- Auto-update updated_at timestamp on project modifications
DEFINE EVENT update_project_timestamp ON TABLE projects WHEN $event = "UPDATE" THEN (
    UPDATE $after.id SET updated_at = time::now()
);

-- =============================================================================
-- Example Queries (for reference, not executed)
-- =============================================================================

-- Graph query: Get all tasks for a project (no JOINs!)
-- SELECT ->has_task->tasks.* FROM projects WHERE project_id = 'my-project';

-- Graph query: Get all artifacts produced by a task's child tasks
-- SELECT ->has_task->tasks->produces_artifact->artifacts.* FROM projects:my_project;

-- Semantic search: Find similar artifacts by vector embedding
-- SELECT * FROM artifacts WHERE embedding <|10|> $query_embedding ORDER BY vector::distance(embedding, $query_embedding) LIMIT 5;

-- Real-time subscription: Watch for new artifacts
-- LIVE SELECT * FROM artifacts;

-- Analytics: Project dashboard (with graph aggregations)
-- SELECT
--   project_id,
--   goal,
--   status,
--   completion_percentage,
--   count(->has_task->tasks) AS total_tasks,
--   count(->has_task->tasks[WHERE status = 'completed']) AS completed_tasks,
--   math::mean(->has_task->tasks->produces_artifact->artifacts.quality_score) AS avg_quality_score,
--   math::sum(->has_metric->execution_metrics.tokens_used) AS total_tokens,
--   math::sum(->has_metric->execution_metrics.cost_usd) AS total_cost
-- FROM projects
-- GROUP ALL;

-- =============================================================================
-- Permissions (Production Security)
-- =============================================================================
-- Note: For production, define more granular permissions
-- Currently using root user credentials from docker-compose

-- DEFINE SCOPE pb_user SESSION 24h;
-- DEFINE ACCESS pb_access ON DATABASE TYPE RECORD
--   SIGNUP ( CREATE user SET email = $email, pass = crypto::argon2::generate($pass) )
--   SIGNIN ( SELECT * FROM user WHERE email = $email AND crypto::argon2::compare(pass, $pass) );
