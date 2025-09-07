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
-- VIEW_ITEM TABLE INDEXES
-- ======================================

-- Core performance indexes - for product analytics
CREATE INDEX IF NOT EXISTS idx_view_item_tenant_date 
ON view_item (tenant_id, event_date);

CREATE INDEX IF NOT EXISTS idx_view_item_tenant_session 
ON view_item (tenant_id, param_ga_session_id);

-- JSONB index for product search
CREATE INDEX IF NOT EXISTS idx_view_item_items_gin 
ON view_item USING GIN (items_json) 
WHERE items_json IS NOT NULL;