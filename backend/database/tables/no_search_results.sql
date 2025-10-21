-- Generated schema for public.no_search_results
CREATE TABLE public.no_search_results (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  event_date date NOT NULL,
  event_timestamp character varying(50),
  user_pseudo_id character varying(255),
  user_prop_webuserid character varying(100),
  user_prop_default_branch_id character varying(100),
  param_ga_session_id character varying(100),
  param_no_search_results_term character varying(500),
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

ALTER TABLE no_search_results ALTER COLUMN user_prop_default_branch_id SET STATISTICS 1000;
ALTER TABLE no_search_results ALTER COLUMN param_ga_session_id SET STATISTICS 1000;
ALTER TABLE no_search_results ALTER COLUMN user_prop_webuserid SET STATISTICS 1000;
ALTER TABLE no_search_results ALTER COLUMN param_no_search_results_term SET STATISTICS 1000;

-- ======================================
-- NO_SEARCH_RESULTS TABLE INDEXES
-- ======================================

-- Core performance indexes - for failed search analytics
CREATE INDEX IF NOT EXISTS idx_no_search_results_tenant_date 
ON no_search_results (tenant_id, event_date);

CREATE INDEX IF NOT EXISTS idx_no_search_results_tenant_session 
ON no_search_results (tenant_id, param_ga_session_id);

CREATE INDEX IF NOT EXISTS idx_no_search_results_tenant_user 
ON no_search_results (tenant_id, user_prop_webuserid);

CREATE INDEX IF NOT EXISTS idx_no_search_results_tenant_date_branch 
ON no_search_results (tenant_id, event_date, user_prop_default_branch_id);

CREATE INDEX IF NOT EXISTS idx_no_search_results_term 
ON no_search_results (tenant_id, param_no_search_results_term);

-- Time-series index for dashboard
CREATE INDEX IF NOT EXISTS idx_no_search_results_time_series 
ON no_search_results (tenant_id, event_date DESC, event_timestamp DESC);

-- Partial index for recent data
CREATE INDEX IF NOT EXISTS idx_no_search_results_recent 
ON no_search_results (tenant_id, event_date DESC) 
WHERE event_date >= '2024-01-01';