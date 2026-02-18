-- Definition for function public.get_performance_tasks (oid=217036)
CREATE OR REPLACE FUNCTION public.get_performance_tasks(p_tenant_id uuid, p_page integer, p_limit integer, p_location_id text DEFAULT NULL::text, p_start_date text DEFAULT NULL::text, p_end_date text DEFAULT NULL::text, p_sort_field text DEFAULT 'last_activity'::text, p_sort_order text DEFAULT 'desc'::text, p_issue_type text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    result JSONB;
BEGIN
    WITH session_page_counts AS (
        SELECT
            param_ga_session_id,
            user_prop_webuserid,
            MAX(user_prop_webcustomerid) as user_prop_webcustomerid,
            MAX(user_prop_default_branch_id) as user_prop_default_branch_id,
            COUNT(DISTINCT param_page_location) as page_view_count,
            MAX(event_timestamp) as last_activity,
            (array_agg(param_page_location ORDER BY event_timestamp))[1] as entry_page
        FROM page_view
        WHERE tenant_id = p_tenant_id
          AND (p_location_id IS NULL OR user_prop_default_branch_id = p_location_id)
          AND (p_start_date IS NULL OR event_date >= TO_DATE(p_start_date, 'YYYY-MM-DD'))
          AND (p_end_date IS NULL OR event_date <= TO_DATE(p_end_date, 'YYYY-MM-DD'))
        GROUP BY param_ga_session_id, user_prop_webuserid
    ),
    bounced_sessions AS (
        SELECT *,
            COUNT(*) OVER() as total_count
        FROM session_page_counts
        WHERE page_view_count = 1
    ),
    bounced_sessions_with_user AS (
        SELECT
            bs.*,
            u.user_id,
            u.buying_company_name AS customer_name,
            u.email,
            u.cell_phone  AS phone,
            u.office_phone,
            bs.user_prop_default_branch_id AS location_id
        FROM bounced_sessions bs
        LEFT JOIN users u ON u.tenant_id = p_tenant_id
            AND (u.user_id = bs.user_prop_webuserid
                 OR (bs.user_prop_webuserid IS NULL AND u.buying_company_erp_id = bs.user_prop_webcustomerid))
    ),
    paginated_sessions AS (
        SELECT *
        FROM bounced_sessions_with_user
        ORDER BY
            CASE WHEN p_sort_field = 'last_activity' AND p_sort_order = 'desc' THEN last_activity  END DESC NULLS LAST,
            CASE WHEN p_sort_field = 'last_activity' AND p_sort_order = 'asc'  THEN last_activity  END ASC  NULLS LAST,
            CASE WHEN p_sort_field = 'customer_name' AND p_sort_order = 'desc' THEN customer_name  END DESC NULLS LAST,
            CASE WHEN p_sort_field = 'customer_name' AND p_sort_order = 'asc'  THEN customer_name  END ASC  NULLS LAST,
            CASE WHEN p_sort_field = 'entry_page'    AND p_sort_order = 'desc' THEN entry_page     END DESC NULLS LAST,
            CASE WHEN p_sort_field = 'entry_page'    AND p_sort_order = 'asc'  THEN entry_page     END ASC  NULLS LAST,
            last_activity DESC
        LIMIT p_limit
        OFFSET (p_page - 1) * p_limit
    ),
    frequently_bounced_pages AS (
        SELECT
            entry_page,
            COUNT(*) as bounce_count
        FROM bounced_sessions
        GROUP BY entry_page
        ORDER BY bounce_count DESC
        LIMIT 10
    ),
    facet_counts AS (
        SELECT
            (SELECT MAX(total_count) FROM bounced_sessions) AS high_bounce_count,
            (SELECT COUNT(*) FROM frequently_bounced_pages) AS page_bounce_count
    )
    SELECT jsonb_build_object(
        'data', jsonb_build_object(
            'bounced_sessions', CASE WHEN p_issue_type IS NULL OR p_issue_type = 'high_bounce' THEN (
                SELECT COALESCE(jsonb_agg(
                    jsonb_build_object(
                        'session_id', ps.param_ga_session_id,
                        'event_date', TO_CHAR(TO_TIMESTAMP(CAST(ps.last_activity AS BIGINT) / 1000000), 'YYYY-MM-DD'),
                        'entry_page', ps.entry_page,
                        'user_id', ps.user_id,
                        'customer_name', ps.customer_name,
                        'email', ps.email,
                        'phone', ps.phone,
                        'office_phone', ps.office_phone
                    )
                ), '[]'::jsonb)
                FROM paginated_sessions ps
            ) ELSE '[]'::jsonb END,
            'frequently_bounced_pages', CASE WHEN p_issue_type IS NULL OR p_issue_type = 'page_bounce_issue' THEN (
                SELECT COALESCE(jsonb_agg(fbp), '[]'::jsonb)
                FROM frequently_bounced_pages fbp
            ) ELSE '[]'::jsonb END
        ),
        'facets', jsonb_build_object(
            'issue_types', (
                SELECT jsonb_agg(item ORDER BY item->>'count' DESC) FROM (
                    SELECT jsonb_build_object('value', 'high_bounce', 'label', 'High Bounce', 'count', COALESCE(fc.high_bounce_count, 0)) AS item FROM facet_counts fc
                    WHERE COALESCE(fc.high_bounce_count, 0) > 0
                    UNION ALL
                    SELECT jsonb_build_object('value', 'page_bounce_issue', 'label', 'Page Bounce', 'count', COALESCE(fc.page_bounce_count, 0)) AS item FROM facet_counts fc
                    WHERE COALESCE(fc.page_bounce_count, 0) > 0
                ) sub
            )
        ),
        'total', (SELECT MAX(total_count) FROM paginated_sessions),
        'page', p_page,
        'limit', p_limit,
        'has_more', (p_page * p_limit) < (SELECT MAX(total_count) FROM paginated_sessions)
    ) INTO result;

    RETURN result;
END;
$function$
