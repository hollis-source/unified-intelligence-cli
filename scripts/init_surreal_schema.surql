-- SurrealDB RAG schema for ATADO
-- Namespace/DB should be selected via `USE <ns> <db>` in the client

-- =============================
-- Tables
-- =============================

DEFINE TABLE code_entity SCHEMAFULL;
DEFINE FIELD id            ON code_entity TYPE string;
DEFINE FIELD repo_path     ON code_entity TYPE string;           -- absolute or repo-relative path
DEFINE FIELD file_path     ON code_entity TYPE string;           -- repo-relative path
DEFINE FIELD language      ON code_entity TYPE string;           -- e.g., 'python'
DEFINE FIELD entity_type   ON code_entity TYPE string;           -- 'module' | 'class' | 'function'
DEFINE FIELD name          ON code_entity TYPE string;           -- symbol name
DEFINE FIELD qualified_name ON code_entity TYPE string;          -- dotted path, e.g., src.module.Class.method
DEFINE FIELD start_line    ON code_entity TYPE int;
DEFINE FIELD end_line      ON code_entity TYPE int;
DEFINE FIELD content       ON code_entity TYPE string;           -- raw code snippet
DEFINE FIELD content_hash  ON code_entity TYPE string;           -- sha256 for incremental indexing
DEFINE FIELD docstring     ON code_entity TYPE string;           -- optional
DEFINE FIELD tags          ON code_entity TYPE array<string>;
DEFINE FIELD embedding     ON code_entity TYPE array<float>;     -- vector embedding of code/content
DEFINE FIELD embedding_model ON code_entity TYPE string;         -- model id
DEFINE FIELD created_at    ON code_entity TYPE datetime VALUE time::now();
DEFINE FIELD updated_at    ON code_entity TYPE datetime VALUE time::now();

DEFINE INDEX idx_code_entity_key ON code_entity FIELDS file_path, name UNIQUE;
DEFINE INDEX idx_code_entity_qname ON code_entity FIELDS qualified_name;
DEFINE INDEX idx_code_entity_hash ON code_entity FIELDS content_hash;
DEFINE INDEX idx_code_entity_tags ON code_entity FIELDS tags;
DEFINE INDEX idx_code_entity_updated ON code_entity FIELDS updated_at;


DEFINE TABLE execution_log SCHEMAFULL;
DEFINE FIELD id               ON execution_log TYPE string;      -- execution id (uuid)
DEFINE FIELD task_id          ON execution_log TYPE string;      -- optional external id
DEFINE FIELD task_description ON execution_log TYPE string;
DEFINE FIELD task_domain      ON execution_log TYPE string;      -- e.g., 'backend','testing','dsl'
DEFINE FIELD agent_id         ON execution_log TYPE string;
DEFINE FIELD agent_role       ON execution_log TYPE string;      -- e.g., 'backend-specialist'
DEFINE FIELD team_id          ON execution_log TYPE string;      -- optional
DEFINE FIELD success          ON execution_log TYPE bool;
DEFINE FIELD status           ON execution_log TYPE string;      -- 'success' | 'failed' | 'partial'
DEFINE FIELD error_message    ON execution_log TYPE string;      -- if failed
DEFINE FIELD latency_seconds  ON execution_log TYPE float;
DEFINE FIELD metadata         ON execution_log TYPE object;      -- JSON metadata
DEFINE FIELD output_excerpt   ON execution_log TYPE string;      -- truncated output for embedding
DEFINE FIELD embedding        ON execution_log TYPE array<float>;-- vector embedding of pattern
DEFINE FIELD embedding_model  ON execution_log TYPE string;
DEFINE FIELD routing_domain   ON execution_log TYPE string;      -- predicted routing domain
DEFINE FIELD routing_confidence ON execution_log TYPE float;
DEFINE FIELD was_fallback     ON execution_log TYPE bool DEFAULT false;
DEFINE FIELD timestamp        ON execution_log TYPE datetime VALUE time::now();

DEFINE INDEX idx_exec_time ON execution_log FIELDS timestamp;
DEFINE INDEX idx_exec_success ON execution_log FIELDS success, status;
DEFINE INDEX idx_exec_domain_agent ON execution_log FIELDS task_domain, agent_role;


DEFINE TABLE agent_learning SCHEMAFULL;
DEFINE FIELD id                 ON agent_learning TYPE string;   -- uuid
DEFINE FIELD pattern_id         ON agent_learning TYPE string;   -- links to execution_log.id
DEFINE FIELD hypothesis         ON agent_learning TYPE string;   -- e.g., 'Use strategy X for domain Y'
DEFINE FIELD confidence         ON agent_learning TYPE float;
DEFINE FIELD evidence_ids       ON agent_learning TYPE array<string>;
DEFINE FIELD embedding          ON agent_learning TYPE array<float>;
DEFINE FIELD embedding_model    ON agent_learning TYPE string;
DEFINE FIELD created_at         ON agent_learning TYPE datetime VALUE time::now();

DEFINE INDEX idx_learning_time ON agent_learning FIELDS created_at;
DEFINE INDEX idx_learning_conf ON agent_learning FIELDS confidence;


DEFINE TABLE optimization_pattern SCHEMAFULL;
DEFINE FIELD id                 ON optimization_pattern TYPE string; -- uuid
DEFINE FIELD title              ON optimization_pattern TYPE string;
DEFINE FIELD description        ON optimization_pattern TYPE string;
DEFINE FIELD applies_to_domain  ON optimization_pattern TYPE string; -- e.g., 'routing','planning','testing'
DEFINE FIELD tags               ON optimization_pattern TYPE array<string>;
DEFINE FIELD snippet            ON optimization_pattern TYPE string; -- example code/prompt snippet
DEFINE FIELD embedding          ON optimization_pattern TYPE array<float>;
DEFINE FIELD embedding_model    ON optimization_pattern TYPE string;
DEFINE FIELD created_at         ON optimization_pattern TYPE datetime VALUE time::now();

DEFINE INDEX idx_pattern_domain ON optimization_pattern FIELDS applies_to_domain;
DEFINE INDEX idx_pattern_tags ON optimization_pattern FIELDS tags;
DEFINE INDEX idx_pattern_time ON optimization_pattern FIELDS created_at;


-- =============================
-- Example Queries (semantic)
-- =============================

-- 1) Semantic code search by embedding (top-5 cosine similarity)
-- Params: $query_embedding (array<float>), $top_k (int)
SELECT id, file_path, name, qualified_name,
       vector::similarity::cosine(embedding, $query_embedding) AS similarity
FROM code_entity
WHERE embedding <|$top_k|> $query_embedding
ORDER BY similarity DESC
LIMIT $top_k;

-- 2) Hybrid search: restrict by language or tag
-- Params: $lang (string), $tag (string), $top_k, $query_embedding
SELECT id, file_path, name, language, tags,
       vector::similarity::cosine(embedding, $query_embedding) AS similarity
FROM code_entity
WHERE language = $lang
  AND $tag IN tags
  AND embedding <|$top_k|> $query_embedding
ORDER BY similarity DESC
LIMIT $top_k;

-- 3) Retrieve similar successful execution patterns in last 30 days for a domain
-- Params: $domain (string), $query_embedding, $top_k
SELECT id, task_description, agent_role, success, latency_seconds,
       vector::similarity::cosine(embedding, $query_embedding) AS similarity
FROM execution_log
WHERE success = true
  AND task_domain = $domain
  AND timestamp > time::now() - 30d
  AND embedding <|$top_k|> $query_embedding
ORDER BY similarity DESC
LIMIT $top_k;

