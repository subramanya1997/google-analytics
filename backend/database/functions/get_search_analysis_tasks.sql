-- Definition for function public.get_search_analysis_tasks (oid=217034)
CREATE OR REPLACE FUNCTION public.get_search_analysis_tasks(p_tenant_id uuid, p_page integer, p_limit integer, p_query text DEFAULT NULL::text, p_location_id text DEFAULT NULL::text, p_start_date text DEFAULT NULL::text, p_end_date text DEFAULT NULL::text, p_include_converted boolean DEFAULT false, p_sort_field text DEFAULT 'search_count'::text, p_sort_order text DEFAULT 'desc'::text)
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
            MAX(nsr.user_prop_webcustomerid) AS user_prop_webcustomerid,
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
            MAX(vsr.user_prop_webcustomerid) AS user_prop_webcustomerid,
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
    all_searches_with_user AS (
        SELECT
            s.*,
            u.user_id,
            u.buying_company_name AS customer_name,
            u.email,
            u.cell_phone AS phone,
            u.office_phone,
            COUNT(*) OVER() AS total_count
        FROM all_searches s
        LEFT JOIN users u ON u.tenant_id = p_tenant_id
            AND (u.user_id = s.user_prop_webuserid
                 OR (s.user_prop_webuserid IS NULL AND u.cimm_buying_company_id = s.user_prop_webcustomerid))
    ),
    paginated_searches AS (
        SELECT *
        FROM all_searches_with_user
        ORDER BY
            CASE WHEN p_sort_field = 'search_count'  AND p_sort_order = 'desc' THEN search_count  END DESC NULLS LAST,
            CASE WHEN p_sort_field = 'search_count'  AND p_sort_order = 'asc'  THEN search_count  END ASC  NULLS LAST,
            CASE WHEN p_sort_field = 'search_term'   AND p_sort_order = 'desc' THEN search_term   END DESC NULLS LAST,
            CASE WHEN p_sort_field = 'search_term'   AND p_sort_order = 'asc'  THEN search_term   END ASC  NULLS LAST,
            CASE WHEN p_sort_field = 'customer_name' AND p_sort_order = 'desc' THEN customer_name END DESC NULLS LAST,
            CASE WHEN p_sort_field = 'customer_name' AND p_sort_order = 'asc'  THEN customer_name END ASC  NULLS LAST,
            last_activity DESC
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
                    'user_id', ps.user_id,
                    'customer_name', ps.customer_name,
                    'email', ps.email,
                    'phone', ps.phone,
                    'office_phone', ps.office_phone
                )
            )
            FROM paginated_searches ps
        ),
        'total', (SELECT MAX(total_count) FROM paginated_searches),
        'page', p_page,
        'limit', p_limit,
        'has_more', (p_page * p_limit) < (SELECT MAX(total_count) FROM paginated_searches)
    ) INTO result;

    RETURN result;
END;
$function$
