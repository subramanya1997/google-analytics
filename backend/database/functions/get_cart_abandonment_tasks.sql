-- Definition for function public.get_cart_abandonment_tasks (oid=217033)
CREATE OR REPLACE FUNCTION public.get_cart_abandonment_tasks(p_tenant_id uuid, p_page integer, p_limit integer, p_query text DEFAULT NULL::text, p_location_id text DEFAULT NULL::text, p_start_date text DEFAULT NULL::text, p_end_date text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    result JSONB;
BEGIN
    WITH     abandoned_sessions AS (
        SELECT DISTINCT 
            ac.param_ga_session_id,
            COUNT(*) OVER() as total_count
        FROM add_to_cart ac
        LEFT JOIN users u ON u.tenant_id = p_tenant_id
            AND (u.user_id = ac.user_prop_webuserid
                 OR (ac.user_prop_webuserid IS NULL AND u.cimm_buying_company_id = ac.user_prop_webcustomerid))
        WHERE ac.tenant_id = p_tenant_id
          AND (p_location_id IS NULL OR ac.user_prop_default_branch_id = p_location_id)
          AND (p_start_date IS NULL OR ac.event_date >= TO_DATE(p_start_date, 'YYYY-MM-DD'))
          AND (p_end_date IS NULL OR ac.event_date <= TO_DATE(p_end_date, 'YYYY-MM-DD'))
          AND NOT EXISTS (
              SELECT 1 FROM purchase p
              WHERE p.param_ga_session_id = ac.param_ga_session_id
                AND p.tenant_id = p_tenant_id
          )
          AND (p_query IS NULL OR
               u.buying_company_name ILIKE '%' || p_query || '%' OR
               u.email ILIKE '%' || p_query || '%' OR
               ac.first_item_item_name ILIKE '%' || p_query || '%')
    ),
    paginated_sessions AS (
        SELECT param_ga_session_id, total_count
        FROM abandoned_sessions
        ORDER BY param_ga_session_id
        LIMIT p_limit
        OFFSET (p_page - 1) * p_limit
    ),
    session_details AS (
        SELECT
            ac.param_ga_session_id,
            ac.user_prop_webuserid,
            MAX(ac.user_prop_webcustomerid) AS user_prop_webcustomerid,
            MAX(ac.event_timestamp) AS last_activity,
            COUNT(ac.id) AS items_count,
            SUM(ac.first_item_price * ac.first_item_quantity) AS total_value,
            jsonb_agg(
                jsonb_build_object(
                    'item_id', ac.first_item_item_id,
                    'item_name', ac.first_item_item_name,
                    'item_category', ac.first_item_item_category,
                    'price', ac.first_item_price,
                    'quantity', ac.first_item_quantity
                )
            ) AS products
        FROM add_to_cart ac
        WHERE ac.param_ga_session_id IN (SELECT param_ga_session_id FROM paginated_sessions)
          AND ac.tenant_id = p_tenant_id
        GROUP BY ac.param_ga_session_id, ac.user_prop_webuserid
    )
    SELECT jsonb_build_object(
        'data', (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'session_id', sd.param_ga_session_id,
                    'event_date', TO_CHAR(TO_TIMESTAMP(CAST(sd.last_activity AS BIGINT) / 1000000), 'YYYY-MM-DD'),
                    'last_activity', TO_CHAR(TO_TIMESTAMP(CAST(sd.last_activity AS BIGINT) / 1000000), 'YYYY-MM-DD'),
                    'items_count', sd.items_count,
                    'total_value', sd.total_value,
                    'user_id', u.user_id,
                    'customer_name', u.buying_company_name,
                    'email', u.email,
                    'phone', u.cell_phone,
                    'office_phone', u.office_phone,
                    'products', sd.products
                )
            )
            FROM session_details sd
            LEFT JOIN users u ON u.tenant_id = p_tenant_id
                AND (u.user_id = sd.user_prop_webuserid
                     OR (sd.user_prop_webuserid IS NULL AND u.cimm_buying_company_id = sd.user_prop_webcustomerid))
        ),
        'total', (SELECT MAX(total_count) FROM paginated_sessions),
        'page', p_page,
        'limit', p_limit,
        'has_more', (p_page * p_limit) < (SELECT MAX(total_count) FROM paginated_sessions)
    ) INTO result;

    RETURN result;
END;
$function$

