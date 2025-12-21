-- Generated schema for public.page_view
CREATE TABLE public.page_view (
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
  param_page_referrer text,
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

ALTER TABLE page_view ALTER COLUMN user_prop_default_branch_id SET STATISTICS 1000;
ALTER TABLE page_view ALTER COLUMN param_ga_session_id SET STATISTICS 1000;
ALTER TABLE page_view ALTER COLUMN user_prop_webuserid SET STATISTICS 1000;

-- ======================================
-- PAGE_VIEW TABLE INDEXES
-- ======================================

-- Core performance indexes - critical for visitor analytics
CREATE INDEX IF NOT EXISTS idx_page_view_tenant_date 
ON page_view (tenant_id, event_date);

CREATE INDEX IF NOT EXISTS idx_page_view_tenant_session 
ON page_view (tenant_id, param_ga_session_id);

CREATE INDEX IF NOT EXISTS idx_page_view_tenant_user 
ON page_view (tenant_id, user_prop_webuserid);

CREATE INDEX IF NOT EXISTS idx_page_view_tenant_date_branch 
ON page_view (tenant_id, event_date, user_prop_default_branch_id);

-- Time-series index for dashboard
CREATE INDEX IF NOT EXISTS idx_page_view_time_series 
ON page_view (tenant_id, event_date DESC, event_timestamp DESC);

-- Specialized index for repeat visitor analysis
CREATE INDEX IF NOT EXISTS idx_page_view_user_session 
ON page_view (tenant_id, user_prop_webuserid, param_ga_session_id) 
WHERE user_prop_webuserid IS NOT NULL AND param_ga_session_id IS NOT NULL;

-- Partial index for recent data
CREATE INDEX IF NOT EXISTS idx_page_view_recent 
ON page_view (tenant_id, event_date DESC) 
WHERE event_date >= '2024-01-01';

-- Covering index for location stats aggregations (eliminates heap lookups)
CREATE INDEX IF NOT EXISTS idx_page_view_location_stats_covering 
ON page_view (tenant_id, event_date, user_prop_default_branch_id) 
INCLUDE (param_ga_session_id, user_prop_webuserid);