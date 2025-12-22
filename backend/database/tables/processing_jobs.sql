-- Generated schema for public.processing_jobs
CREATE TABLE public.processing_jobs (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  job_id character varying(255) NOT NULL,
  status character varying(50) NOT NULL,
  data_types json NOT NULL,
  start_date date NOT NULL,
  end_date date NOT NULL,
  progress json NOT NULL,
  records_processed json NOT NULL,
  error_message text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  started_at timestamp with time zone,
  completed_at timestamp with time zone,
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  PRIMARY KEY (id)
);

-- ======================================
-- PROCESSING_JOBS TABLE INDEXES
-- ======================================

-- Critical performance index for job history queries
CREATE INDEX IF NOT EXISTS idx_processing_jobs_tenant_created 
ON processing_jobs (tenant_id, created_at DESC);

-- Unique constraint on job_id for fast lookups
CREATE UNIQUE INDEX IF NOT EXISTS idx_processing_jobs_job_id 
ON processing_jobs (job_id);

-- Status filtering index
CREATE INDEX IF NOT EXISTS idx_processing_jobs_tenant_status 
ON processing_jobs (tenant_id, status);

-- Date range queries index
CREATE INDEX IF NOT EXISTS idx_processing_jobs_tenant_date_range 
ON processing_jobs (tenant_id, start_date, end_date);