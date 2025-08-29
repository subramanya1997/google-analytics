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
    session_product_views AS (
        SELECT
            rvs.param_ga_session_id,
            COUNT(DISTINCT vi.first_item_item_id) as products_viewed,
            jsonb_agg(DISTINCT 
                CASE WHEN vi.first_item_item_id IS NOT NULL THEN
                    jsonb_build_object(
                        'title', COALESCE(vi.first_item_item_name, vi.first_item_item_id),
                        'url', vi.param_page_location,
                        'category', vi.first_item_item_category,
                        'price', vi.first_item_price
                    )
                ELSE NULL END
            ) FILTER (WHERE vi.first_item_item_id IS NOT NULL) as products_details
        FROM repeat_visitor_sessions rvs
        LEFT JOIN view_item vi ON vi.param_ga_session_id = rvs.param_ga_session_id
          AND vi.tenant_id = p_tenant_id
        GROUP BY rvs.param_ga_session_id
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
                    'products_viewed', COALESCE(spv.products_viewed, 0),
                    'products_details', COALESCE(spv.products_details, '[]'::jsonb),
                    'user_id', u.user_id,
                    'customer_name', u.customer_name,
                    'email', u.email,
                    'phone', u.phone
                )
            ), '[]'::jsonb)
            FROM paginated_sessions ps
            LEFT JOIN users u ON u.user_id = CAST(ps.user_prop_webuserid AS INTEGER) AND u.tenant_id = p_tenant_id
            LEFT JOIN session_product_views spv ON spv.param_ga_session_id = ps.param_ga_session_id
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
        
        UNION ALL
        
        -- View Item (Product Views)
        SELECT
            event_timestamp,
            param_ga_session_id,
            'view_item' AS event_type,
            jsonb_build_object(
                'item_id', first_item_item_id,
                'item_name', first_item_item_name,
                'price', first_item_price,
                'category', first_item_item_category
            ) AS details
        FROM view_item
        WHERE tenant_id = p_tenant_id AND param_ga_session_id IN (SELECT param_ga_session_id FROM user_sessions)
    )
    SELECT jsonb_agg(
        ae ORDER BY ae.event_timestamp ASC
    ) INTO result
    FROM all_events ae;

    RETURN COALESCE(result, '[]'::jsonb);
END;
$$ LANGUAGE plpgsql;

-- Function to get dashboard overview statistics
CREATE OR REPLACE FUNCTION get_dashboard_overview_stats(
    p_tenant_id UUID,
    p_start_date TEXT,
    p_end_date TEXT,
    p_location_id TEXT DEFAULT NULL
)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    WITH date_range AS (
        SELECT TO_DATE(p_start_date, 'YYYY-MM-DD') as start_date, TO_DATE(p_end_date, 'YYYY-MM-DD') as end_date
    ),
    purchase_stats AS (
        SELECT
            SUM(ecommerce_purchase_revenue) as total_revenue,
            COUNT(*) as total_purchases,
            COUNT(DISTINCT param_ga_session_id) as purchase_sessions
        FROM purchase
        WHERE tenant_id = p_tenant_id 
          AND event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
          AND (p_location_id IS NULL OR user_prop_default_branch_id = p_location_id)
    ),
    visitor_stats AS (
        SELECT
            COUNT(DISTINCT param_ga_session_id) as total_visitors,
            COUNT(DISTINCT user_prop_webuserid) as unique_users
        FROM page_view
        WHERE tenant_id = p_tenant_id 
          AND event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
          AND (p_location_id IS NULL OR user_prop_default_branch_id = p_location_id)
    ),
    cart_stats AS (
        SELECT
            COUNT(DISTINCT param_ga_session_id) as cart_sessions
        FROM add_to_cart
        WHERE tenant_id = p_tenant_id 
          AND event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
          AND (p_location_id IS NULL OR user_prop_default_branch_id = p_location_id)
    ),
    search_stats AS (
        SELECT
            COUNT(*) as total_searches,
            (SELECT COUNT(*) FROM no_search_results 
             WHERE tenant_id = p_tenant_id 
               AND event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
               AND (p_location_id IS NULL OR user_prop_default_branch_id = p_location_id)
            ) as failed_searches
        FROM view_search_results
        WHERE tenant_id = p_tenant_id 
          AND event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
          AND (p_location_id IS NULL OR user_prop_default_branch_id = p_location_id)
    ),
    repeat_visit_stats AS (
        SELECT
            COUNT(DISTINCT user_prop_webuserid) as repeat_visitors
        FROM page_view
        WHERE tenant_id = p_tenant_id 
          AND event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
          AND (p_location_id IS NULL OR user_prop_default_branch_id = p_location_id)
          AND user_prop_webuserid IS NOT NULL
          AND user_prop_webuserid IN (
            SELECT user_prop_webuserid
            FROM page_view
            WHERE tenant_id = p_tenant_id
              AND event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
              AND user_prop_webuserid IS NOT NULL
            GROUP BY user_prop_webuserid
            HAVING COUNT(DISTINCT param_ga_session_id) > 1
          )
    )
    SELECT jsonb_build_object(
        'totalRevenue', '$' || COALESCE(ps.total_revenue, 0)::text,
        'purchases', COALESCE(ps.total_purchases, 0),
        'totalVisitors', COALESCE(vs.total_visitors, 0),
        'uniqueUsers', COALESCE(vs.unique_users, 0),
        'abandonedCarts', COALESCE(cs.cart_sessions, 0) - COALESCE(ps.purchase_sessions, 0),
        'totalSearches', COALESCE(ss.total_searches, 0),
        'failedSearches', COALESCE(ss.failed_searches, 0),
        'repeatVisits', COALESCE(rvs.repeat_visitors, 0),
        'conversionRate', CASE 
            WHEN COALESCE(vs.total_visitors, 0) > 0 
            THEN ROUND((COALESCE(ps.total_purchases, 0)::NUMERIC / vs.total_visitors) * 100, 2)
            ELSE 0 
        END
    )
    INTO result
    FROM purchase_stats ps
    CROSS JOIN visitor_stats vs
    CROSS JOIN cart_stats cs
    CROSS JOIN search_stats ss
    CROSS JOIN repeat_visit_stats rvs;

    RETURN COALESCE(result, '{}'::jsonb);
END;
$$ LANGUAGE plpgsql;

-- Function to get bulk statistics for all locations
CREATE OR REPLACE FUNCTION get_location_stats_bulk(
    p_tenant_id UUID,
    p_start_date TEXT,
    p_end_date TEXT
)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    WITH date_range AS (
        SELECT TO_DATE(p_start_date, 'YYYY-MM-DD') as start_date, TO_DATE(p_end_date, 'YYYY-MM-DD') as end_date
    ),
    location_page_views AS (
        SELECT
            user_prop_default_branch_id AS location_id,
            COUNT(DISTINCT param_ga_session_id) AS totalVisitors
        FROM page_view
        WHERE tenant_id = p_tenant_id AND event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
        GROUP BY user_prop_default_branch_id
    ),
    location_purchases AS (
        SELECT
            user_prop_default_branch_id AS location_id,
            SUM(ecommerce_purchase_revenue) AS totalRevenue,
            COUNT(*) AS purchases
        FROM purchase
        WHERE tenant_id = p_tenant_id AND event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
        GROUP BY user_prop_default_branch_id
    ),
    abandoned_carts_by_session AS (
      SELECT DISTINCT ac.param_ga_session_id, ac.user_prop_default_branch_id as location_id
      FROM add_to_cart ac
      WHERE ac.tenant_id = p_tenant_id
        AND ac.event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
        AND NOT EXISTS (
          SELECT 1 FROM purchase p
          WHERE p.param_ga_session_id = ac.param_ga_session_id
            AND p.tenant_id = p_tenant_id
        )
    ),
    location_abandoned_carts AS (
      SELECT
        location_id,
        COUNT(param_ga_session_id) as abandonedCarts
      FROM abandoned_carts_by_session
      GROUP BY location_id
    ),
    location_failed_searches AS (
        SELECT
            user_prop_default_branch_id AS location_id,
            COUNT(*) AS failedSearches
        FROM no_search_results
        WHERE tenant_id = p_tenant_id AND event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
        GROUP BY user_prop_default_branch_id
    ),
    user_sessions_per_location AS (
        SELECT
            user_prop_webuserid,
            user_prop_default_branch_id AS location_id,
            COUNT(DISTINCT param_ga_session_id) as session_count
        FROM page_view
        WHERE tenant_id = p_tenant_id
          AND event_date BETWEEN (SELECT start_date FROM date_range) AND (SELECT end_date FROM date_range)
          AND user_prop_webuserid IS NOT NULL
          AND user_prop_default_branch_id IS NOT NULL
        GROUP BY user_prop_webuserid, user_prop_default_branch_id
    ),
    location_repeat_visits AS (
        SELECT
            location_id,
            COUNT(user_prop_webuserid) as repeatVisits
        FROM user_sessions_per_location
        WHERE session_count > 1
        GROUP BY location_id
    )
    SELECT jsonb_agg(jsonb_build_object(
        'locationId', l.warehouse_code,
        'locationName', l.warehouse_name,
        'city', l.city,
        'state', l.state,
        'totalRevenue', '$' || COALESCE(lp.totalRevenue, 0)::text,
        'purchases', COALESCE(lp.purchases, 0),
        'totalVisitors', COALESCE(lpw.totalVisitors, 0),
        'abandonedCarts', COALESCE(lac.abandonedCarts, 0),
        'repeatVisits', COALESCE(lrv.repeatVisits, 0),
        'failedSearches', COALESCE(lfs.failedSearches, 0)
    ))
    INTO result
    FROM locations l
    LEFT JOIN location_page_views lpw ON l.warehouse_code = lpw.location_id
    LEFT JOIN location_purchases lp ON l.warehouse_code = lp.location_id
    LEFT JOIN location_abandoned_carts lac ON l.warehouse_code = lac.location_id
    LEFT JOIN location_failed_searches lfs ON l.warehouse_code = lfs.location_id
    LEFT JOIN location_repeat_visits lrv ON l.warehouse_code = lrv.location_id
    WHERE l.tenant_id = p_tenant_id AND l.is_active = TRUE;

    RETURN COALESCE(result, '[]'::jsonb);
END;
$$ LANGUAGE plpgsql;

-- Function to get time-series chart data for the dashboard
CREATE OR REPLACE FUNCTION get_chart_data(
    p_tenant_id UUID,
    p_start_date TEXT,
    p_end_date TEXT,
    p_granularity TEXT,
    p_location_id TEXT DEFAULT NULL
)
RETURNS JSONB AS $$
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
$$ LANGUAGE plpgsql;

-- Function to get complete dashboard data in a single call
CREATE OR REPLACE FUNCTION get_complete_dashboard_data(
    p_tenant_id UUID,
    p_start_date TEXT,
    p_end_date TEXT,
    p_granularity TEXT DEFAULT 'daily',
    p_location_id TEXT DEFAULT NULL
)
RETURNS JSONB AS $$
DECLARE
    overview_stats JSONB;
    chart_data JSONB;
    location_stats JSONB;
BEGIN
    -- Get overview stats
    SELECT get_dashboard_overview_stats(p_tenant_id, p_start_date, p_end_date, p_location_id)
    INTO overview_stats;
    
    -- Get chart data
    SELECT get_chart_data(p_tenant_id, p_start_date, p_end_date, p_granularity, p_location_id)
    INTO chart_data;
    
    -- Always get location stats, regardless of whether a location is selected
    SELECT get_location_stats_bulk(p_tenant_id, p_start_date, p_end_date)
    INTO location_stats;
    
    RETURN jsonb_build_object(
        'metrics', overview_stats,
        'chartData', chart_data,
        'locationStats', location_stats
    );
END;
$$ LANGUAGE plpgsql;
