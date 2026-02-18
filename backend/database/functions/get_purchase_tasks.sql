-- Definition for function public.get_purchase_tasks
CREATE OR REPLACE FUNCTION public.get_purchase_tasks(p_tenant_id uuid, p_page integer, p_limit integer, p_query text DEFAULT NULL::text, p_location_id text DEFAULT NULL::text, p_start_date text DEFAULT NULL::text, p_end_date text DEFAULT NULL::text, p_sort_field text DEFAULT 'event_timestamp'::text, p_sort_order text DEFAULT 'desc'::text)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    result JSONB;
BEGIN
    WITH filtered_purchases AS (
        SELECT
            p.param_transaction_id,
            p.event_timestamp,
            p.ecommerce_purchase_revenue,
            p.param_ga_session_id,
            p.user_prop_webuserid,
            p.user_prop_webcustomerid,
            p.items_json,
            p.param_page_location,
            p.event_date
        FROM purchase p
        WHERE p.tenant_id = p_tenant_id
          AND (p_location_id IS NULL OR p.user_prop_default_branch_id = p_location_id)
          AND (p_start_date IS NULL OR p.event_date >= TO_DATE(p_start_date, 'YYYY-MM-DD'))
          AND (p_end_date IS NULL OR p.event_date <= TO_DATE(p_end_date, 'YYYY-MM-DD'))
          AND (p_query IS NULL OR p.items_json::text ILIKE '%' || p_query || '%')
    ),
    purchase_details AS (
        SELECT
            fp.param_transaction_id,
            fp.event_timestamp,
            fp.ecommerce_purchase_revenue,
            fp.param_ga_session_id,
            fp.user_prop_webuserid,
            fp.items_json,
            fp.param_page_location,
            fp.event_date,
            u.user_id,
            u.buying_company_name AS customer_name,
            u.email,
            u.cell_phone AS phone,
            u.office_phone,
            false AS completed,
            COUNT(*) OVER() AS total_count
        FROM filtered_purchases fp
        LEFT JOIN users u ON u.tenant_id = p_tenant_id
            AND (u.user_id = fp.user_prop_webuserid
                 OR (fp.user_prop_webuserid IS NULL AND u.buying_company_erp_id = fp.user_prop_webcustomerid))
    ),
    paginated_purchases AS (
        SELECT *
        FROM purchase_details
        ORDER BY
            CASE WHEN p_sort_field = 'event_timestamp' AND p_sort_order = 'desc' THEN event_timestamp           END DESC NULLS LAST,
            CASE WHEN p_sort_field = 'event_timestamp' AND p_sort_order = 'asc'  THEN event_timestamp           END ASC  NULLS LAST,
            CASE WHEN p_sort_field = 'order_value'     AND p_sort_order = 'desc' THEN ecommerce_purchase_revenue END DESC NULLS LAST,
            CASE WHEN p_sort_field = 'order_value'     AND p_sort_order = 'asc'  THEN ecommerce_purchase_revenue END ASC  NULLS LAST,
            CASE WHEN p_sort_field = 'customer_name'   AND p_sort_order = 'desc' THEN customer_name              END DESC NULLS LAST,
            CASE WHEN p_sort_field = 'customer_name'   AND p_sort_order = 'asc'  THEN customer_name              END ASC  NULLS LAST,
            event_timestamp DESC
        LIMIT p_limit
        OFFSET (p_page - 1) * p_limit
    )
    SELECT jsonb_build_object(
        'data', (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'transaction_id', pp.param_transaction_id,
                    'event_date', TO_CHAR(TO_TIMESTAMP(CAST(pp.event_timestamp AS BIGINT) / 1000000), 'YYYY-MM-DD'),
                    'order_value', COALESCE(pp.ecommerce_purchase_revenue, 0),
                    'page_location', COALESCE(pp.param_page_location, ''),
                    'ga_session_id', pp.param_ga_session_id,
                    'user_id', pp.user_id,
                    'customer_name', pp.customer_name,
                    'email', pp.email,
                    'phone', pp.phone,
                    'office_phone', pp.office_phone,
                    'products', COALESCE(pp.items_json, '[]'::jsonb),
                    'completed', pp.completed
                )
            )
            FROM paginated_purchases pp
        ),
        'total', (SELECT MAX(total_count) FROM paginated_purchases),
        'page', p_page,
        'limit', p_limit,
        'has_more', (p_page * p_limit) < (SELECT MAX(total_count) FROM paginated_purchases)
    ) INTO result;

    RETURN result;
END;
$function$
