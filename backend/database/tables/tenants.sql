-- Generated schema for public.tenants
CREATE TABLE public.tenants (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name character varying(255) NOT NULL,
  domain character varying(255),
  bigquery_project_id character varying(255),
  bigquery_dataset_id character varying(255),
  bigquery_credentials json,
  sftp_config json,
  is_active boolean NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  postgres_config jsonb,
  PRIMARY KEY (id)
);
