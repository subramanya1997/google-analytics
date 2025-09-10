-- Generated schema for public.tenants
CREATE TABLE public.tenants (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name character varying(255) NOT NULL,
  domain character varying(255),
  bigquery_project_id character varying(255),
  bigquery_dataset_id character varying(255),
  bigquery_credentials json,
  sftp_config json,
  email_config jsonb,
  is_active boolean NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  postgres_config jsonb,
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