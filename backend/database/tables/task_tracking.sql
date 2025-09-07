-- Generated schema for public.task_tracking
CREATE TABLE public.task_tracking (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  task_id character varying(255) NOT NULL,
  task_type character varying(100) NOT NULL,
  completed boolean DEFAULT false,
  notes text,
  completed_by character varying(255),
  completed_at timestamp with time zone,
  updated_at timestamp with time zone DEFAULT now(),
  created_at timestamp with time zone DEFAULT now(),
  PRIMARY KEY (id)
);
