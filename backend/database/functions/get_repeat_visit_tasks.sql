-- Definition for function public.get_repeat_visit_tasks (oid=217035)
CREATE OR REPLACE FUNCTION public.get_repeat_visit_tasks(p_tenant_id uuid, p_page integer, p_limit integer, p_query text DEFAULT NULL::text, p_location_id text DEFAULT NULL::text, p_start_date text DEFAULT NULL::text, p_end_date text DEFAULT NULL::text, p_sort_field text DEFAULT 'page_views_count'::text, p_sort_order text DEFAULT 'desc'::text)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    result JSONB;
BEGIN
    WITH active_sessions AS (
        SELECT
            pv.param_ga_session_id,
            pv.user_prop_webuserid,
            MAX(pv.user_prop_webcustomerid) AS user_prop_webcustomerid,
            COUNT(DISTINCT pv.param_page_location) AS page_views_count,
            MAX(pv.event_timestamp) AS last_activity
        FROM page_view pv
        WHERE pv.tenant_id = p_tenant_id
          AND (p_location_id IS NULL OR pv.user_prop_default_branch_id = p_location_id)
          AND (p_start_date IS NULL OR pv.event_date >= TO_DATE(p_start_date, 'YYYY-MM-DD'))
          AND (p_end_date IS NULL OR pv.event_date <= TO_DATE(p_end_date, 'YYYY-MM-DD'))
        GROUP BY pv.param_ga_session_id, pv.user_prop_webuserid
        HAVING COUNT(DISTINCT pv.param_page_location) > 2
    ),
    user_session_counts AS (
        SELECT
            user_prop_webuserid,
            COUNT(param_ga_session_id) AS session_count
        FROM active_sessions
        GROUP BY user_prop_webuserid
    ),
    repeat_visitors AS (
        SELECT user_prop_webuserid
        FROM user_session_counts
        WHERE session_count > 1
    ),
    repeat_visitor_sessions AS (
        SELECT
            a_s.param_ga_session_id,
            a_s.user_prop_webuserid,
            a_s.user_prop_webcustomerid,
            a_s.page_views_count,
            a_s.last_activity
        FROM active_sessions a_s
        INNER JOIN repeat_visitors rv ON a_s.user_prop_webuserid = rv.user_prop_webuserid
    ),
    repeat_visitor_sessions_with_user AS (
        SELECT
            rvs.*,
            u.user_id,
            u.buying_company_name AS customer_name,
            u.email,
            u.cell_phone  AS phone,
            u.office_phone,
            COUNT(*) OVER() AS total_count
        FROM repeat_visitor_sessions rvs
        LEFT JOIN users u ON u.tenant_id = p_tenant_id
            AND (u.user_id = rvs.user_prop_webuserid
                 OR (rvs.user_prop_webuserid IS NULL AND u.cimm_buying_company_id = rvs.user_prop_webcustomerid))
        WHERE p_query IS NULL
           OR u.buying_company_name ILIKE ('%' || p_query || '%')
           OR u.email ILIKE ('%' || p_query || '%')
    ),
    paginated_sessions AS (
        SELECT *
        FROM repeat_visitor_sessions_with_user
        ORDER BY
            CASE WHEN p_sort_field = 'page_views_count' AND p_sort_order = 'desc' THEN page_views_count END DESC NULLS LAST,
            CASE WHEN p_sort_field = 'page_views_count' AND p_sort_order = 'asc'  THEN page_views_count END ASC  NULLS LAST,
            CASE WHEN p_sort_field = 'last_activity'    AND p_sort_order = 'desc' THEN last_activity    END DESC NULLS LAST,
            CASE WHEN p_sort_field = 'last_activity'    AND p_sort_order = 'asc'  THEN last_activity    END ASC  NULLS LAST,
            CASE WHEN p_sort_field = 'customer_name'    AND p_sort_order = 'desc' THEN customer_name    END DESC NULLS LAST,
            CASE WHEN p_sort_field = 'customer_name'    AND p_sort_order = 'asc'  THEN customer_name    END ASC  NULLS LAST,
            last_activity DESC
        LIMIT p_limit
        OFFSET (p_page - 1) * p_limit
    ),
    session_product_views AS (
        SELECT
            ps.param_ga_session_id,
            COUNT(DISTINCT vi.first_item_item_id) as products_viewed,
            jsonb_agg(DISTINCT 
                CASE WHEN vi.first_item_item_id IS NOT NULL THEN
                    jsonb_build_object(
                        'title', COALESCE(vi.first_item_item_name, vi.first_item_item_id),
                        'url', vi.param_page_location,
                        'category', vi.first_item_item_category,
                        'price', vi.first_item_price
                    )
                ELSE NULL END
            ) FILTER (WHERE vi.first_item_item_id IS NOT NULL) as products_details
        FROM paginated_sessions ps
        LEFT JOIN view_item vi ON vi.param_ga_session_id = ps.param_ga_session_id
          AND vi.tenant_id = p_tenant_id
        GROUP BY ps.param_ga_session_id
    )
    SELECT jsonb_build_object(
        'data', (
            SELECT COALESCE(jsonb_agg(
                jsonb_build_object(
                    'session_id', ps.param_ga_session_id,
                    'event_date', TO_CHAR(TO_TIMESTAMP(CAST(ps.last_activity AS BIGINT) / 1000000), 'YYYY-MM-DD'),
                    'page_views_count', ps.page_views_count,
                    'products_viewed', COALESCE(spv.products_viewed, 0),
                    'products_details', COALESCE(spv.products_details, '[]'::jsonb),
                    'user_id', ps.user_id,
                    'customer_name', ps.customer_name,
                    'email', ps.email,
                    'phone', ps.phone,
                    'office_phone', ps.office_phone
                )
            ), '[]'::jsonb)
            FROM paginated_sessions ps
            LEFT JOIN session_product_views spv ON spv.param_ga_session_id = ps.param_ga_session_id
        ),
        'total', (SELECT MAX(total_count) FROM paginated_sessions),
        'page', p_page,
        'limit', p_limit,
        'has_more', (p_page * p_limit) < (SELECT MAX(total_count) FROM paginated_sessions)
    ) INTO result;

    RETURN result;
END;
$function$
