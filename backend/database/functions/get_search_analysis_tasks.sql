-- Definition for function public.get_search_analysis_tasks (oid=217034)
CREATE OR REPLACE FUNCTION public.get_search_analysis_tasks(p_tenant_id uuid, p_page integer, p_limit integer, p_query text DEFAULT NULL::text, p_location_id text DEFAULT NULL::text, p_start_date text DEFAULT NULL::text, p_end_date text DEFAULT NULL::text, p_include_converted boolean DEFAULT false)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    result JSONB;
BEGIN
    WITH failed_searches AS (
        SELECT
            nsr.param_ga_session_id,
            nsr.user_prop_webuserid,
            nsr.param_no_search_results_term AS search_term,
            'no_results' AS search_type,
            COUNT(*) AS search_count,
            MAX(nsr.event_timestamp) AS last_activity
        FROM no_search_results nsr
        WHERE nsr.tenant_id = p_tenant_id
          AND (p_location_id IS NULL OR nsr.user_prop_default_branch_id = p_location_id)
          AND (p_start_date IS NULL OR nsr.event_date >= TO_DATE(p_start_date, 'YYYY-MM-DD'))
          AND (p_end_date IS NULL OR nsr.event_date <= TO_DATE(p_end_date, 'YYYY-MM-DD'))
          AND (p_query IS NULL OR nsr.param_no_search_results_term ILIKE ('%' || p_query || '%'))
        GROUP BY nsr.param_ga_session_id, nsr.user_prop_webuserid, nsr.param_no_search_results_term
    ),
    unconverted_searches AS (
        SELECT
            vsr.param_ga_session_id,
            vsr.user_prop_webuserid,
            STRING_AGG(DISTINCT vsr.param_search_term, ', ') AS search_term,
            'no_conversion' AS search_type,
            COUNT(*) AS search_count,
            MAX(vsr.event_timestamp) AS last_activity
        FROM view_search_results vsr
        WHERE vsr.tenant_id = p_tenant_id
          AND (p_location_id IS NULL OR vsr.user_prop_default_branch_id = p_location_id)
          AND (p_start_date IS NULL OR vsr.event_date >= TO_DATE(p_start_date, 'YYYY-MM-DD'))
          AND (p_end_date IS NULL OR vsr.event_date <= TO_DATE(p_end_date, 'YYYY-MM-DD'))
          AND (p_query IS NULL OR vsr.param_search_term ILIKE ('%' || p_query || '%'))
          AND (p_include_converted OR NOT EXISTS (
              SELECT 1 FROM purchase p
              WHERE p.param_ga_session_id = vsr.param_ga_session_id
                AND p.tenant_id = p_tenant_id
          ))
        GROUP BY vsr.param_ga_session_id, vsr.user_prop_webuserid
        HAVING COUNT(*) > 2
    ),
    all_searches AS (
        SELECT * FROM failed_searches
        UNION ALL
        SELECT * FROM unconverted_searches
    ),
    paginated_searches AS (
        SELECT *
        FROM all_searches
        ORDER BY last_activity DESC
        LIMIT p_limit
        OFFSET (p_page - 1) * p_limit
    )
    SELECT jsonb_build_object(
        'data', (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'session_id', ps.param_ga_session_id,
                    'event_date', TO_CHAR(TO_TIMESTAMP(CAST(ps.last_activity AS BIGINT) / 1000000), 'YYYY-MM-DD'),
                    'search_term', ps.search_term,
                    'search_type', ps.search_type,
                    'search_count', ps.search_count,
                    'user_id', u.user_id,
                    'customer_name', u.buying_company_name,
                    'email', u.email,
                    'phone', u.cell_phone
                )
            )
            FROM paginated_searches ps
            LEFT JOIN users u ON u.user_id = ps.user_prop_webuserid AND u.tenant_id = p_tenant_id
        ),
        'total', (SELECT COUNT(*) FROM all_searches),
        'page', p_page,
        'limit', p_limit,
        'has_more', (p_page * p_limit) < (SELECT COUNT(*) FROM all_searches)
    ) INTO result;

    RETURN result;
END;
$function$

