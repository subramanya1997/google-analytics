-- Users table: stores user master data synced from BigQuery
CREATE TABLE IF NOT EXISTS public.users (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  user_id character varying(100),
  user_name character varying(255),
  buying_company_name character varying(255),
  buying_company_erp_id character varying(100),
  email character varying(255),
  office_phone character varying(50),
  cell_phone character varying(50),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  PRIMARY KEY (id),
  CONSTRAINT uq_users_tenant_user UNIQUE (tenant_id, user_id)
);

-- ======================================
-- STATISTICS TARGETS FOR QUERY OPTIMIZER
-- ======================================
-- Increase statistics for frequently joined columns to improve cardinality estimates

ALTER TABLE users ALTER COLUMN user_id SET STATISTICS 1000;
ALTER TABLE users ALTER COLUMN tenant_id SET STATISTICS 1000;

-- ======================================
-- USERS TABLE CONSTRAINTS AND INDEXES
-- ======================================

-- Core performance index for user lookups (PostgreSQL will use the unique constraint as an index too)
CREATE INDEX IF NOT EXISTS idx_users_tenant_user_id 
ON users (tenant_id, user_id);

-- Email lookup index for search functionality in get_repeat_visit_tasks
CREATE INDEX IF NOT EXISTS idx_users_tenant_email 
ON users (tenant_id, email) 
WHERE email IS NOT NULL;
