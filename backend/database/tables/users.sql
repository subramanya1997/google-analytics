-- Generated schema for public.users
CREATE TABLE IF NOT EXISTS public.users (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  user_id character varying(100),
  user_name character varying(255),
  first_name character varying(255),
  middle_name character varying(255),
  last_name character varying(255),
  job_title character varying(255),
  user_erp_id character varying(100),
  fax character varying(50),
  address1 character varying(255),
  address2 character varying(255),
  address3 character varying(255),
  city character varying(100),
  state character varying(100),
  country character varying(100),
  office_phone character varying(50),
  cell_phone character varying(50),
  email character varying(255),
  registered_date timestamp with time zone,
  zip character varying(20),
  warehouse_code character varying(100),
  last_login_date timestamp with time zone,
  cimm_buying_company_id character varying(100),
  buying_company_name character varying(255),
  buying_company_erp_id character varying(100),
  role_name character varying(100),
  site_name character varying(255),
  is_active boolean NOT NULL,
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