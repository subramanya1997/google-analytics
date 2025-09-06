-- ============================================
-- MINIMAL OPTIMIZED VERSION
-- Only what's needed for get_locations_with_activity_table
-- ============================================

-- Create essential indexes for optimal performance
CREATE INDEX IF NOT EXISTS idx_locations_tenant_active 
ON locations(tenant_id, is_active) 
WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_page_view_branch 
ON page_view(user_prop_default_branch_id);

-- Optional but recommended: Covering index for index-only scans
CREATE INDEX IF NOT EXISTS idx_locations_covering 
ON locations(tenant_id, warehouse_code, warehouse_name, city, state) 
WHERE is_active = true;

-- Main table-returning function (fastest and most flexible)
CREATE OR REPLACE FUNCTION get_locations_with_activity_table(
    p_tenant_id TEXT
)
RETURNS TABLE(
    location_id TEXT,
    location_name TEXT,
    city TEXT,
    state TEXT
)
LANGUAGE sql
STABLE
PARALLEL SAFE
AS $$
    SELECT DISTINCT 
        l.warehouse_code AS location_id,
        l.warehouse_name AS location_name,
        l.city,
        l.state
    FROM locations l
    INNER JOIN page_view pv ON pv.user_prop_default_branch_id = l.warehouse_code
    WHERE l.tenant_id = p_tenant_id 
      AND l.is_active = true
    ORDER BY l.warehouse_name;
$$;

-- Note: Keep the indexes as they improve query performance!