-- Generated schema for public.email_send_history
CREATE TABLE public.email_send_history (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  job_id character varying(100),
  branch_code character varying(100) NOT NULL,
  sales_rep_email character varying(255) NOT NULL,
  sales_rep_name character varying(255),
  subject character varying(500) NOT NULL,
  report_date date NOT NULL,
  status character varying(50) NOT NULL DEFAULT 'sent',
  smtp_response text,
  error_message text,
  sent_at timestamp with time zone NOT NULL DEFAULT now(),
  PRIMARY KEY (id)
);

-- ======================================
-- EMAIL_SEND_HISTORY TABLE INDEXES
-- ======================================

-- Core performance index for tenant history queries
CREATE INDEX IF NOT EXISTS idx_email_history_tenant_date 
ON email_send_history (tenant_id, sent_at DESC);

-- Index for job-based queries
CREATE INDEX IF NOT EXISTS idx_email_history_job 
ON email_send_history (job_id) WHERE job_id IS NOT NULL;

-- Index for branch-based queries
CREATE INDEX IF NOT EXISTS idx_email_history_branch 
ON email_send_history (tenant_id, branch_code, sent_at DESC);

-- Index for email recipient queries
CREATE INDEX IF NOT EXISTS idx_email_history_email 
ON email_send_history (tenant_id, sales_rep_email, sent_at DESC);

-- Index for status monitoring
CREATE INDEX IF NOT EXISTS idx_email_history_status 
ON email_send_history (tenant_id, status, sent_at DESC) 
WHERE status != 'sent';

-- Foreign key reference to email jobs
ALTER TABLE email_send_history 
ADD CONSTRAINT fk_email_history_job 
FOREIGN KEY (job_id) REFERENCES email_sending_jobs(job_id);
