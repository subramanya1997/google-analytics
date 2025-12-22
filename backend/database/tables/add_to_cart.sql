-- Generated schema for public.add_to_cart
CREATE TABLE IF NOT EXISTS public.add_to_cart (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  event_date date NOT NULL,
  event_timestamp character varying(50),
  user_pseudo_id character varying(255),
  user_prop_webuserid character varying(100),
  user_prop_default_branch_id character varying(100),
  param_ga_session_id character varying(100),
  param_page_title character varying(500),
  param_page_location text,
  first_item_item_id character varying(255),
  first_item_item_name character varying(500),
  first_item_item_category character varying(255),
  first_item_price numeric(10,2),
  first_item_quantity integer,
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

ALTER TABLE add_to_cart ALTER COLUMN user_prop_default_branch_id SET STATISTICS 1000;
ALTER TABLE add_to_cart ALTER COLUMN param_ga_session_id SET STATISTICS 1000;
ALTER TABLE add_to_cart ALTER COLUMN user_prop_webuserid SET STATISTICS 1000;

-- ======================================
-- ADD_TO_CART TABLE INDEXES
-- ======================================

-- Core performance indexes - critical for cart abandonment
CREATE INDEX IF NOT EXISTS idx_add_to_cart_tenant_date 
ON add_to_cart (tenant_id, event_date);

CREATE INDEX IF NOT EXISTS idx_add_to_cart_tenant_session 
ON add_to_cart (tenant_id, param_ga_session_id);

CREATE INDEX IF NOT EXISTS idx_add_to_cart_tenant_user 
ON add_to_cart (tenant_id, user_prop_webuserid);

CREATE INDEX IF NOT EXISTS idx_add_to_cart_tenant_date_branch 
ON add_to_cart (tenant_id, event_date, user_prop_default_branch_id);

-- Time-series index for dashboard
CREATE INDEX IF NOT EXISTS idx_add_to_cart_time_series 
ON add_to_cart (tenant_id, event_date DESC, event_timestamp DESC);

-- JSONB index for product search
CREATE INDEX IF NOT EXISTS idx_add_to_cart_items_gin 
ON add_to_cart USING GIN (items_json) 
WHERE items_json IS NOT NULL;

-- Partial index for recent data
CREATE INDEX IF NOT EXISTS idx_add_to_cart_recent 
ON add_to_cart (tenant_id, event_date DESC) 
WHERE event_date >= '2024-01-01';

-- Covering index for location stats aggregations (eliminates heap lookups)
CREATE INDEX IF NOT EXISTS idx_add_to_cart_location_stats_covering 
ON add_to_cart (tenant_id, event_date, user_prop_default_branch_id) 
INCLUDE (param_ga_session_id, first_item_price, first_item_quantity);