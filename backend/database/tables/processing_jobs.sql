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
