-- ULTRA-FAST combined data availability function
-- Gets BOTH summary AND breakdown in a single optimized query!

CREATE OR REPLACE FUNCTION get_data_availability_combined(p_tenant_id uuid)
RETURNS TABLE(
    result_type varchar,    -- 'summary' or 'breakdown'
    event_date date,        -- NULL for summary row
    event_type varchar,     -- 'total' for summary row
    event_count bigint,     -- total events for summary, daily count for breakdown
    earliest_date date,     -- Only populated in summary row
    latest_date date        -- Only populated in summary row  
) LANGUAGE sql STABLE AS $$
    WITH breakdown_data AS (
        -- Get all breakdown data first
        SELECT event_date, 'purchase'::varchar as event_type, COUNT(*)::bigint as event_count
        FROM purchase 
        WHERE tenant_id = p_tenant_id 
          AND event_date >= (CURRENT_DATE - INTERVAL '30 days')
        GROUP BY event_date
        
        UNION ALL
        
        SELECT event_date, 'add_to_cart'::varchar, COUNT(*)::bigint
        FROM add_to_cart
        WHERE tenant_id = p_tenant_id 
          AND event_date >= (CURRENT_DATE - INTERVAL '30 days')
        GROUP BY event_date
        
        UNION ALL
        
        SELECT event_date, 'page_view'::varchar, COUNT(*)::bigint
        FROM page_view
        WHERE tenant_id = p_tenant_id 
          AND event_date >= (CURRENT_DATE - INTERVAL '30 days')
        GROUP BY event_date
        
        UNION ALL
        
        SELECT event_date, 'view_search_results'::varchar, COUNT(*)::bigint
        FROM view_search_results
        WHERE tenant_id = p_tenant_id 
          AND event_date >= (CURRENT_DATE - INTERVAL '30 days')
        GROUP BY event_date
        
        UNION ALL
        
        SELECT event_date, 'no_search_results'::varchar, COUNT(*)::bigint
        FROM no_search_results
        WHERE tenant_id = p_tenant_id 
          AND event_date >= (CURRENT_DATE - INTERVAL '30 days')
        GROUP BY event_date
        
        UNION ALL
        
        SELECT event_date, 'view_item'::varchar, COUNT(*)::bigint
        FROM view_item
        WHERE tenant_id = p_tenant_id 
          AND event_date >= (CURRENT_DATE - INTERVAL '30 days')
        GROUP BY event_date
    ),
    all_data AS (
        -- Get ALL data (not just last 30 days) for summary calculation
        SELECT event_date, COUNT(*) as event_count FROM purchase WHERE tenant_id = p_tenant_id GROUP BY event_date
        UNION ALL
        SELECT event_date, COUNT(*) FROM add_to_cart WHERE tenant_id = p_tenant_id GROUP BY event_date
        UNION ALL  
        SELECT event_date, COUNT(*) FROM page_view WHERE tenant_id = p_tenant_id GROUP BY event_date
        UNION ALL
        SELECT event_date, COUNT(*) FROM view_search_results WHERE tenant_id = p_tenant_id GROUP BY event_date
        UNION ALL
        SELECT event_date, COUNT(*) FROM no_search_results WHERE tenant_id = p_tenant_id GROUP BY event_date
        UNION ALL
        SELECT event_date, COUNT(*) FROM view_item WHERE tenant_id = p_tenant_id GROUP BY event_date
    )
    -- Return summary row first
    SELECT 
        'summary'::varchar as result_type,
        NULL::date as event_date,
        'total'::varchar as event_type, 
        SUM(event_count)::bigint as event_count,
        MIN(event_date) as earliest_date,
        MAX(event_date) as latest_date
    FROM all_data
    
    UNION ALL
    
    -- Then return breakdown rows  
    SELECT 
        'breakdown'::varchar as result_type,
        event_date,
        event_type,
        event_count,
        NULL::date as earliest_date,
        NULL::date as latest_date
    FROM breakdown_data
    ORDER BY result_type DESC, event_date DESC, event_type;
$$;
