-- Definition for function public.get_locations
-- Uses covering index idx_locations_tenant_name_covering for index-only scan
CREATE OR REPLACE FUNCTION public.get_locations(p_tenant_id uuid)
 RETURNS TABLE(location_id text, location_name text, city text, state text)
 LANGUAGE sql
 STABLE PARALLEL SAFE
AS $function$
    SELECT 
        warehouse_code AS location_id,
        warehouse_name AS location_name,
        city,
        state
    FROM locations 
    WHERE tenant_id = p_tenant_id 
      AND is_active = true
    ORDER BY warehouse_name;
$function$
