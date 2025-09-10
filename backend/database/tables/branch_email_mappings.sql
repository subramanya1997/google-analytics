-- Generated schema for public.branch_email_mappings
CREATE TABLE public.branch_email_mappings (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  branch_code character varying(100) NOT NULL,
  branch_name character varying(255),
  sales_rep_email character varying(255) NOT NULL,
  sales_rep_name character varying(255),
  is_enabled boolean NOT NULL DEFAULT true,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  PRIMARY KEY (id),
  CONSTRAINT uq_branch_rep_mapping UNIQUE (tenant_id, branch_code, sales_rep_email)
);

-- ======================================
-- BRANCH_EMAIL_MAPPINGS TABLE INDEXES
-- ======================================

-- Core performance index for tenant lookups
CREATE INDEX IF NOT EXISTS idx_branch_email_mappings_tenant 
ON branch_email_mappings (tenant_id) WHERE is_enabled = true;

-- Index for branch code lookups
CREATE INDEX IF NOT EXISTS idx_branch_email_mappings_branch 
ON branch_email_mappings (tenant_id, branch_code) WHERE is_enabled = true;

-- Index for email lookups (for management interfaces)
CREATE INDEX IF NOT EXISTS idx_branch_email_mappings_email 
ON branch_email_mappings (tenant_id, sales_rep_email) WHERE is_enabled = true;
