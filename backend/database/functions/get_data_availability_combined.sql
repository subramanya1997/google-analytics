-- Data availability summary function (OPTIMIZED)
-- Gets summary statistics for all event types using per-table aggregation
-- This is much faster than UNION ALL as it uses indexes on each table

CREATE OR REPLACE FUNCTION get_data_availability_combined(p_tenant_id uuid)
RETURNS TABLE(
    event_count bigint,     -- total events
    earliest_date date,     -- earliest event date
    latest_date date        -- latest event date  
) LANGUAGE sql STABLE AS $$
    WITH table_stats AS (
        -- Aggregate each table separately (uses indexes efficiently)
        SELECT COUNT(*) as cnt, MIN(event_date) as min_date, MAX(event_date) as max_date
        FROM purchase WHERE tenant_id = p_tenant_id
        UNION ALL
        SELECT COUNT(*), MIN(event_date), MAX(event_date)
        FROM add_to_cart WHERE tenant_id = p_tenant_id
        UNION ALL
        SELECT COUNT(*), MIN(event_date), MAX(event_date)
        FROM page_view WHERE tenant_id = p_tenant_id
        UNION ALL
        SELECT COUNT(*), MIN(event_date), MAX(event_date)
        FROM view_search_results WHERE tenant_id = p_tenant_id
        UNION ALL
        SELECT COUNT(*), MIN(event_date), MAX(event_date)
        FROM no_search_results WHERE tenant_id = p_tenant_id
        UNION ALL
        SELECT COUNT(*), MIN(event_date), MAX(event_date)
        FROM view_item WHERE tenant_id = p_tenant_id
    )
    -- Combine the 6 summary rows (just 6 rows to process!)
    SELECT 
        SUM(cnt)::bigint as event_count,
        MIN(min_date) as earliest_date,
        MAX(max_date) as latest_date
    FROM table_stats;
$$;
