-- Definition for function public.get_purchase_tasks (oid=217032)
CREATE OR REPLACE FUNCTION public.get_purchase_tasks(p_tenant_id uuid, p_page integer, p_limit integer, p_query text DEFAULT NULL::text, p_location_id text DEFAULT NULL::text, p_start_date text DEFAULT NULL::text, p_end_date text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    result JSONB;
BEGIN
    WITH     filtered_purchases AS (
        SELECT 
            p.param_transaction_id,
            p.event_timestamp,
            p.ecommerce_purchase_revenue,
            p.param_ga_session_id,
            p.user_prop_webuserid,
            p.user_prop_webcustomerid,
            p.items_json,
            p.param_page_location,
            p.event_date,
            COUNT(*) OVER() as total_count
        FROM purchase p
        WHERE p.tenant_id = p_tenant_id
          AND (p_location_id IS NULL OR p.user_prop_default_branch_id = p_location_id)
          AND (p_start_date IS NULL OR p.event_date >= TO_DATE(p_start_date, 'YYYY-MM-DD'))
          AND (p_end_date IS NULL OR p.event_date <= TO_DATE(p_end_date, 'YYYY-MM-DD'))
          AND (p_query IS NULL OR p.items_json::text ILIKE '%' || p_query || '%')
        ORDER BY p.event_timestamp DESC
    ),
    paginated_purchases AS (
        SELECT *
        FROM filtered_purchases
        LIMIT p_limit
        OFFSET (p_page - 1) * p_limit
    ),
    purchase_details AS (
        SELECT
            pp.param_transaction_id,
            pp.event_timestamp,
            pp.ecommerce_purchase_revenue,
            pp.param_ga_session_id,
            pp.user_prop_webuserid,
            pp.items_json,
            pp.param_page_location,
            pp.event_date,
            pp.total_count,
            u.user_id,
            u.buying_company_name as customer_name,
            u.email,
            u.cell_phone as phone,
            u.office_phone as office_phone,
            false as completed
        FROM paginated_purchases pp
        LEFT JOIN users u ON u.tenant_id = p_tenant_id
            AND (u.user_id = pp.user_prop_webuserid
                 OR (pp.user_prop_webuserid IS NULL AND u.cimm_buying_company_id = pp.user_prop_webcustomerid))
    )
    SELECT jsonb_build_object(
        'data', (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'transaction_id', pd.param_transaction_id,
                    'event_date', TO_CHAR(TO_TIMESTAMP(CAST(pd.event_timestamp AS BIGINT) / 1000000), 'YYYY-MM-DD'),
                    'order_value', COALESCE(pd.ecommerce_purchase_revenue, 0),
                    'page_location', COALESCE(pd.param_page_location, ''),
                    'ga_session_id', pd.param_ga_session_id,
                    'user_id', pd.user_id,
                    'customer_name', pd.customer_name,
                    'email', pd.email,
                    'phone', pd.phone,
                    'office_phone', pd.office_phone,
                    'products', COALESCE(pd.items_json, '[]'::jsonb),
                    'completed', pd.completed
                )
            )
            FROM purchase_details pd
        ),
        'total', (SELECT MAX(total_count) FROM purchase_details),
        'page', p_page,
        'limit', p_limit,
        'has_more', (p_page * p_limit) < (SELECT MAX(total_count) FROM purchase_details)
    ) INTO result;

    RETURN result;
END;
$function$

