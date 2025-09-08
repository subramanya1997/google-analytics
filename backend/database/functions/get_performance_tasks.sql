-- Definition for function public.get_performance_tasks (oid=217036)
CREATE OR REPLACE FUNCTION public.get_performance_tasks(p_tenant_id uuid, p_page integer, p_limit integer, p_location_id text DEFAULT NULL::text, p_start_date text DEFAULT NULL::text, p_end_date text DEFAULT NULL::text)
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
        SELECT *
        FROM session_page_counts
        WHERE page_view_count = 1
    ),
    paginated_sessions AS (
        SELECT *
        FROM bounced_sessions
        ORDER BY last_activity DESC
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
        LIMIT 10 -- Top 10 bounced pages
    )
    SELECT jsonb_build_object(
        'data', jsonb_build_object(
            'bounced_sessions', (
                SELECT COALESCE(jsonb_agg(
                    jsonb_build_object(
                        'session_id', ps.param_ga_session_id,
                        'event_date', TO_CHAR(TO_TIMESTAMP(CAST(ps.last_activity AS BIGINT) / 1000000), 'YYYY-MM-DD'),
                        'entry_page', ps.entry_page,
                        'user_id', u.user_id,
                        'customer_name', u.buying_company_name,
                        'email', u.email,
                        'phone', u.cell_phone,
                        'office_phone', u.office_phone
                    )
                ), '[]'::jsonb)
                FROM paginated_sessions ps
                LEFT JOIN users u ON u.user_id = ps.user_prop_webuserid AND u.tenant_id = p_tenant_id
            ),
            'frequently_bounced_pages', (
                SELECT COALESCE(jsonb_agg(fbp), '[]'::jsonb)
                FROM frequently_bounced_pages fbp
            )
        ),
        'total', (SELECT COUNT(*) FROM bounced_sessions),
        'page', p_page,
        'limit', p_limit,
        'has_more', (p_page * p_limit) < (SELECT COUNT(*) FROM bounced_sessions)
    ) INTO result;

    RETURN result;
END;
$function$

