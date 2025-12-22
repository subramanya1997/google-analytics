-- Definition for function public.get_locations_with_activity_table (oid=222478)
CREATE OR REPLACE FUNCTION public.get_locations_with_activity_table(p_tenant_id uuid)
 RETURNS TABLE(location_id text, location_name text, city text, state text)
 LANGUAGE sql
 STABLE PARALLEL SAFE
AS $function$
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
$function$

