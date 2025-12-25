-- Definition for function public.get_session_history (oid=217037)
CREATE OR REPLACE FUNCTION public.get_session_history(p_tenant_id uuid, p_session_id text)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
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
                'items', COALESCE(items_json::text, '[]')
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
        
        UNION ALL
        
        -- View Item (Product Views)
        SELECT
            event_timestamp,
            'view_item' AS event_type,
            jsonb_build_object(
                'item_id', first_item_item_id,
                'item_name', first_item_item_name,
                'price', first_item_price,
                'category', first_item_item_category
            ) AS details
        FROM view_item
        WHERE tenant_id = p_tenant_id AND param_ga_session_id = p_session_id
    )
    SELECT jsonb_agg(
        ae ORDER BY ae.event_timestamp ASC
    ) INTO result
    FROM all_events ae;

    RETURN COALESCE(result, '[]'::jsonb);
END;
$function$

