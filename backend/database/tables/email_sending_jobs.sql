-- Generated schema for public.email_sending_jobs
CREATE TABLE public.email_sending_jobs (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  job_id character varying(100) NOT NULL,
  status character varying(50) NOT NULL DEFAULT 'queued',
  report_date date NOT NULL,
  target_branches text[],
  total_emails integer NOT NULL DEFAULT 0,
  emails_sent integer NOT NULL DEFAULT 0,
  emails_failed integer NOT NULL DEFAULT 0,
  error_message text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  started_at timestamp with time zone,
  completed_at timestamp with time zone,
  PRIMARY KEY (id),
  CONSTRAINT uq_email_job_id UNIQUE (job_id)
);

-- ======================================
-- STATISTICS TARGETS FOR QUERY OPTIMIZER
-- ======================================
-- Increase statistics for frequently filtered/joined columns to improve cardinality estimates

ALTER TABLE email_sending_jobs ALTER COLUMN tenant_id SET STATISTICS 1000;
ALTER TABLE email_sending_jobs ALTER COLUMN job_id SET STATISTICS 1000;
ALTER TABLE email_sending_jobs ALTER COLUMN status SET STATISTICS 1000;
ALTER TABLE email_sending_jobs ALTER COLUMN created_at SET STATISTICS 1000;

-- ======================================
-- EMAIL_SENDING_JOBS TABLE INDEXES
-- ======================================

-- Core performance index for tenant and job status queries
CREATE INDEX IF NOT EXISTS idx_email_jobs_tenant_status 
ON email_sending_jobs (tenant_id, status);

-- Index for job history queries (most recent first)
CREATE INDEX IF NOT EXISTS idx_email_jobs_tenant_created 
ON email_sending_jobs (tenant_id, created_at DESC);

-- Index for date-based queries
CREATE INDEX IF NOT EXISTS idx_email_jobs_report_date 
ON email_sending_jobs (tenant_id, report_date DESC);

-- Index for active job monitoring
CREATE INDEX IF NOT EXISTS idx_email_jobs_active 
ON email_sending_jobs (status, created_at) 
WHERE status IN ('queued', 'processing');
