-- Tenant configuration table (single-tenant-per-database model)
-- Each database has exactly one tenant configuration row
CREATE TABLE IF NOT EXISTS public.tenant_config (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name character varying(255) NOT NULL,
  bigquery_project_id character varying(255),
  bigquery_dataset_id character varying(255),
  bigquery_credentials jsonb,
  sftp_config jsonb,
  email_config jsonb,
  bigquery_enabled boolean DEFAULT true,
  sftp_enabled boolean DEFAULT true,
  smtp_enabled boolean DEFAULT true,
  bigquery_validation_error text,
  sftp_validation_error text,
  smtp_validation_error text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  PRIMARY KEY (id)
);



