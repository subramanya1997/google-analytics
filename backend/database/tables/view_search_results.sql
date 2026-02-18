-- Generated schema for public.view_search_results
CREATE TABLE IF NOT EXISTS public.view_search_results (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  event_date date NOT NULL,
  event_timestamp character varying(50),
  user_pseudo_id character varying(255),
  user_prop_webuserid character varying(100),
  user_prop_default_branch_id character varying(100),
  user_prop_webcustomerid character varying(100),
  param_ga_session_id character varying(100),
  param_search_term character varying(500),
  param_page_title character varying(500),
  param_page_location text,
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

ALTER TABLE view_search_results ALTER COLUMN user_prop_default_branch_id SET STATISTICS 1000;
ALTER TABLE view_search_results ALTER COLUMN param_ga_session_id SET STATISTICS 1000;
ALTER TABLE view_search_results ALTER COLUMN user_prop_webuserid SET STATISTICS 1000;
ALTER TABLE view_search_results ALTER COLUMN param_search_term SET STATISTICS 1000;

-- ======================================
-- VIEW_SEARCH_RESULTS TABLE INDEXES
-- ======================================

-- Core performance indexes - for search analytics
CREATE INDEX IF NOT EXISTS idx_view_search_results_tenant_date 
ON view_search_results (tenant_id, event_date);

CREATE INDEX IF NOT EXISTS idx_view_search_results_tenant_session 
ON view_search_results (tenant_id, param_ga_session_id);

CREATE INDEX IF NOT EXISTS idx_view_search_results_tenant_user 
ON view_search_results (tenant_id, user_prop_webuserid);

CREATE INDEX IF NOT EXISTS idx_view_search_results_tenant_date_branch 
ON view_search_results (tenant_id, event_date, user_prop_default_branch_id);

CREATE INDEX IF NOT EXISTS idx_view_search_results_term 
ON view_search_results (tenant_id, param_search_term);

-- Time-series index for dashboard
CREATE INDEX IF NOT EXISTS idx_view_search_results_time_series 
ON view_search_results (tenant_id, event_date DESC, event_timestamp DESC);

-- Specialized index for search conversion analysis
CREATE INDEX IF NOT EXISTS idx_view_search_results_session_lookup 
ON view_search_results (param_ga_session_id, tenant_id) 
WHERE param_ga_session_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_view_search_results_tenant_customer 
ON view_search_results (tenant_id, user_prop_webcustomerid)
WHERE user_prop_webcustomerid IS NOT NULL;

-- Covering index for location stats aggregations (eliminates heap lookups)
CREATE INDEX IF NOT EXISTS idx_view_search_results_location_stats_covering 
ON view_search_results (tenant_id, event_date, user_prop_default_branch_id) 
INCLUDE (param_ga_session_id, param_search_term);