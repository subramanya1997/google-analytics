-- Generated schema for public.tenants
CREATE TABLE public.tenants (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name character varying(255) NOT NULL,
  domain character varying(255),
  bigquery_project_id character varying(255),
  bigquery_dataset_id character varying(255),
  bigquery_credentials jsonb,
  sftp_config jsonb,
  email_config jsonb,
  postgres_config jsonb,
  email_schedule character varying(255) DEFAULT '0 10 * * *',
  email_schedule_task_id character varying(255),
  data_ingestion_schedule character varying(255) DEFAULT '0 10 * * *',
  data_ingestion_schedule_task_id character varying(255),
  bigquery_enabled boolean DEFAULT true,
  sftp_enabled boolean DEFAULT true,
  smtp_enabled boolean DEFAULT true,
  bigquery_validation_error text,
  sftp_validation_error text,
  smtp_validation_error text,
  is_active boolean NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  PRIMARY KEY (id)
);

-- ======================================
-- TENANTS TABLE INDEXES
-- ======================================

-- Core performance index for tenant lookups
CREATE INDEX IF NOT EXISTS idx_tenants_active 
ON tenants (id) WHERE is_active = true;

-- Index for domain lookups if needed
CREATE INDEX IF NOT EXISTS idx_tenants_domain
ON tenants (domain) WHERE domain IS NOT NULL;

-- ======================================
-- ADDITIONAL INDEXES FOR PERFORMANCE
-- ======================================

-- Index for email schedule task lookups
CREATE INDEX IF NOT EXISTS idx_tenants_email_task
ON tenants (email_schedule_task_id) WHERE email_schedule_task_id IS NOT NULL;

-- Index for data ingestion schedule task lookups
CREATE INDEX IF NOT EXISTS idx_tenants_ingestion_task
ON tenants (data_ingestion_schedule_task_id) WHERE data_ingestion_schedule_task_id IS NOT NULL;

-- Index for active tenants (useful for frequent active-only queries)
CREATE INDEX IF NOT EXISTS idx_tenants_is_active
ON tenants (is_active) WHERE is_active = true;

-- Composite index for email tasks on active tenants (if frequently queried together)
CREATE INDEX IF NOT EXISTS idx_tenants_email_active
ON tenants (email_schedule_task_id, is_active) WHERE email_schedule_task_id IS NOT NULL;

-- Composite index for ingestion tasks on active tenants (if frequently queried together)
CREATE INDEX IF NOT EXISTS idx_tenants_ingestion_active
ON tenants (data_ingestion_schedule_task_id, is_active) WHERE data_ingestion_schedule_task_id IS NOT NULL;

-- Index on updated_at for time-based queries (if needed for monitoring/updates)
CREATE INDEX IF NOT EXISTS idx_tenants_updated_at
ON tenants (updated_at);
