-- Data availability summary function
-- Gets summary statistics for all event types

CREATE OR REPLACE FUNCTION get_data_availability_combined(p_tenant_id uuid)
RETURNS TABLE(
    event_count bigint,     -- total events
    earliest_date date,     -- earliest event date
    latest_date date        -- latest event date  
) LANGUAGE sql STABLE AS $$
    WITH all_data AS (
        -- Get ALL data from all event tables
        SELECT event_date FROM purchase WHERE tenant_id = p_tenant_id
        UNION ALL
        SELECT event_date FROM add_to_cart WHERE tenant_id = p_tenant_id
        UNION ALL  
        SELECT event_date FROM page_view WHERE tenant_id = p_tenant_id
        UNION ALL
        SELECT event_date FROM view_search_results WHERE tenant_id = p_tenant_id
        UNION ALL
        SELECT event_date FROM no_search_results WHERE tenant_id = p_tenant_id
        UNION ALL
        SELECT event_date FROM view_item WHERE tenant_id = p_tenant_id
    )
    -- Return summary statistics
    SELECT 
        COUNT(*)::bigint as event_count,
        MIN(event_date) as earliest_date,
        MAX(event_date) as latest_date
    FROM all_data;
$$;
