-- Database Initialization Script for Project Builder
-- Sprint 1: Production Deployment - P1.2 PostgreSQL Setup
-- Migrates from SQLite to PostgreSQL for production

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create schema for Project Builder tables
CREATE SCHEMA IF NOT EXISTS project_builder;

-- Set search path
SET search_path TO project_builder, public;

-- Projects table (main project metadata)
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id VARCHAR(255) UNIQUE NOT NULL,
    goal TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'in_progress',
    completion_percentage DECIMAL(5,2) DEFAULT 0.0,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Tasks table (individual tasks within projects)
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id VARCHAR(255) REFERENCES projects(project_id) ON DELETE CASCADE,
    task_id VARCHAR(255) NOT NULL,
    task_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(project_id, task_id)
);

-- Artifacts table (generated code, documentation, etc.)
CREATE TABLE IF NOT EXISTS artifacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id VARCHAR(255) REFERENCES projects(project_id) ON DELETE CASCADE,
    task_id VARCHAR(255) NOT NULL,
    artifact_name VARCHAR(255) NOT NULL,
    artifact_type VARCHAR(100) NOT NULL,
    content TEXT,
    quality_score DECIMAL(5,2),
    syntax_correct BOOLEAN,
    has_todos BOOLEAN,
    has_thinking BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(project_id, artifact_name)
);

-- Execution metrics table (for performance tracking)
CREATE TABLE IF NOT EXISTS execution_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id VARCHAR(255) REFERENCES projects(project_id) ON DELETE CASCADE,
    task_id VARCHAR(255),
    execution_time_ms INTEGER,
    tokens_used INTEGER,
    cost_usd DECIMAL(10,4),
    model_used VARCHAR(100),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_artifacts_project_id ON artifacts(project_id);
CREATE INDEX IF NOT EXISTS idx_metrics_project_id ON execution_metrics(project_id);
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON execution_metrics(timestamp DESC);

-- Create view for project dashboard
CREATE OR REPLACE VIEW project_dashboard AS
SELECT
    p.project_id,
    p.goal,
    p.status,
    p.completion_percentage,
    p.created_at,
    COUNT(DISTINCT t.id) AS total_tasks,
    COUNT(DISTINCT CASE WHEN t.status = 'completed' THEN t.id END) AS completed_tasks,
    COUNT(DISTINCT a.id) AS total_artifacts,
    AVG(a.quality_score) AS avg_quality_score,
    SUM(m.tokens_used) AS total_tokens,
    SUM(m.cost_usd) AS total_cost
FROM projects p
LEFT JOIN tasks t ON p.project_id = t.project_id
LEFT JOIN artifacts a ON p.project_id = a.project_id
LEFT JOIN execution_metrics m ON p.project_id = m.project_id
GROUP BY p.id, p.project_id, p.goal, p.status, p.completion_percentage, p.created_at;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update updated_at
CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions to pb_user
GRANT ALL PRIVILEGES ON SCHEMA project_builder TO pb_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA project_builder TO pb_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA project_builder TO pb_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA project_builder TO pb_user;

-- Insert sample data for testing (optional, can be removed in production)
-- INSERT INTO projects (project_id, goal, status) VALUES ('test-project-1', 'Test project for validation', 'completed');
