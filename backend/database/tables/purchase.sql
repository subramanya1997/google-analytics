-- Generated schema for public.purchase
CREATE TABLE public.purchase (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  event_date date NOT NULL,
  event_timestamp character varying(50),
  user_pseudo_id character varying(255),
  user_prop_webuserid character varying(100),
  user_prop_default_branch_id character varying(100),
  param_ga_session_id character varying(100),
  param_transaction_id character varying(100),
  param_page_title character varying(500),
  param_page_location text,
  ecommerce_purchase_revenue numeric(15,2),
  items_json jsonb,
  device_category character varying(50),
  device_operating_system character varying(50),
  geo_country character varying(100),
  geo_city character varying(100),
  raw_data jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  PRIMARY KEY (id)
);

-- ======================================
-- STATISTICS TARGETS FOR QUERY OPTIMIZER
-- ======================================
-- Increase statistics for frequently aggregated columns to improve cardinality estimates

ALTER TABLE purchase ALTER COLUMN user_prop_default_branch_id SET STATISTICS 1000;
ALTER TABLE purchase ALTER COLUMN param_ga_session_id SET STATISTICS 1000;
ALTER TABLE purchase ALTER COLUMN user_prop_webuserid SET STATISTICS 1000;
ALTER TABLE purchase ALTER COLUMN ecommerce_purchase_revenue SET STATISTICS 1000;

-- ======================================
-- PURCHASE TABLE INDEXES
-- ======================================

-- Core performance indexes
CREATE INDEX IF NOT EXISTS idx_purchase_tenant_date 
ON purchase (tenant_id, event_date);

CREATE INDEX IF NOT EXISTS idx_purchase_tenant_session 
ON purchase (tenant_id, param_ga_session_id);

CREATE INDEX IF NOT EXISTS idx_purchase_tenant_user 
ON purchase (tenant_id, user_prop_webuserid);

CREATE INDEX IF NOT EXISTS idx_purchase_tenant_date_branch 
ON purchase (tenant_id, event_date, user_prop_default_branch_id);

CREATE INDEX IF NOT EXISTS idx_purchase_transaction 
ON purchase (tenant_id, param_transaction_id);

CREATE INDEX IF NOT EXISTS idx_purchase_revenue 
ON purchase (tenant_id, event_date, ecommerce_purchase_revenue) 
WHERE ecommerce_purchase_revenue IS NOT NULL;

-- Time-series index for dashboard
CREATE INDEX IF NOT EXISTS idx_purchase_time_series 
ON purchase (tenant_id, event_date DESC, event_timestamp DESC);

-- Specialized index for cart abandonment detection (NOT EXISTS queries)
CREATE INDEX IF NOT EXISTS idx_purchase_session_lookup 
ON purchase (param_ga_session_id, tenant_id) 
WHERE param_ga_session_id IS NOT NULL;

-- JSONB index for product search (task filtering)
CREATE INDEX IF NOT EXISTS idx_purchase_items_gin 
ON purchase USING GIN (items_json) 
WHERE items_json IS NOT NULL;

-- Partial index for recent data
CREATE INDEX IF NOT EXISTS idx_purchase_recent 
ON purchase (tenant_id, event_date DESC) 
WHERE event_date >= '2024-01-01';

-- Covering index for location stats aggregations (eliminates heap lookups)
CREATE INDEX IF NOT EXISTS idx_purchase_location_stats_covering 
ON purchase (tenant_id, event_date, user_prop_default_branch_id) 
INCLUDE (ecommerce_purchase_revenue, param_ga_session_id);