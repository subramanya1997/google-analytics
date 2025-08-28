-- SQL functions for the analytics service

-- Function to get cart abandonment tasks
CREATE OR REPLACE FUNCTION get_cart_abandonment_tasks(
    p_tenant_id UUID,
    p_page INT,
    p_limit INT,
    p_query TEXT DEFAULT NULL,
    p_location_id TEXT DEFAULT NULL,
    p_start_date TEXT DEFAULT NULL,
    p_end_date TEXT DEFAULT NULL
)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    WITH abandoned_sessions AS (
        SELECT DISTINCT ac.param_ga_session_id
        FROM add_to_cart ac
        WHERE ac.tenant_id = p_tenant_id
          AND (p_location_id IS NULL OR ac.user_prop_default_branch_id = p_location_id)
          AND (p_start_date IS NULL OR ac.event_date >= TO_DATE(p_start_date, 'YYYY-MM-DD'))
          AND (p_end_date IS NULL OR ac.event_date <= TO_DATE(p_end_date, 'YYYY-MM-DD'))
          AND NOT EXISTS (
              SELECT 1 FROM purchase p
              WHERE p.param_ga_session_id = ac.param_ga_session_id
                AND p.tenant_id = p_tenant_id
          )
    ),
    paginated_sessions AS (
        SELECT param_ga_session_id
        FROM abandoned_sessions
        ORDER BY param_ga_session_id
        LIMIT p_limit
        OFFSET (p_page - 1) * p_limit
    ),
    session_details AS (
        SELECT
            ac.param_ga_session_id,
            ac.user_prop_webuserid,
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
                    'customer_name', u.customer_name,
                    'email', u.email,
                    'phone', u.phone,
                    'products', sd.products
                )
            )
            FROM session_details sd
            LEFT JOIN users u ON u.user_id = CAST(sd.user_prop_webuserid AS INTEGER) AND u.tenant_id = p_tenant_id
        ),
        'total', (SELECT COUNT(*) FROM abandoned_sessions),
        'page', p_page,
        'limit', p_limit,
        'has_more', (p_page * p_limit) < (SELECT COUNT(*) FROM abandoned_sessions)
    ) INTO result;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Function to get search analysis tasks
CREATE OR REPLACE FUNCTION get_search_analysis_tasks(
    p_tenant_id UUID,
    p_page INT,
    p_limit INT,
    p_query TEXT DEFAULT NULL,
    p_location_id TEXT DEFAULT NULL,
    p_start_date TEXT DEFAULT NULL,
    p_end_date TEXT DEFAULT NULL,
    p_include_converted BOOLEAN DEFAULT FALSE
)
RETURNS JSONB AS $$
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
                    'customer_name', u.customer_name,
                    'email', u.email,
                    'phone', u.phone
                )
            )
            FROM paginated_searches ps
            LEFT JOIN users u ON u.user_id = CAST(ps.user_prop_webuserid AS INTEGER) AND u.tenant_id = p_tenant_id
        ),
        'total', (SELECT COUNT(*) FROM all_searches),
        'page', p_page,
        'limit', p_limit,
        'has_more', (p_page * p_limit) < (SELECT COUNT(*) FROM all_searches)
    ) INTO result;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Function to get repeat visit tasks
CREATE OR REPLACE FUNCTION get_repeat_visit_tasks(
    p_tenant_id UUID,
    p_page INT,
    p_limit INT,
    p_query TEXT DEFAULT NULL,
    p_location_id TEXT DEFAULT NULL,
    p_start_date TEXT DEFAULT NULL,
    p_end_date TEXT DEFAULT NULL
)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    WITH active_sessions AS (
        SELECT
            pv.param_ga_session_id,
            pv.user_prop_webuserid,
            COUNT(DISTINCT pv.param_page_location) AS page_views_count,
            MAX(pv.event_timestamp) AS last_activity
        FROM page_view pv
        WHERE pv.tenant_id = p_tenant_id
          AND (p_location_id IS NULL OR pv.user_prop_default_branch_id = p_location_id)
          AND (p_start_date IS NULL OR pv.event_date >= TO_DATE(p_start_date, 'YYYY-MM-DD'))
          AND (p_end_date IS NULL OR pv.event_date <= TO_DATE(p_end_date, 'YYYY-MM-DD'))
        GROUP BY pv.param_ga_session_id, pv.user_prop_webuserid
        HAVING COUNT(DISTINCT pv.param_page_location) > 2
    ),
    user_session_counts AS (
        SELECT
            user_prop_webuserid,
            COUNT(param_ga_session_id) AS session_count
        FROM active_sessions
        GROUP BY user_prop_webuserid
    ),
    repeat_visitors AS (
        SELECT user_prop_webuserid
        FROM user_session_counts
        WHERE session_count > 1
    ),
    repeat_visitor_sessions AS (
        SELECT
            a_s.param_ga_session_id,
            a_s.user_prop_webuserid,
            a_s.page_views_count,
            a_s.last_activity
        FROM active_sessions a_s
        INNER JOIN repeat_visitors rv ON a_s.user_prop_webuserid = rv.user_prop_webuserid
    ),
    paginated_sessions AS (
        SELECT *
        FROM repeat_visitor_sessions
        ORDER BY last_activity DESC
        LIMIT p_limit
        OFFSET (p_page - 1) * p_limit
    )
    SELECT jsonb_build_object(
        'data', (
            SELECT COALESCE(jsonb_agg(
                jsonb_build_object(
                    'session_id', ps.param_ga_session_id,
                    'event_date', TO_CHAR(TO_TIMESTAMP(CAST(ps.last_activity AS BIGINT) / 1000000), 'YYYY-MM-DD'),
                    'page_views_count', ps.page_views_count,
                    'user_id', u.user_id,
                    'customer_name', u.customer_name,
                    'email', u.email,
                    'phone', u.phone
                )
            ), '[]'::jsonb)
            FROM paginated_sessions ps
            LEFT JOIN users u ON u.user_id = CAST(ps.user_prop_webuserid AS INTEGER) AND u.tenant_id = p_tenant_id
            WHERE p_query IS NULL OR u.customer_name ILIKE ('%' || p_query || '%') OR u.email ILIKE ('%' || p_query || '%')
        ),
        'total', (SELECT COUNT(*) FROM repeat_visitor_sessions),
        'page', p_page,
        'limit', p_limit,
        'has_more', (p_page * p_limit) < (SELECT COUNT(*) FROM repeat_visitor_sessions)
    ) INTO result;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Function to get performance tasks (bounced sessions and pages)
CREATE OR REPLACE FUNCTION get_performance_tasks(
    p_tenant_id UUID,
    p_page INT,
    p_limit INT,
    p_location_id TEXT DEFAULT NULL,
    p_start_date TEXT DEFAULT NULL,
    p_end_date TEXT DEFAULT NULL
)
RETURNS JSONB AS $$
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
                        'customer_name', u.customer_name,
                        'email', u.email,
                        'phone', u.phone
                    )
                ), '[]'::jsonb)
                FROM paginated_sessions ps
                LEFT JOIN users u ON u.user_id = CAST(ps.user_prop_webuserid AS INTEGER) AND u.tenant_id = p_tenant_id
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
$$ LANGUAGE plpgsql;

-- Function to get session history
CREATE OR REPLACE FUNCTION get_session_history(
    p_tenant_id UUID,
    p_session_id TEXT
)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    WITH all_events AS (
        -- Page Views
        SELECT
            event_timestamp,
            'page_view' AS event_type,
            jsonb_build_object(
                'page_location', param_page_location,
                'page_title', param_page_title
            ) AS details
        FROM page_view
        WHERE tenant_id = p_tenant_id AND param_ga_session_id = p_session_id

        UNION ALL

        -- Add to Cart
        SELECT
            event_timestamp,
            'add_to_cart' AS event_type,
            jsonb_build_object(
                'item_id', first_item_item_id,
                'item_name', first_item_item_name,
                'price', first_item_price,
                'quantity', first_item_quantity
            ) AS details
        FROM add_to_cart
        WHERE tenant_id = p_tenant_id AND param_ga_session_id = p_session_id

        UNION ALL

        -- Purchases
        SELECT
            event_timestamp,
            'purchase' AS event_type,
            jsonb_build_object(
                'transaction_id', param_transaction_id,
                'revenue', ecommerce_purchase_revenue,
                'items', items_json
            ) AS details
        FROM purchase
        WHERE tenant_id = p_tenant_id AND param_ga_session_id = p_session_id

        UNION ALL

        -- View Search Results
        SELECT
            event_timestamp,
            'view_search_results' AS event_type,
            jsonb_build_object(
                'search_term', param_search_term
            ) AS details
        FROM view_search_results
        WHERE tenant_id = p_tenant_id AND param_ga_session_id = p_session_id
        
        UNION ALL

        -- No Search Results
        SELECT
            event_timestamp,
            'no_search_results' AS event_type,
            jsonb_build_object(
                'search_term', param_no_search_results_term
            ) AS details
        FROM no_search_results
        WHERE tenant_id = p_tenant_id AND param_ga_session_id = p_session_id
    )
    SELECT jsonb_agg(
        ae ORDER BY ae.event_timestamp ASC
    ) INTO result
    FROM all_events ae;

    RETURN COALESCE(result, '[]'::jsonb);
END;
$$ LANGUAGE plpgsql;

-- Function to get user history
CREATE OR REPLACE FUNCTION get_user_history(
    p_tenant_id UUID,
    p_user_id TEXT
)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    WITH user_sessions AS (
        SELECT DISTINCT param_ga_session_id
        FROM page_view
        WHERE tenant_id = p_tenant_id AND user_prop_webuserid = p_user_id
    ),
    all_events AS (
        -- Page Views
        SELECT
            event_timestamp,
            param_ga_session_id,
            'page_view' AS event_type,
            jsonb_build_object(
                'page_location', param_page_location,
                'page_title', param_page_title
            ) AS details
        FROM page_view
        WHERE tenant_id = p_tenant_id AND param_ga_session_id IN (SELECT param_ga_session_id FROM user_sessions)

        UNION ALL

        -- Add to Cart
        SELECT
            event_timestamp,
            param_ga_session_id,
            'add_to_cart' AS event_type,
            jsonb_build_object(
                'item_id', first_item_item_id,
                'item_name', first_item_item_name,
                'price', first_item_price,
                'quantity', first_item_quantity
            ) AS details
        FROM add_to_cart
        WHERE tenant_id = p_tenant_id AND param_ga_session_id IN (SELECT param_ga_session_id FROM user_sessions)

        UNION ALL

        -- Purchases
        SELECT
            event_timestamp,
            param_ga_session_id,
            'purchase' AS event_type,
            jsonb_build_object(
                'transaction_id', param_transaction_id,
                'revenue', ecommerce_purchase_revenue,
                'items', items_json
            ) AS details
        FROM purchase
        WHERE tenant_id = p_tenant_id AND param_ga_session_id IN (SELECT param_ga_session_id FROM user_sessions)

        UNION ALL

        -- View Search Results
        SELECT
            event_timestamp,
            param_ga_session_id,
            'view_search_results' AS event_type,
            jsonb_build_object(
                'search_term', param_search_term
            ) AS details
        FROM view_search_results
        WHERE tenant_id = p_tenant_id AND param_ga_session_id IN (SELECT param_ga_session_id FROM user_sessions)
        
        UNION ALL

        -- No Search Results
        SELECT
            event_timestamp,
            param_ga_session_id,
            'no_search_results' AS event_type,
            jsonb_build_object(
                'search_term', param_no_search_results_term
            ) AS details
        FROM no_search_results
        WHERE tenant_id = p_tenant_id AND param_ga_session_id IN (SELECT param_ga_session_id FROM user_sessions)
    )
    SELECT jsonb_agg(
        ae ORDER BY ae.event_timestamp ASC
    ) INTO result
    FROM all_events ae;

    RETURN COALESCE(result, '[]'::jsonb);
END;
$$ LANGUAGE plpgsql;
