-- Generated schema for public.view_item
CREATE TABLE public.view_item (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  event_date date NOT NULL,
  event_timestamp character varying(50),
  user_pseudo_id character varying(255),
  user_prop_webuserid character varying(100),
  user_prop_default_branch_id character varying(100),
  param_ga_session_id character varying(100),
  first_item_item_id character varying(255),
  first_item_item_name character varying(500),
  first_item_item_category character varying(255),
  first_item_price numeric(10,2),
  param_page_title character varying(500),
  param_page_location text,
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

ALTER TABLE view_item ALTER COLUMN user_prop_default_branch_id SET STATISTICS 1000;
ALTER TABLE view_item ALTER COLUMN param_ga_session_id SET STATISTICS 1000;
ALTER TABLE view_item ALTER COLUMN user_prop_webuserid SET STATISTICS 1000;

-- ======================================
-- VIEW_ITEM TABLE INDEXES
-- ======================================

-- Core performance indexes - for product analytics
CREATE INDEX IF NOT EXISTS idx_view_item_tenant_date 
ON view_item (tenant_id, event_date);

CREATE INDEX IF NOT EXISTS idx_view_item_tenant_session 
ON view_item (tenant_id, param_ga_session_id);

CREATE INDEX IF NOT EXISTS idx_view_item_tenant_user 
ON view_item (tenant_id, user_prop_webuserid);

CREATE INDEX IF NOT EXISTS idx_view_item_tenant_date_branch 
ON view_item (tenant_id, event_date, user_prop_default_branch_id);

-- Time-series index for dashboard
CREATE INDEX IF NOT EXISTS idx_view_item_time_series 
ON view_item (tenant_id, event_date DESC, event_timestamp DESC);

-- JSONB index for product search
CREATE INDEX IF NOT EXISTS idx_view_item_items_gin 
ON view_item USING GIN (items_json) 
WHERE items_json IS NOT NULL;

-- Partial index for recent data
CREATE INDEX IF NOT EXISTS idx_view_item_recent 
ON view_item (tenant_id, event_date DESC) 
WHERE event_date >= '2024-01-01';