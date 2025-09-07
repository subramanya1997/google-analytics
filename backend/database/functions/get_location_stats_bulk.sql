-- Definition for function public.get_location_stats_bulk (oid=217040)
CREATE OR REPLACE FUNCTION public.get_location_stats_bulk(p_tenant_id uuid, p_start_date text, p_end_date text)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    result JSONB;
BEGIN
    WITH date_range AS (
        SELECT TO_DATE(p_start_date, 'YYYY-MM-DD') as start_date, TO_DATE(p_end_date, 'YYYY-MM-DD') as end_date
    ),
    location_page_views AS (
        SELECT
            user_prop_default_branch_id AS location_id,
            COUNT(DISTINCT param_ga_session_id) AS totalVisitors
        FROM page_view
        WHERE tenant_id = p_tenant_id AND event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
        GROUP BY user_prop_default_branch_id
    ),
    location_purchases AS (
        SELECT
            user_prop_default_branch_id AS location_id,
            SUM(ecommerce_purchase_revenue) AS totalRevenue,
            COUNT(*) AS purchases
        FROM purchase
        WHERE tenant_id = p_tenant_id AND event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
        GROUP BY user_prop_default_branch_id
    ),
    abandoned_carts_by_session AS (
      SELECT DISTINCT ac.param_ga_session_id, ac.user_prop_default_branch_id as location_id
      FROM add_to_cart ac
      WHERE ac.tenant_id = p_tenant_id
        AND ac.event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
        AND NOT EXISTS (
          SELECT 1 FROM purchase p
          WHERE p.param_ga_session_id = ac.param_ga_session_id
            AND p.tenant_id = p_tenant_id
        )
    ),
    location_abandoned_carts AS (
      SELECT
        location_id,
        COUNT(param_ga_session_id) as abandonedCarts
      FROM abandoned_carts_by_session
      GROUP BY location_id
    ),
    location_failed_searches AS (
        SELECT
            user_prop_default_branch_id AS location_id,
            COUNT(*) AS failedSearches
        FROM no_search_results
        WHERE tenant_id = p_tenant_id AND event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
        GROUP BY user_prop_default_branch_id
    ),
    user_sessions_per_location AS (
        SELECT
            user_prop_webuserid,
            user_prop_default_branch_id AS location_id,
            COUNT(DISTINCT param_ga_session_id) as session_count
        FROM page_view
        WHERE tenant_id = p_tenant_id
          AND event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
          AND user_prop_webuserid IS NOT NULL
          AND user_prop_default_branch_id IS NOT NULL
        GROUP BY user_prop_webuserid, user_prop_default_branch_id
    ),
    location_repeat_visits AS (
        SELECT
            location_id,
            COUNT(user_prop_webuserid) as repeatVisits
        FROM user_sessions_per_location
        WHERE session_count > 1
        GROUP BY location_id
    )
    SELECT jsonb_agg(jsonb_build_object(
        'locationId', l.warehouse_code,
        'locationName', l.warehouse_name,
        'city', l.city,
        'state', l.state,
        'totalRevenue', '$' || COALESCE(lp.totalRevenue, 0)::text,
        'purchases', COALESCE(lp.purchases, 0),
        'totalVisitors', COALESCE(lpw.totalVisitors, 0),
        'abandonedCarts', COALESCE(lac.abandonedCarts, 0),
        'repeatVisits', COALESCE(lrv.repeatVisits, 0),
        'failedSearches', COALESCE(lfs.failedSearches, 0)
    ))
    INTO result
    FROM locations l
    LEFT JOIN location_page_views lpw ON l.warehouse_code = lpw.location_id
    LEFT JOIN location_purchases lp ON l.warehouse_code = lp.location_id
    LEFT JOIN location_abandoned_carts lac ON l.warehouse_code = lac.location_id
    LEFT JOIN location_failed_searches lfs ON l.warehouse_code = lfs.location_id
    LEFT JOIN location_repeat_visits lrv ON l.warehouse_code = lrv.location_id
    WHERE l.tenant_id = p_tenant_id AND l.is_active = TRUE;

    RETURN COALESCE(result, '[]'::jsonb);
END;
$function$

