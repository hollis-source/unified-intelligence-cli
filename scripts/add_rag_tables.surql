-- =============================
-- Additional RAG Tables
-- =============================
-- This script adds the missing tables for RAG integration:
-- 1. agent_performance - Track agent success rates and performance metrics
-- 2. routing_decisions - Track routing decisions and feedback

-- Agent Performance Table
DEFINE TABLE agent_performance SCHEMAFULL;
DEFINE FIELD agent_role         ON agent_performance TYPE string;      -- e.g., 'backend-specialist'
DEFINE FIELD total_tasks        ON agent_performance TYPE int DEFAULT 0;
DEFINE FIELD successful_tasks   ON agent_performance TYPE int DEFAULT 0;
DEFINE FIELD failed_tasks       ON agent_performance TYPE int DEFAULT 0;
DEFINE FIELD avg_latency_ms     ON agent_performance TYPE float DEFAULT 0.0;
DEFINE FIELD success_rate       ON agent_performance TYPE float DEFAULT 0.0; -- calculated: successful/total
DEFINE FIELD last_updated       ON agent_performance TYPE datetime VALUE time::now();
DEFINE FIELD created_at         ON agent_performance TYPE datetime VALUE time::now();

DEFINE INDEX idx_agent_role ON agent_performance FIELDS agent_role UNIQUE;
DEFINE INDEX idx_agent_success_rate ON agent_performance FIELDS success_rate;
DEFINE INDEX idx_agent_updated ON agent_performance FIELDS last_updated;


-- Routing Decisions Table
DEFINE TABLE routing_decisions SCHEMAFULL;
DEFINE FIELD id                 ON routing_decisions TYPE string;      -- uuid
DEFINE FIELD task_id            ON routing_decisions TYPE string;      -- links to execution_log
DEFINE FIELD task_description   ON routing_decisions TYPE string;
DEFINE FIELD task_domain        ON routing_decisions TYPE string;      -- predicted domain
DEFINE FIELD selected_agent     ON routing_decisions TYPE string;      -- agent_role selected
DEFINE FIELD selected_team      ON routing_decisions TYPE string;      -- team selected (if team routing)
DEFINE FIELD routing_strategy   ON routing_decisions TYPE string;      -- 'keyword' | 'team' | 'rag'
DEFINE FIELD confidence         ON routing_decisions TYPE float;       -- routing confidence score
DEFINE FIELD success            ON routing_decisions TYPE bool;        -- was the routing successful?
DEFINE FIELD actual_agent       ON routing_decisions TYPE string;      -- actual agent that executed (if different)
DEFINE FIELD fallback_used      ON routing_decisions TYPE bool DEFAULT false;
DEFINE FIELD metadata           ON routing_decisions TYPE object;      -- additional routing metadata
DEFINE FIELD timestamp          ON routing_decisions TYPE datetime VALUE time::now();

DEFINE INDEX idx_routing_time ON routing_decisions FIELDS timestamp;
DEFINE INDEX idx_routing_task ON routing_decisions FIELDS task_id;
DEFINE INDEX idx_routing_agent ON routing_decisions FIELDS selected_agent;
DEFINE INDEX idx_routing_success ON routing_decisions FIELDS success;
DEFINE INDEX idx_routing_strategy ON routing_decisions FIELDS routing_strategy;

