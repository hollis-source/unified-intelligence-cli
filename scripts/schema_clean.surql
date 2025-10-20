-- SurrealDB RAG schema for ATADO (clean definitions only)
-- Vector embeddings for semantic code search

-- =============================
-- Tables with Vector Embeddings
-- =============================

DEFINE TABLE code_entity SCHEMAFULL;
DEFINE FIELD id            ON code_entity TYPE string;
DEFINE FIELD repo_path     ON code_entity TYPE string;
DEFINE FIELD file_path     ON code_entity TYPE string;
DEFINE FIELD language      ON code_entity TYPE string;
DEFINE FIELD entity_type   ON code_entity TYPE string;
DEFINE FIELD name          ON code_entity TYPE string;
DEFINE FIELD qualified_name ON code_entity TYPE string;
DEFINE FIELD start_line    ON code_entity TYPE int;
DEFINE FIELD end_line      ON code_entity TYPE option<int> DEFAULT 0;
DEFINE FIELD content       ON code_entity TYPE string;
DEFINE FIELD content_hash  ON code_entity TYPE string;
DEFINE FIELD docstring     ON code_entity TYPE string;
DEFINE FIELD tags          ON code_entity TYPE array<string>;
DEFINE FIELD embedding     ON code_entity TYPE array<float>;
DEFINE FIELD embedding_model ON code_entity TYPE string;
DEFINE FIELD created_at    ON code_entity TYPE datetime VALUE time::now();
DEFINE FIELD updated_at    ON code_entity TYPE datetime VALUE time::now();

DEFINE INDEX idx_code_entity_key ON code_entity FIELDS file_path, name UNIQUE;
DEFINE INDEX idx_code_entity_qname ON code_entity FIELDS qualified_name;
DEFINE INDEX idx_code_entity_hash ON code_entity FIELDS content_hash;
DEFINE INDEX idx_code_entity_tags ON code_entity FIELDS tags;
DEFINE INDEX idx_code_entity_updated ON code_entity FIELDS updated_at;


DEFINE TABLE execution_log SCHEMAFULL;
DEFINE FIELD id               ON execution_log TYPE string;
DEFINE FIELD task_id          ON execution_log TYPE string;
DEFINE FIELD task_description ON execution_log TYPE string;
DEFINE FIELD task_domain      ON execution_log TYPE string;
DEFINE FIELD agent_id         ON execution_log TYPE string;
DEFINE FIELD agent_role       ON execution_log TYPE string;
DEFINE FIELD team_id          ON execution_log TYPE string;
DEFINE FIELD success          ON execution_log TYPE bool;
DEFINE FIELD status           ON execution_log TYPE string;
DEFINE FIELD error_message    ON execution_log TYPE string;
DEFINE FIELD latency_seconds  ON execution_log TYPE float;
DEFINE FIELD metadata         ON execution_log TYPE object;
DEFINE FIELD output_excerpt   ON execution_log TYPE string;
DEFINE FIELD embedding        ON execution_log TYPE array<float>;
DEFINE FIELD embedding_model  ON execution_log TYPE string;
DEFINE FIELD routing_domain   ON execution_log TYPE string;
DEFINE FIELD routing_confidence ON execution_log TYPE float;
DEFINE FIELD was_fallback     ON execution_log TYPE bool DEFAULT false;
DEFINE FIELD timestamp        ON execution_log TYPE datetime VALUE time::now();

DEFINE INDEX idx_exec_time ON execution_log FIELDS timestamp;
DEFINE INDEX idx_exec_success ON execution_log FIELDS success, status;
DEFINE INDEX idx_exec_domain_agent ON execution_log FIELDS task_domain, agent_role;


DEFINE TABLE agent_learning SCHEMAFULL;
DEFINE FIELD id                 ON agent_learning TYPE string;
DEFINE FIELD pattern_id         ON agent_learning TYPE string;
DEFINE FIELD hypothesis         ON agent_learning TYPE string;
DEFINE FIELD confidence         ON agent_learning TYPE float;
DEFINE FIELD evidence_ids       ON agent_learning TYPE array<string>;
DEFINE FIELD embedding          ON agent_learning TYPE array<float>;
DEFINE FIELD embedding_model    ON agent_learning TYPE string;
DEFINE FIELD created_at         ON agent_learning TYPE datetime VALUE time::now();

DEFINE INDEX idx_learning_time ON agent_learning FIELDS created_at;
DEFINE INDEX idx_learning_conf ON agent_learning FIELDS confidence;


DEFINE TABLE optimization_pattern SCHEMAFULL;
DEFINE FIELD id                 ON optimization_pattern TYPE string;
DEFINE FIELD title              ON optimization_pattern TYPE string;
DEFINE FIELD description        ON optimization_pattern TYPE string;
DEFINE FIELD applies_to_domain  ON optimization_pattern TYPE string;
DEFINE FIELD tags               ON optimization_pattern TYPE array<string>;
DEFINE FIELD snippet            ON optimization_pattern TYPE string;
DEFINE FIELD embedding          ON optimization_pattern TYPE array<float>;
DEFINE FIELD embedding_model    ON optimization_pattern TYPE string;
DEFINE FIELD created_at         ON optimization_pattern TYPE datetime VALUE time::now();

DEFINE INDEX idx_pattern_domain ON optimization_pattern FIELDS applies_to_domain;
DEFINE INDEX idx_pattern_tags ON optimization_pattern FIELDS tags;
