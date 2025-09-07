-- Definition for function public.get_chart_data (oid=217041)
CREATE OR REPLACE FUNCTION public.get_chart_data(p_tenant_id uuid, p_start_date text, p_end_date text, p_granularity text, p_location_id text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    result JSONB;
    date_format TEXT;
BEGIN
    -- Determine date format based on granularity
    IF p_granularity = 'monthly' THEN
        date_format := 'YYYY-MM-01';
    ELSIF p_granularity = 'weekly' THEN
        date_format := 'IYYY-IW'; -- ISO week
    ELSE
        date_format := 'YYYY-MM-DD';
    END IF;

    WITH date_series AS (
        SELECT generate_series(
            TO_DATE(p_start_date, 'YYYY-MM-DD'),
            TO_DATE(p_end_date, 'YYYY-MM-DD'),
            '1 day'::interval
        )::date as day
    ),
    grouped_dates AS (
        SELECT
            TO_CHAR(day, date_format) as date_group,
            MIN(day) as start_of_period
        FROM date_series
        GROUP BY date_group
    ),
    purchases_by_period AS (
        SELECT
            TO_CHAR(event_date, date_format) as date_group,
            SUM(ecommerce_purchase_revenue) as revenue,
            COUNT(*) as purchases
        FROM purchase
        WHERE tenant_id = p_tenant_id
          AND event_date BETWEEN TO_DATE(p_start_date, 'YYYY-MM-DD') AND TO_DATE(p_end_date, 'YYYY-MM-DD')
          AND (p_location_id IS NULL OR user_prop_default_branch_id = p_location_id)
        GROUP BY date_group
    ),
    visitors_by_period AS (
        SELECT
            TO_CHAR(event_date, date_format) as date_group,
            COUNT(DISTINCT param_ga_session_id) as visitors
        FROM page_view
        WHERE tenant_id = p_tenant_id
          AND event_date BETWEEN TO_DATE(p_start_date, 'YYYY-MM-DD') AND TO_DATE(p_end_date, 'YYYY-MM-DD')
          AND (p_location_id IS NULL OR user_prop_default_branch_id = p_location_id)
        GROUP BY date_group
    ),
    cart_additions_by_period AS (
        SELECT
            TO_CHAR(event_date, date_format) as date_group,
            COUNT(*) as cart_additions
        FROM add_to_cart
        WHERE tenant_id = p_tenant_id
          AND event_date BETWEEN TO_DATE(p_start_date, 'YYYY-MM-DD') AND TO_DATE(p_end_date, 'YYYY-MM-DD')
          AND (p_location_id IS NULL OR user_prop_default_branch_id = p_location_id)
        GROUP BY date_group
    ),
    searches_by_period AS (
        SELECT 
            date_group,
            SUM(searches) as searches
        FROM (
            SELECT
                TO_CHAR(event_date, date_format) as date_group,
                COUNT(*) as searches
            FROM view_search_results
            WHERE tenant_id = p_tenant_id
              AND event_date BETWEEN TO_DATE(p_start_date, 'YYYY-MM-DD') AND TO_DATE(p_end_date, 'YYYY-MM-DD')
              AND (p_location_id IS NULL OR user_prop_default_branch_id = p_location_id)
            GROUP BY date_group
            
            UNION ALL
            
            SELECT
                TO_CHAR(event_date, date_format) as date_group,
                COUNT(*) as searches
            FROM no_search_results
            WHERE tenant_id = p_tenant_id
              AND event_date BETWEEN TO_DATE(p_start_date, 'YYYY-MM-DD') AND TO_DATE(p_end_date, 'YYYY-MM-DD')
              AND (p_location_id IS NULL OR user_prop_default_branch_id = p_location_id)
            GROUP BY date_group
        ) combined_searches
        GROUP BY date_group
    )
    SELECT jsonb_agg(jsonb_build_object(
        'date', gd.start_of_period,
        'time', gd.start_of_period,
        'revenue', COALESCE(p.revenue, 0),
        'purchases', COALESCE(p.purchases, 0),
        'visitors', COALESCE(v.visitors, 0),
        'carts', COALESCE(ca.cart_additions, 0),
        'searches', COALESCE(s.searches, 0)
    ) ORDER BY gd.start_of_period)
    INTO result
    FROM grouped_dates gd
    LEFT JOIN purchases_by_period p ON gd.date_group = p.date_group
    LEFT JOIN visitors_by_period v ON gd.date_group = v.date_group
    LEFT JOIN cart_additions_by_period ca ON gd.date_group = ca.date_group
    LEFT JOIN searches_by_period s ON gd.date_group = s.date_group;

    RETURN COALESCE(result, '[]'::jsonb);
END;
$function$

