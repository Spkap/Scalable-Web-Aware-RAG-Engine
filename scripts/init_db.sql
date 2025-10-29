-- Initialization SQL for PostgreSQL: creates the url_ingestion_jobs table, constraints, indexes, and trigger.
-- Uses gen_random_uuid() from the pgcrypto extension to populate UUID keys.

-- Ensure required extension for gen_random_uuid is available.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS url_ingestion_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    chunk_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    processing_time_seconds DOUBLE PRECISION DEFAULT 0,
    error_message TEXT,
    error_traceback TEXT,
    celery_task_id VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Trigger function to update `updated_at` on row modifications.
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = now();
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_updated_at ON url_ingestion_jobs;
CREATE TRIGGER trg_update_updated_at
BEFORE UPDATE ON url_ingestion_jobs
FOR EACH ROW
EXECUTE PROCEDURE update_updated_at_column();

-- Indexes to support common queries
CREATE INDEX IF NOT EXISTS idx_url_ingestion_jobs_status ON url_ingestion_jobs (status);
CREATE INDEX IF NOT EXISTS idx_url_ingestion_jobs_created_at ON url_ingestion_jobs (created_at);
CREATE INDEX IF NOT EXISTS idx_url_ingestion_jobs_celery_task_id ON url_ingestion_jobs (celery_task_id);
CREATE INDEX IF NOT EXISTS idx_url_ingestion_jobs_url ON url_ingestion_jobs (url);

-- Optional: GIN index for metadata JSONB if you perform jsonb queries
CREATE INDEX IF NOT EXISTS idx_url_ingestion_jobs_metadata_gin ON url_ingestion_jobs USING GIN (metadata);
