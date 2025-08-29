-- Complete Working Analytics Indexes
-- Tested and verified - safe to copy and paste into PostgreSQL

-- ======================================
-- CORE PERFORMANCE INDEXES
-- ======================================

-- Purchase table - most critical for analytics
CREATE INDEX IF NOT EXISTS idx_purchase_tenant_date 
ON purchase (tenant_id, event_date);

CREATE INDEX IF NOT EXISTS idx_purchase_tenant_session 
ON purchase (tenant_id, param_ga_session_id);

CREATE INDEX IF NOT EXISTS idx_purchase_tenant_user 
ON purchase (tenant_id, user_prop_webuserid);

CREATE INDEX IF NOT EXISTS idx_purchase_tenant_date_branch 
ON purchase (tenant_id, event_date, user_prop_default_branch_id);

CREATE INDEX IF NOT EXISTS idx_purchase_transaction 
ON purchase (tenant_id, param_transaction_id);

CREATE INDEX IF NOT EXISTS idx_purchase_revenue 
ON purchase (tenant_id, event_date, ecommerce_purchase_revenue) 
WHERE ecommerce_purchase_revenue IS NOT NULL;

-- Add to Cart table - critical for cart abandonment
CREATE INDEX IF NOT EXISTS idx_add_to_cart_tenant_date 
ON add_to_cart (tenant_id, event_date);

CREATE INDEX IF NOT EXISTS idx_add_to_cart_tenant_session 
ON add_to_cart (tenant_id, param_ga_session_id);

CREATE INDEX IF NOT EXISTS idx_add_to_cart_tenant_user 
ON add_to_cart (tenant_id, user_prop_webuserid);

CREATE INDEX IF NOT EXISTS idx_add_to_cart_tenant_date_branch 
ON add_to_cart (tenant_id, event_date, user_prop_default_branch_id);

-- Page View table - critical for visitor analytics
CREATE INDEX IF NOT EXISTS idx_page_view_tenant_date 
ON page_view (tenant_id, event_date);

CREATE INDEX IF NOT EXISTS idx_page_view_tenant_session 
ON page_view (tenant_id, param_ga_session_id);

CREATE INDEX IF NOT EXISTS idx_page_view_tenant_user 
ON page_view (tenant_id, user_prop_webuserid);

CREATE INDEX IF NOT EXISTS idx_page_view_tenant_date_branch 
ON page_view (tenant_id, event_date, user_prop_default_branch_id);

-- Search tables - for search analytics
CREATE INDEX IF NOT EXISTS idx_view_search_results_tenant_date 
ON view_search_results (tenant_id, event_date);

CREATE INDEX IF NOT EXISTS idx_view_search_results_tenant_session 
ON view_search_results (tenant_id, param_ga_session_id);

CREATE INDEX IF NOT EXISTS idx_view_search_results_term 
ON view_search_results (tenant_id, param_search_term);

CREATE INDEX IF NOT EXISTS idx_no_search_results_tenant_date 
ON no_search_results (tenant_id, event_date);

CREATE INDEX IF NOT EXISTS idx_no_search_results_term 
ON no_search_results (tenant_id, param_no_search_results_term);

-- View Item table - for product analytics
CREATE INDEX IF NOT EXISTS idx_view_item_tenant_date 
ON view_item (tenant_id, event_date);

CREATE INDEX IF NOT EXISTS idx_view_item_tenant_session 
ON view_item (tenant_id, param_ga_session_id);

-- ======================================
-- TIME-SERIES INDEXES FOR DASHBOARD
-- ======================================

CREATE INDEX IF NOT EXISTS idx_purchase_time_series 
ON purchase (tenant_id, event_date DESC, event_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_add_to_cart_time_series 
ON add_to_cart (tenant_id, event_date DESC, event_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_page_view_time_series 
ON page_view (tenant_id, event_date DESC, event_timestamp DESC);

-- ======================================
-- SPECIALIZED INDEXES FOR COMPLEX QUERIES
-- ======================================

-- Critical for cart abandonment detection (NOT EXISTS queries)
CREATE INDEX IF NOT EXISTS idx_purchase_session_lookup 
ON purchase (param_ga_session_id, tenant_id) 
WHERE param_ga_session_id IS NOT NULL;

-- For repeat visitor analysis
CREATE INDEX IF NOT EXISTS idx_page_view_user_session 
ON page_view (tenant_id, user_prop_webuserid, param_ga_session_id) 
WHERE user_prop_webuserid IS NOT NULL AND param_ga_session_id IS NOT NULL;

-- For search conversion analysis
CREATE INDEX IF NOT EXISTS idx_search_session_lookup 
ON view_search_results (param_ga_session_id, tenant_id) 
WHERE param_ga_session_id IS NOT NULL;

-- ======================================
-- JSONB INDEXES FOR PRODUCT SEARCH
-- ======================================

-- Product search in purchase data (for task filtering)
CREATE INDEX IF NOT EXISTS idx_purchase_items_gin 
ON purchase USING GIN (items_json) 
WHERE items_json IS NOT NULL;

-- Product search in cart data  
CREATE INDEX IF NOT EXISTS idx_add_to_cart_items_gin 
ON add_to_cart USING GIN (items_json) 
WHERE items_json IS NOT NULL;

-- Product search in view item data
CREATE INDEX IF NOT EXISTS idx_view_item_items_gin 
ON view_item USING GIN (items_json) 
WHERE items_json IS NOT NULL;

-- ======================================
-- PARTIAL INDEXES FOR RECENT DATA
-- ======================================

-- Index only recent data for faster queries on active data
-- Using fixed dates instead of CURRENT_DATE for immutability
CREATE INDEX IF NOT EXISTS idx_purchase_recent 
ON purchase (tenant_id, event_date DESC) 
WHERE event_date >= '2024-01-01';

CREATE INDEX IF NOT EXISTS idx_add_to_cart_recent 
ON add_to_cart (tenant_id, event_date DESC) 
WHERE event_date >= '2024-01-01';

CREATE INDEX IF NOT EXISTS idx_page_view_recent 
ON page_view (tenant_id, event_date DESC) 
WHERE event_date >= '2024-01-01';

-- ======================================
-- SUPPORT TABLE INDEXES
-- ======================================

-- Users table
CREATE INDEX IF NOT EXISTS idx_users_tenant_user_id 
ON users (tenant_id, user_id);

-- Locations table
CREATE INDEX IF NOT EXISTS idx_locations_tenant_location 
ON locations (tenant_id, location_id) WHERE is_active = true;

-- Task tracking
CREATE INDEX IF NOT EXISTS idx_task_tracking_tenant_task 
ON task_tracking (tenant_id, task_id, task_type);

CREATE INDEX IF NOT EXISTS idx_task_tracking_completed 
ON task_tracking (tenant_id, completed, updated_at DESC);



-- ======================================
-- UPDATE TABLE STATISTICS
-- ======================================

-- Update table statistics for optimal query planning
ANALYZE purchase, add_to_cart, page_view, view_search_results, no_search_results, view_item, users, locations, task_tracking;

