-- Definition for function public.get_cart_abandonment_tasks
CREATE OR REPLACE FUNCTION public.get_cart_abandonment_tasks(p_tenant_id uuid, p_page integer, p_limit integer, p_query text DEFAULT NULL::text, p_location_id text DEFAULT NULL::text, p_start_date text DEFAULT NULL::text, p_end_date text DEFAULT NULL::text, p_sort_field text DEFAULT 'last_activity'::text, p_sort_order text DEFAULT 'desc'::text)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    result JSONB;
BEGIN
    WITH abandoned_sessions AS (
        SELECT DISTINCT
            ac.param_ga_session_id
        FROM add_to_cart ac
        LEFT JOIN users u ON u.tenant_id = p_tenant_id
            AND (u.user_id = ac.user_prop_webuserid
                 OR (ac.user_prop_webuserid IS NULL AND u.buying_company_erp_id = ac.user_prop_webcustomerid))
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
        WHERE ac.param_ga_session_id IN (SELECT param_ga_session_id FROM abandoned_sessions)
          AND ac.tenant_id = p_tenant_id
        GROUP BY ac.param_ga_session_id, ac.user_prop_webuserid
    ),
    sessions_with_user AS (
        SELECT
            sd.*,
            u.user_id,
            u.buying_company_name AS customer_name,
            u.email,
            u.cell_phone AS phone,
            u.office_phone,
            COUNT(*) OVER() AS total_count
        FROM session_details sd
        LEFT JOIN users u ON u.tenant_id = p_tenant_id
            AND (u.user_id = sd.user_prop_webuserid
                 OR (sd.user_prop_webuserid IS NULL AND u.buying_company_erp_id = sd.user_prop_webcustomerid))
    ),
    paginated_sessions AS (
        SELECT *
        FROM sessions_with_user
        ORDER BY
            CASE WHEN p_sort_field = 'total_value'   AND p_sort_order = 'desc' THEN total_value   END DESC NULLS LAST,
            CASE WHEN p_sort_field = 'total_value'   AND p_sort_order = 'asc'  THEN total_value   END ASC  NULLS LAST,
            CASE WHEN p_sort_field = 'last_activity' AND p_sort_order = 'desc' THEN last_activity END DESC NULLS LAST,
            CASE WHEN p_sort_field = 'last_activity' AND p_sort_order = 'asc'  THEN last_activity END ASC  NULLS LAST,
            CASE WHEN p_sort_field = 'customer_name' AND p_sort_order = 'desc' THEN customer_name END DESC NULLS LAST,
            CASE WHEN p_sort_field = 'customer_name' AND p_sort_order = 'asc'  THEN customer_name END ASC  NULLS LAST,
            CASE WHEN p_sort_field = 'items_count'   AND p_sort_order = 'desc' THEN items_count   END DESC NULLS LAST,
            CASE WHEN p_sort_field = 'items_count'   AND p_sort_order = 'asc'  THEN items_count   END ASC  NULLS LAST,
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
                    'last_activity', TO_CHAR(TO_TIMESTAMP(CAST(ps.last_activity AS BIGINT) / 1000000), 'YYYY-MM-DD'),
                    'items_count', ps.items_count,
                    'total_value', ps.total_value,
                    'user_id', ps.user_id,
                    'customer_name', ps.customer_name,
                    'email', ps.email,
                    'phone', ps.phone,
                    'office_phone', ps.office_phone,
                    'products', ps.products
                )
            )
            FROM paginated_sessions ps
        ),
        'total', (SELECT MAX(total_count) FROM paginated_sessions),
        'page', p_page,
        'limit', p_limit,
        'has_more', (p_page * p_limit) < (SELECT MAX(total_count) FROM paginated_sessions)
    ) INTO result;

    RETURN result;
END;
$function$
