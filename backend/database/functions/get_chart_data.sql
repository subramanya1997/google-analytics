-- Definition for function public.get_chart_data (oid=217041)
CREATE OR REPLACE FUNCTION public.get_chart_data(p_tenant_id uuid, p_start_date text, p_end_date text, p_granularity text, p_location_id text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
DECLARE
    result JSONB;
    date_format TEXT;
    series_interval TEXT;
    use_hourly_data BOOLEAN;
BEGIN
    -- Determine if we need hourly data based on granularity
    use_hourly_data := p_granularity IN ('hourly', '4hours', '12hours');
    -- Set date format and series interval
    IF p_granularity = 'monthly' THEN
        date_format := 'YYYY-MM-01';
        series_interval := '1 day';
    ELSIF p_granularity = 'weekly' THEN
        date_format := 'IYYY-IW'; -- ISO week
        series_interval := '1 day';
    ELSIF p_granularity = 'hourly' THEN
        date_format := 'YYYY-MM-DD HH24:00';
        series_interval := '1 hour';
    ELSIF p_granularity = '4hours' THEN
        date_format := 'YYYY-MM-DD HH24:00';
        series_interval := '4 hours';
    ELSIF p_granularity = '12hours' THEN
        date_format := 'YYYY-MM-DD HH24:00';
        series_interval := '12 hours';
    ELSE -- daily
        date_format := 'YYYY-MM-DD';
        series_interval := '1 day';
    END IF;

    WITH date_series AS (
        SELECT generate_series(
            TO_TIMESTAMP(p_start_date || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS'),
            TO_TIMESTAMP(p_end_date || ' 23:59:59', 'YYYY-MM-DD HH24:MI:SS'),
            series_interval::interval
        ) as time_point
    ),
    grouped_dates AS (
        SELECT
            CASE 
                WHEN p_granularity = 'monthly' THEN TO_CHAR(DATE_TRUNC('month', time_point), date_format)
                WHEN p_granularity = 'weekly' THEN TO_CHAR(DATE_TRUNC('week', time_point), date_format)
                WHEN p_granularity = '4hours' THEN 
                    TO_CHAR(DATE_TRUNC('hour', time_point) - INTERVAL '1 hour' * (EXTRACT(HOUR FROM time_point)::int % 4), date_format)
                WHEN p_granularity = '12hours' THEN 
                    TO_CHAR(DATE_TRUNC('hour', time_point) - INTERVAL '1 hour' * (EXTRACT(HOUR FROM time_point)::int % 12), date_format)
                WHEN p_granularity = 'hourly' THEN TO_CHAR(DATE_TRUNC('hour', time_point), date_format)
                ELSE TO_CHAR(DATE_TRUNC('day', time_point), date_format)
            END as date_group,
            CASE 
                WHEN p_granularity = 'monthly' THEN DATE_TRUNC('month', time_point)
                WHEN p_granularity = 'weekly' THEN DATE_TRUNC('week', time_point)
                WHEN p_granularity = '4hours' THEN 
                    DATE_TRUNC('hour', time_point) - INTERVAL '1 hour' * (EXTRACT(HOUR FROM time_point)::int % 4)
                WHEN p_granularity = '12hours' THEN 
                    DATE_TRUNC('hour', time_point) - INTERVAL '1 hour' * (EXTRACT(HOUR FROM time_point)::int % 12)
                WHEN p_granularity = 'hourly' THEN DATE_TRUNC('hour', time_point)
                ELSE DATE_TRUNC('day', time_point)
            END as start_of_period
        FROM date_series
    ),
    unique_grouped_dates AS (
        SELECT DISTINCT date_group, start_of_period
        FROM grouped_dates
    ),
    purchases_by_period AS (
        SELECT
            CASE 
                -- For daily/weekly/monthly, use event_date (date field)
                WHEN p_granularity = 'monthly' THEN TO_CHAR(DATE_TRUNC('month', event_date::timestamp), date_format)
                WHEN p_granularity = 'weekly' THEN TO_CHAR(DATE_TRUNC('week', event_date::timestamp), date_format)
                WHEN NOT use_hourly_data THEN TO_CHAR(DATE_TRUNC('day', event_date::timestamp), date_format)
                -- For hourly granularities, convert string timestamp to timestamp (assuming microseconds since epoch)
                WHEN p_granularity = '4hours' THEN 
                    TO_CHAR(
                        DATE_TRUNC('hour', TO_TIMESTAMP(event_timestamp::bigint / 1000000.0)) - 
                        INTERVAL '1 hour' * (EXTRACT(HOUR FROM TO_TIMESTAMP(event_timestamp::bigint / 1000000.0))::int % 4), 
                        date_format
                    )
                WHEN p_granularity = '12hours' THEN 
                    TO_CHAR(
                        DATE_TRUNC('hour', TO_TIMESTAMP(event_timestamp::bigint / 1000000.0)) - 
                        INTERVAL '1 hour' * (EXTRACT(HOUR FROM TO_TIMESTAMP(event_timestamp::bigint / 1000000.0))::int % 12), 
                        date_format
                    )
                WHEN p_granularity = 'hourly' THEN 
                    TO_CHAR(DATE_TRUNC('hour', TO_TIMESTAMP(event_timestamp::bigint / 1000000.0)), date_format)
                ELSE TO_CHAR(DATE_TRUNC('day', event_date::timestamp), date_format)
            END as date_group,
            SUM(ecommerce_purchase_revenue) as revenue,
            COUNT(*) as purchases
        FROM purchase
        WHERE tenant_id = p_tenant_id
          AND event_date BETWEEN TO_DATE(p_start_date, 'YYYY-MM-DD') AND TO_DATE(p_end_date, 'YYYY-MM-DD')
          AND (p_location_id IS NULL OR user_prop_default_branch_id = p_location_id)
          -- Only include records with valid timestamp for hourly data
          AND (NOT use_hourly_data OR (event_timestamp IS NOT NULL AND event_timestamp ~ '^[0-9]+$'))
        GROUP BY date_group
    ),
    visitors_by_period AS (
        SELECT
            CASE 
                -- For daily/weekly/monthly, use event_date (date field)
                WHEN p_granularity = 'monthly' THEN TO_CHAR(DATE_TRUNC('month', event_date::timestamp), date_format)
                WHEN p_granularity = 'weekly' THEN TO_CHAR(DATE_TRUNC('week', event_date::timestamp), date_format)
                WHEN NOT use_hourly_data THEN TO_CHAR(DATE_TRUNC('day', event_date::timestamp), date_format)
                -- For hourly granularities, convert string timestamp to timestamp
                WHEN p_granularity = '4hours' THEN 
                    TO_CHAR(
                        DATE_TRUNC('hour', TO_TIMESTAMP(event_timestamp::bigint / 1000000.0)) - 
                        INTERVAL '1 hour' * (EXTRACT(HOUR FROM TO_TIMESTAMP(event_timestamp::bigint / 1000000.0))::int % 4), 
                        date_format
                    )
                WHEN p_granularity = '12hours' THEN 
                    TO_CHAR(
                        DATE_TRUNC('hour', TO_TIMESTAMP(event_timestamp::bigint / 1000000.0)) - 
                        INTERVAL '1 hour' * (EXTRACT(HOUR FROM TO_TIMESTAMP(event_timestamp::bigint / 1000000.0))::int % 12), 
                        date_format
                    )
                WHEN p_granularity = 'hourly' THEN 
                    TO_CHAR(DATE_TRUNC('hour', TO_TIMESTAMP(event_timestamp::bigint / 1000000.0)), date_format)
                ELSE TO_CHAR(DATE_TRUNC('day', event_date::timestamp), date_format)
            END as date_group,
            COUNT(DISTINCT param_ga_session_id) as visitors
        FROM page_view
        WHERE tenant_id = p_tenant_id
          AND event_date BETWEEN TO_DATE(p_start_date, 'YYYY-MM-DD') AND TO_DATE(p_end_date, 'YYYY-MM-DD')
          AND (p_location_id IS NULL OR user_prop_default_branch_id = p_location_id)
          -- Only include records with valid timestamp for hourly data
          AND (NOT use_hourly_data OR (event_timestamp IS NOT NULL AND event_timestamp ~ '^[0-9]+$'))
        GROUP BY date_group
    ),
    cart_additions_by_period AS (
        SELECT
            CASE 
                -- For daily/weekly/monthly, use event_date (date field)
                WHEN p_granularity = 'monthly' THEN TO_CHAR(DATE_TRUNC('month', event_date::timestamp), date_format)
                WHEN p_granularity = 'weekly' THEN TO_CHAR(DATE_TRUNC('week', event_date::timestamp), date_format)
                WHEN NOT use_hourly_data THEN TO_CHAR(DATE_TRUNC('day', event_date::timestamp), date_format)
                -- For hourly granularities, convert string timestamp to timestamp
                WHEN p_granularity = '4hours' THEN 
                    TO_CHAR(
                        DATE_TRUNC('hour', TO_TIMESTAMP(event_timestamp::bigint / 1000000.0)) - 
                        INTERVAL '1 hour' * (EXTRACT(HOUR FROM TO_TIMESTAMP(event_timestamp::bigint / 1000000.0))::int % 4), 
                        date_format
                    )
                WHEN p_granularity = '12hours' THEN 
                    TO_CHAR(
                        DATE_TRUNC('hour', TO_TIMESTAMP(event_timestamp::bigint / 1000000.0)) - 
                        INTERVAL '1 hour' * (EXTRACT(HOUR FROM TO_TIMESTAMP(event_timestamp::bigint / 1000000.0))::int % 12), 
                        date_format
                    )
                WHEN p_granularity = 'hourly' THEN 
                    TO_CHAR(DATE_TRUNC('hour', TO_TIMESTAMP(event_timestamp::bigint / 1000000.0)), date_format)
                ELSE TO_CHAR(DATE_TRUNC('day', event_date::timestamp), date_format)
            END as date_group,
            COUNT(*) as cart_additions
        FROM add_to_cart
        WHERE tenant_id = p_tenant_id
          AND event_date BETWEEN TO_DATE(p_start_date, 'YYYY-MM-DD') AND TO_DATE(p_end_date, 'YYYY-MM-DD')
          AND (p_location_id IS NULL OR user_prop_default_branch_id = p_location_id)
          -- Only include records with valid timestamp for hourly data
          AND (NOT use_hourly_data OR (event_timestamp IS NOT NULL AND event_timestamp ~ '^[0-9]+$'))
        GROUP BY date_group
    ),
    searches_by_period AS (
        SELECT 
            date_group,
            SUM(searches) as searches
        FROM (
            SELECT
                CASE 
                    -- For daily/weekly/monthly, use event_date (date field)
                    WHEN p_granularity = 'monthly' THEN TO_CHAR(DATE_TRUNC('month', event_date::timestamp), date_format)
                    WHEN p_granularity = 'weekly' THEN TO_CHAR(DATE_TRUNC('week', event_date::timestamp), date_format)
                    WHEN NOT use_hourly_data THEN TO_CHAR(DATE_TRUNC('day', event_date::timestamp), date_format)
                    -- For hourly granularities, convert string timestamp to timestamp
                    WHEN p_granularity = '4hours' THEN 
                        TO_CHAR(
                            DATE_TRUNC('hour', TO_TIMESTAMP(event_timestamp::bigint / 1000000.0)) - 
                            INTERVAL '1 hour' * (EXTRACT(HOUR FROM TO_TIMESTAMP(event_timestamp::bigint / 1000000.0))::int % 4), 
                            date_format
                        )
                    WHEN p_granularity = '12hours' THEN 
                        TO_CHAR(
                            DATE_TRUNC('hour', TO_TIMESTAMP(event_timestamp::bigint / 1000000.0)) - 
                            INTERVAL '1 hour' * (EXTRACT(HOUR FROM TO_TIMESTAMP(event_timestamp::bigint / 1000000.0))::int % 12), 
                            date_format
                        )
                    WHEN p_granularity = 'hourly' THEN 
                        TO_CHAR(DATE_TRUNC('hour', TO_TIMESTAMP(event_timestamp::bigint / 1000000.0)), date_format)
                    ELSE TO_CHAR(DATE_TRUNC('day', event_date::timestamp), date_format)
                END as date_group,
                COUNT(*) as searches
            FROM view_search_results
            WHERE tenant_id = p_tenant_id
              AND event_date BETWEEN TO_DATE(p_start_date, 'YYYY-MM-DD') AND TO_DATE(p_end_date, 'YYYY-MM-DD')
              AND (p_location_id IS NULL OR user_prop_default_branch_id = p_location_id)
              -- Only include records with valid timestamp for hourly data
              AND (NOT use_hourly_data OR (event_timestamp IS NOT NULL AND event_timestamp ~ '^[0-9]+$'))
            GROUP BY date_group
            
            UNION ALL
            
            SELECT
                CASE 
                    -- For daily/weekly/monthly, use event_date (date field)
                    WHEN p_granularity = 'monthly' THEN TO_CHAR(DATE_TRUNC('month', event_date::timestamp), date_format)
                    WHEN p_granularity = 'weekly' THEN TO_CHAR(DATE_TRUNC('week', event_date::timestamp), date_format)
                    WHEN NOT use_hourly_data THEN TO_CHAR(DATE_TRUNC('day', event_date::timestamp), date_format)
                    -- For hourly granularities, convert string timestamp to timestamp
                    WHEN p_granularity = '4hours' THEN 
                        TO_CHAR(
                            DATE_TRUNC('hour', TO_TIMESTAMP(event_timestamp::bigint / 1000000.0)) - 
                            INTERVAL '1 hour' * (EXTRACT(HOUR FROM TO_TIMESTAMP(event_timestamp::bigint / 1000000.0))::int % 4), 
                            date_format
                        )
                    WHEN p_granularity = '12hours' THEN 
                        TO_CHAR(
                            DATE_TRUNC('hour', TO_TIMESTAMP(event_timestamp::bigint / 1000000.0)) - 
                            INTERVAL '1 hour' * (EXTRACT(HOUR FROM TO_TIMESTAMP(event_timestamp::bigint / 1000000.0))::int % 12), 
                            date_format
                        )
                    WHEN p_granularity = 'hourly' THEN 
                        TO_CHAR(DATE_TRUNC('hour', TO_TIMESTAMP(event_timestamp::bigint / 1000000.0)), date_format)
                    ELSE TO_CHAR(DATE_TRUNC('day', event_date::timestamp), date_format)
                END as date_group,
                COUNT(*) as searches
            FROM no_search_results
            WHERE tenant_id = p_tenant_id
              AND event_date BETWEEN TO_DATE(p_start_date, 'YYYY-MM-DD') AND TO_DATE(p_end_date, 'YYYY-MM-DD')
              AND (p_location_id IS NULL OR user_prop_default_branch_id = p_location_id)
              -- Only include records with valid timestamp for hourly data
              AND (NOT use_hourly_data OR (event_timestamp IS NOT NULL AND event_timestamp ~ '^[0-9]+$'))
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
    FROM unique_grouped_dates gd
    LEFT JOIN purchases_by_period p ON gd.date_group = p.date_group
    LEFT JOIN visitors_by_period v ON gd.date_group = v.date_group
    LEFT JOIN cart_additions_by_period ca ON gd.date_group = ca.date_group
    LEFT JOIN searches_by_period s ON gd.date_group = s.date_group;

    RETURN COALESCE(result, '[]'::jsonb);
END;
$function$
