-- Generated schema for public.locations
CREATE TABLE IF NOT EXISTS public.locations (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  warehouse_id character varying(100),
  warehouse_code character varying(100),
  warehouse_name character varying(255),
  address1 character varying(255),
  address2 character varying(255),
  address3 character varying(255),
  country character varying(100),
  city character varying(100),
  state character varying(100),
  zip character varying(20),
  user_edited character varying(255),
  updated_datetime timestamp with time zone,
  email character varying(255),
  phone_number character varying(50),
  keywords character varying(500),
  subset_id character varying(100),
  fax character varying(50),
  latitude character varying(50),
  longitude character varying(50),
  service_manager character varying(255),
  wfl_phase_id character varying(100),
  work_hour character varying(255),
  note character varying(1000),
  ac character varying(100),
  branch_location_id character varying(100),
  toll_free_number character varying(50),
  status character varying(50),
  cne_batch_id character varying(100),
  external_system_ref_id character varying(100),
  is_active boolean NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  PRIMARY KEY (id),
  CONSTRAINT uq_locations_tenant_warehouse UNIQUE (tenant_id, warehouse_id)
);

-- ======================================
-- STATISTICS TARGETS FOR QUERY OPTIMIZER
-- ======================================
-- Increase statistics for frequently joined columns to improve cardinality estimates

ALTER TABLE locations ALTER COLUMN warehouse_code SET STATISTICS 1000;
ALTER TABLE locations ALTER COLUMN tenant_id SET STATISTICS 1000;

-- ======================================
-- LOCATIONS TABLE CONSTRAINTS AND INDEXES  
-- ======================================

-- Core performance index for location lookups 
CREATE INDEX IF NOT EXISTS idx_locations_tenant_location 
ON locations (tenant_id, warehouse_code) WHERE is_active = true;