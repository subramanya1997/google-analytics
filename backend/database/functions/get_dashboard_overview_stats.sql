-- Definition for function public.get_dashboard_overview_stats (oid=217039)
CREATE OR REPLACE FUNCTION public.get_dashboard_overview_stats(p_tenant_id uuid, p_start_date text, p_end_date text, p_location_id text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    result JSONB;
BEGIN
    WITH date_range AS (
        SELECT TO_DATE(p_start_date, 'YYYY-MM-DD') as start_date, TO_DATE(p_end_date, 'YYYY-MM-DD') as end_date
    ),
    purchase_stats AS (
        SELECT
            SUM(ecommerce_purchase_revenue) as total_revenue,
            COUNT(*) as total_purchases,
            COUNT(DISTINCT param_ga_session_id) as purchase_sessions
        FROM purchase
        WHERE tenant_id = p_tenant_id 
          AND event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
          AND (p_location_id IS NULL OR user_prop_default_branch_id = p_location_id)
    ),
    visitor_stats AS (
        SELECT
            COUNT(DISTINCT param_ga_session_id) as total_visitors,
            COUNT(DISTINCT user_prop_webuserid) as unique_users
        FROM page_view
        WHERE tenant_id = p_tenant_id 
          AND event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
          AND (p_location_id IS NULL OR user_prop_default_branch_id = p_location_id)
    ),
    cart_stats AS (
        SELECT
            COUNT(DISTINCT ac.param_ga_session_id) as abandoned_cart_sessions
        FROM add_to_cart ac
        WHERE ac.tenant_id = p_tenant_id 
          AND ac.event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
          AND (p_location_id IS NULL OR ac.user_prop_default_branch_id = p_location_id)
          AND NOT EXISTS (
              SELECT 1 FROM purchase p
              WHERE p.param_ga_session_id = ac.param_ga_session_id
                AND p.tenant_id = p_tenant_id
          )
    ),
    search_stats AS (
        SELECT
            COUNT(*) as total_searches,
            (SELECT COUNT(*) FROM no_search_results 
             WHERE tenant_id = p_tenant_id 
               AND event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
               AND (p_location_id IS NULL OR user_prop_default_branch_id = p_location_id)
            ) as failed_searches
        FROM view_search_results
        WHERE tenant_id = p_tenant_id 
          AND event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
          AND (p_location_id IS NULL OR user_prop_default_branch_id = p_location_id)
    ),
    repeat_visit_stats AS (
        SELECT COUNT(*) as repeat_visitors
        FROM (
            SELECT user_prop_webuserid
            FROM page_view
            WHERE tenant_id = p_tenant_id 
              AND event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
              AND (p_location_id IS NULL OR user_prop_default_branch_id = p_location_id)
              AND user_prop_webuserid IS NOT NULL
            GROUP BY user_prop_webuserid
            HAVING COUNT(DISTINCT param_ga_session_id) > 1
        ) multi_session_users
    )
    SELECT jsonb_build_object(
        'totalRevenue', '$' || COALESCE(ps.total_revenue, 0)::text,
        'purchases', COALESCE(ps.total_purchases, 0),
        'totalVisitors', COALESCE(vs.total_visitors, 0),
        'uniqueUsers', COALESCE(vs.unique_users, 0),
        'abandonedCarts', COALESCE(cs.abandoned_cart_sessions, 0),
        'totalSearches', COALESCE(ss.total_searches, 0),
        'failedSearches', COALESCE(ss.failed_searches, 0),
        'repeatVisits', COALESCE(rvs.repeat_visitors, 0),
        'conversionRate', CASE 
            WHEN COALESCE(vs.total_visitors, 0) > 0 
            THEN ROUND((COALESCE(ps.total_purchases, 0)::NUMERIC / vs.total_visitors) * 100, 2)
            ELSE 0 
        END
    )
    INTO result
    FROM purchase_stats ps
    CROSS JOIN visitor_stats vs
    CROSS JOIN cart_stats cs
    CROSS JOIN search_stats ss
    CROSS JOIN repeat_visit_stats rvs;

    RETURN COALESCE(result, '{}'::jsonb);
END;
$function$

