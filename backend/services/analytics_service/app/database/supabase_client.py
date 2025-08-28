"""
Supabase client for analytics service operations
"""
import os
from typing import Dict, List, Any, Optional, Union
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from loguru import logger
from datetime import datetime, date
from uuid import UUID
import httpx


class AnalyticsSupabaseClient:
    """Supabase client for analytics operations."""
    
    def __init__(self, supabase_config: Dict[str, Any]):
        """Initialize Supabase client."""
        self.project_url = supabase_config['project_url']
        self.service_role_key = supabase_config['service_role_key']
        
        if not self.project_url or not self.service_role_key:
            raise EnvironmentError("Supabase URL and Service Key must be set")
        
        # Create client with timeout
        postgrest_timeout = httpx.Timeout(300.0)
        options = ClientOptions(postgrest_client_timeout=postgrest_timeout)
        
        self.client: Client = create_client(
            self.project_url, 
            self.service_role_key, 
            options=options
        )
        
        logger.info(f"Initialized Analytics Supabase client for {self.project_url}")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the Supabase connection."""
        try:
            # Try to access the client - this will test authentication
            result = self.client.table('tenants').select("*").limit(1).execute()
            return {
                'success': True,
                'message': 'Connection successful',
                'data': result.data if hasattr(result, 'data') else []
            }
        except Exception as e:
            error_message = str(e)
            logger.error(f"Supabase connection test failed: {error_message}")
            return {
                'success': False,
                'message': f'Connection failed: {error_message}',
                'data': []
            }
    
    # Location operations
    def get_locations(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Get all locations with activity."""
        try:
            # Get locations directly and check for activity
            locations_result = self.client.table('locations').select(
                'location_id, warehouse_code, warehouse_name, city, state'
            ).eq('tenant_id', tenant_id).eq('is_active', True).execute()
            
            locations = []
            for location in locations_result.data:
                # Check if this location has any page view activity
                activity_check = self.client.table('page_view').select(
                    'id'
                ).eq('tenant_id', tenant_id).eq(
                    'user_prop_default_branch_id', location['warehouse_code']
                ).limit(1).execute()
                
                if activity_check.data:
                    locations.append({
                        'locationId': location['warehouse_code'],
                        'locationName': location['warehouse_name'],
                        'city': location['city'],
                        'state': location['state']
                    })
            
            return locations
            
        except Exception as e:
            logger.error(f"Error fetching locations: {e}")
            # Return empty list instead of raising exception
            return []
    
    # Analytics operations
    def get_dashboard_stats(self, tenant_id: str, location_id: Optional[str] = None, 
                           start_date: Optional[str] = None, end_date: Optional[str] = None,
                           granularity: str = 'daily') -> Dict[str, Any]:
        """Get dashboard statistics."""
        try:
            # Since RPC functions don't exist, use fallback calculation
            return self._calculate_dashboard_stats_fallback(
                tenant_id, location_id, start_date, end_date
            )
            
        except Exception as e:
            logger.error(f"Error fetching dashboard stats: {e}")
            # Return fallback stats
            return self._calculate_dashboard_stats_fallback(
                tenant_id, location_id, start_date, end_date
            )
    
    def _calculate_dashboard_stats_fallback(self, tenant_id: str, location_id: Optional[str],
                                          start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
        """Fallback method to calculate dashboard stats."""
        try:
            # Base query filters
            base_filters = [('tenant_id', 'eq', tenant_id)]
            if location_id:
                base_filters.append(('user_prop_default_branch_id', 'eq', location_id))
            if start_date and end_date:
                start_formatted = start_date.replace('-', '')
                end_formatted = end_date.replace('-', '')
                base_filters.append(('event_date', 'gte', start_formatted))
                base_filters.append(('event_date', 'lte', end_formatted))

            # Fetch all necessary data in fewer queries
            
            # Purchase data
            purchase_query = self.client.table('purchase').select('ecommerce_purchase_revenue, param_ga_session_id')
            for field, op, value in base_filters:
                purchase_query = getattr(purchase_query, op)(field, value)
            purchases_result = purchase_query.execute()
            
            total_revenue = sum(
                float(p.get('ecommerce_purchase_revenue', 0) or 0) 
                for p in purchases_result.data
            )
            total_purchases = len(purchases_result.data)
            purchase_sessions = set(p.get('param_ga_session_id') for p in purchases_result.data if p.get('param_ga_session_id'))

            # Cart data
            cart_query = self.client.table('add_to_cart').select('param_ga_session_id')
            for field, op, value in base_filters:
                cart_query = getattr(cart_query, op)(field, value)
            carts_result = cart_query.execute()
            cart_sessions = set(c.get('param_ga_session_id') for c in carts_result.data if c.get('param_ga_session_id'))
            abandoned_carts = len(cart_sessions - purchase_sessions)
            
            # Failed searches
            no_results_query = self.client.table('no_search_results').select('id')
            for field, op, value in base_filters:
                no_results_query = getattr(no_results_query, op)(field, value)
            failed_searches = len(no_results_query.execute().data)

            # Page view data for visitors and repeat visits
            pageview_query = self.client.table('page_view').select('param_ga_session_id, user_prop_webuserid')
            for field, op, value in base_filters:
                pageview_query = getattr(pageview_query, op)(field, value)
            pageviews_result = pageview_query.execute()

            # Total Visitors (unique sessions)
            total_visitors = len(set(pv.get('param_ga_session_id') for pv in pageviews_result.data if pv.get('param_ga_session_id')))

            # Repeat Visits (users with more than one session)
            user_sessions = {}
            for pv in pageviews_result.data:
                user_id = pv.get('user_prop_webuserid')
                session_id = pv.get('param_ga_session_id')
                if user_id and session_id:
                    if user_id not in user_sessions:
                        user_sessions[user_id] = set()
                    user_sessions[user_id].add(session_id)
            
            repeat_visits = sum(1 for sessions in user_sessions.values() if len(sessions) > 1)

            return {
                'totalRevenue': f"${total_revenue:,.2f}",
                'purchases': total_purchases,
                'abandonedCarts': abandoned_carts,
                'failedSearches': failed_searches,
                'totalVisitors': total_visitors,
                'repeatVisits': repeat_visits
            }
            
        except Exception as e:
            logger.error(f"Error in fallback stats calculation: {e}")
            return {
                'totalRevenue': "$0.00",
                'purchases': 0,
                'abandonedCarts': 0,
                'failedSearches': 0,
                'totalVisitors': 0,
                'repeatVisits': 0
            }
    
    # Task operations
    def get_task_status(self, tenant_id: str, task_id: str, task_type: str) -> Dict[str, Any]:
        """Get task completion status."""
        try:
            result = self.client.table('task_tracking').select(
                '*'
            ).eq('tenant_id', tenant_id).eq('task_id', task_id).eq('task_type', task_type).execute()
            
            if result.data:
                task = result.data[0]
                return {
                    'taskId': task_id,
                    'taskType': task_type,
                    'completed': task.get('completed', False),
                    'notes': task.get('notes', ''),
                    'completedAt': task.get('completed_at'),
                    'completedBy': task.get('completed_by')
                }
            else:
                return {
                    'taskId': task_id,
                    'taskType': task_type,
                    'completed': False,
                    'notes': '',
                    'completedAt': None,
                    'completedBy': None
                }
                
        except Exception as e:
            logger.error(f"Error fetching task status: {e}")
            raise
    
    def update_task_status(self, tenant_id: str, task_id: str, task_type: str, 
                          completed: bool, notes: str = '', completed_by: str = '') -> Dict[str, Any]:
        """Update task completion status."""
        try:
            data = {
                'tenant_id': tenant_id,
                'task_id': task_id,
                'task_type': task_type,
                'completed': completed,
                'notes': notes,
                'completed_by': completed_by,
                'updated_at': datetime.now().isoformat()
            }
            
            if completed:
                data['completed_at'] = datetime.now().isoformat()
            
            # Use upsert to handle both insert and update
            result = self.client.table('task_tracking').upsert(
                data,
                on_conflict='tenant_id,task_id,task_type'
            ).execute()
            
            return {
                'success': True,
                'taskId': task_id,
                'taskType': task_type,
                'completed': completed
            }
            
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            raise

    # Task list operations
    def get_purchase_tasks(self, tenant_id: str, page: int, limit: int, 
                           query: Optional[str] = None, location_id: Optional[str] = None, 
                           start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Get purchase analysis tasks with pagination and filtering."""
        try:
            # Base query
            base_query = self.client.table('purchase').select(
                'param_transaction_id, param_ga_session_id, user_prop_webuserid, ecommerce_purchase_revenue, items_json, event_timestamp, user_prop_default_branch_id',
                count='exact'
            ).eq('tenant_id', tenant_id)
            
            # Apply filters
            if location_id:
                base_query = base_query.eq('user_prop_default_branch_id', location_id)
            if start_date:
                base_query = base_query.gte('event_date', start_date.replace('-', ''))
            if end_date:
                base_query = base_query.lte('event_date', end_date.replace('-', ''))

            # Apply search query
            if query:
                # This is a simplified search. A more robust implementation might use full-text search.
                base_query = base_query.ilike('items_json', f'%{query}%')

            # Apply pagination and ordering
            offset = (page - 1) * limit
            base_query = base_query.order('event_timestamp', desc=True).range(offset, offset + limit - 1)
            
            # Execute query
            result = base_query.execute()
            
            # Get total count from the result
            total_count = result.count if result.count is not None else 0

            # Process results
            tasks = []
            for item in result.data:
                user = self._get_user_details(tenant_id, item.get('user_prop_webuserid'))
                
                tasks.append({
                    'transaction_id': item.get('param_transaction_id'),
                    'event_date': self._format_event_date(item.get('event_timestamp')),
                    'order_value': float(item.get('ecommerce_purchase_revenue') or 0),
                    'page_location': '', # This information is not directly available in purchase table
                    'ga_session_id': item.get('param_ga_session_id'),
                    'user_id': user.get('user_id'),
                    'customer_name': user.get('customer_name'),
                    'email': user.get('email'),
                    'phone': user.get('phone'),
                    'products': self._parse_items_json(item.get('items_json')),
                    'completed': self._get_task_completion_status(tenant_id, item.get('param_transaction_id'), 'purchase')
                })

            return {
                'data': tasks,
                'total': total_count,
                'page': page,
                'limit': limit,
                'has_more': (page * limit) < total_count
            }

        except Exception as e:
            logger.error(f"Error fetching purchase tasks: {e}")
            raise

    def get_cart_abandonment_tasks(self, tenant_id: str, page: int, limit: int, 
                                 query: Optional[str] = None, location_id: Optional[str] = None, 
                                 start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Get cart abandonment tasks with pagination and filtering."""
        try:
            # Date filtering for subqueries
            date_filter = ""
            if start_date and end_date:
                start_formatted = start_date.replace('-', '')
                end_formatted = end_date.replace('-', '')
                date_filter = f"AND event_date BETWEEN '{start_formatted}' AND '{end_formatted}'"

            # Step 1: Find sessions that have added to cart but not purchased
            rpc_params = {
                'p_tenant_id': tenant_id,
                'p_location_id': location_id,
                'p_start_date': start_date,
                'p_end_date': end_date,
                'p_limit': limit,
                'p_offset': (page - 1) * limit
            }
            
            # Since the RPC function doesn't exist, we'll implement the logic here
            # First, get all sessions with cart activity in the date range
            cart_sessions_query = self.client.table('add_to_cart').select('param_ga_session_id').eq('tenant_id', tenant_id)
            if location_id:
                cart_sessions_query = cart_sessions_query.eq('user_prop_default_branch_id', location_id)
            if start_date:
                cart_sessions_query = cart_sessions_query.gte('event_date', start_date.replace('-', ''))
            if end_date:
                cart_sessions_query = cart_sessions_query.lte('event_date', end_date.replace('-', ''))
            
            cart_sessions_result = cart_sessions_query.execute()
            cart_sessions = {item['param_ga_session_id'] for item in cart_sessions_result.data}

            # Then, get all sessions with purchases in the same range
            purchase_sessions_query = self.client.table('purchase').select('param_ga_session_id').eq('tenant_id', tenant_id)
            if location_id:
                purchase_sessions_query = purchase_sessions_query.eq('user_prop_default_branch_id', location_id)
            if start_date:
                purchase_sessions_query = purchase_sessions_query.gte('event_date', start_date.replace('-', ''))
            if end_date:
                purchase_sessions_query = purchase_sessions_query.lte('event_date', end_date.replace('-', ''))
            
            purchase_sessions_result = purchase_sessions_query.execute()
            purchase_sessions = {item['param_ga_session_id'] for item in purchase_sessions_result.data}

            abandoned_session_ids = list(cart_sessions - purchase_sessions)
            
            total_count = len(abandoned_session_ids)
            
            # Paginate the abandoned session IDs
            offset = (page - 1) * limit
            paginated_session_ids = abandoned_session_ids[offset : offset + limit]

            if not paginated_session_ids:
                return {'data': [], 'total': 0, 'page': page, 'limit': limit, 'has_more': False}

            # Step 2: For the abandoned sessions, get the cart details
            abandoned_carts_query = self.client.table('add_to_cart').select(
                '*'
            ).eq('tenant_id', tenant_id).in_('param_ga_session_id', paginated_session_ids)
            
            abandoned_carts_result = abandoned_carts_query.execute()

            # Group cart items by session ID
            session_data = {}
            for item in abandoned_carts_result.data:
                session_id = item['param_ga_session_id']
                if session_id not in session_data:
                    session_data[session_id] = {
                        'items': [],
                        'last_activity': '0',
                        'web_user_id': item.get('user_prop_webuserid'),
                        'event_date': self._format_event_date(item.get('event_timestamp'))
                    }
                session_data[session_id]['items'].append(item)
                if item['event_timestamp'] > session_data[session_id]['last_activity']:
                    session_data[session_id]['last_activity'] = item['event_timestamp']

            # Step 3: Format the data into tasks
            tasks = []
            for session_id, data in session_data.items():
                user = self._get_user_details(tenant_id, data['web_user_id'])
                
                total_value = sum(
                    float(i.get('first_item_price', 0) or 0) * int(i.get('first_item_quantity', 0) or 0)
                    for i in data['items']
                )

                tasks.append({
                    'session_id': session_id,
                    'event_date': data['event_date'],
                    'last_activity': self._format_event_date(data['last_activity']),
                    'items_count': len(data['items']),
                    'total_value': total_value,
                    'user_id': user.get('user_id'),
                    'customer_name': user.get('customer_name'),
                    'email': user.get('email'),
                    'phone': user.get('phone'),
                    'products': self._parse_cart_items(data['items']),
                    'completed': self._get_task_completion_status(tenant_id, session_id, 'cart_abandonment')
                })
            
            return {
                'data': tasks,
                'total': total_count,
                'page': page,
                'limit': limit,
                'has_more': (page * limit) < total_count
            }

        except Exception as e:
            logger.error(f"Error fetching cart abandonment tasks: {e}")
            raise

    def get_search_analysis_tasks(self, tenant_id: str, page: int, limit: int, 
                                  query: Optional[str] = None, location_id: Optional[str] = None, 
                                  start_date: Optional[str] = None, end_date: Optional[str] = None,
                                  include_converted: bool = False) -> Dict[str, Any]:
        """Get search analysis tasks with pagination and filtering."""
        try:
            # Step 1: Get failed searches
            failed_searches_query = self.client.table('no_search_results').select(
                'param_ga_session_id, param_no_search_results_term, event_timestamp, user_prop_webuserid',
                count='exact'
            ).eq('tenant_id', tenant_id)

            if location_id:
                failed_searches_query = failed_searches_query.eq('user_prop_default_branch_id', location_id)
            if start_date:
                failed_searches_query = failed_searches_query.gte('event_date', start_date.replace('-', ''))
            if end_date:
                failed_searches_query = failed_searches_query.lte('event_date', end_date.replace('-', ''))
            if query:
                failed_searches_query = failed_searches_query.ilike('param_no_search_results_term', f'%{query}%')

            failed_searches_result = failed_searches_query.execute()
            
            # Step 2: Get unconverted searches
            # This is a complex query, and this implementation is a simplified version.
            # A more performant version would use a database function (RPC).
            
            # First, get all sessions with search activity
            search_sessions_query = self.client.table('view_search_results').select(
                'param_ga_session_id, user_prop_webuserid, param_search_term, event_timestamp'
            ).eq('tenant_id', tenant_id)

            if location_id:
                search_sessions_query = search_sessions_query.eq('user_prop_default_branch_id', location_id)
            if start_date:
                search_sessions_query = search_sessions_query.gte('event_date', start_date.replace('-', ''))
            if end_date:
                search_sessions_query = search_sessions_query.lte('event_date', end_date.replace('-', ''))
            
            search_sessions_result = search_sessions_query.execute()

            # Group by session and count searches
            sessions = {}
            for search in search_sessions_result.data:
                session_id = search.get('param_ga_session_id')
                if session_id:
                    if session_id not in sessions:
                        sessions[session_id] = {'searches': [], 'user_id': search.get('user_prop_webuserid')}
                    sessions[session_id]['searches'].append(search)
            
            # Filter for sessions with > 2 searches
            multi_search_sessions = {sid: data for sid, data in sessions.items() if len(data['searches']) > 2}

            # Get purchase sessions to filter out converted sessions
            if not include_converted:
                purchase_sessions_query = self.client.table('purchase').select('param_ga_session_id').eq('tenant_id', tenant_id)
                if location_id:
                    purchase_sessions_query = purchase_sessions_query.eq('user_prop_default_branch_id', location_id)
                if start_date:
                    purchase_sessions_query = purchase_sessions_query.gte('event_date', start_date.replace('-', ''))
                if end_date:
                    purchase_sessions_query = purchase_sessions_query.lte('event_date', end_date.replace('-', ''))
                
                purchase_sessions_result = purchase_sessions_query.execute()
                purchase_sessions = {item['param_ga_session_id'] for item in purchase_sessions_result.data}
                
                unconverted_sessions = {sid: data for sid, data in multi_search_sessions.items() if sid not in purchase_sessions}
            else:
                unconverted_sessions = multi_search_sessions

            # Step 3: Combine, format, and paginate
            tasks = []
            # Add failed searches
            for item in failed_searches_result.data:
                user = self._get_user_details(tenant_id, item.get('user_prop_webuserid'))
                tasks.append({
                    'session_id': item.get('param_ga_session_id'),
                    'event_date': self._format_event_date(item.get('event_timestamp')),
                    'search_term': item.get('param_no_search_results_term'),
                    'search_type': 'no_results',
                    'search_count': 1,
                    'user_id': user.get('user_id'),
                    'customer_name': user.get('customer_name'),
                    'email': user.get('email'),
                    'phone': user.get('phone'),
                    'completed': self._get_task_completion_status(tenant_id, item.get('param_ga_session_id'), 'search_analysis_failed')
                })

            # Add unconverted searches
            for session_id, data in unconverted_sessions.items():
                user = self._get_user_details(tenant_id, data['user_id'])
                search_terms = [s.get('param_search_term') for s in data['searches']]
                tasks.append({
                    'session_id': session_id,
                    'event_date': self._format_event_date(data['searches'][0].get('event_timestamp')),
                    'search_term': ", ".join(set(search_terms)),
                    'search_type': 'no_conversion',
                    'search_count': len(search_terms),
                    'user_id': user.get('user_id'),
                    'customer_name': user.get('customer_name'),
                    'email': user.get('email'),
                    'phone': user.get('phone'),
                    'completed': self._get_task_completion_status(tenant_id, session_id, 'search_analysis_unconverted')
                })

            total_count = len(tasks)
            offset = (page - 1) * limit
            paginated_tasks = tasks[offset : offset + limit]

            return {
                'data': paginated_tasks,
                'total': total_count,
                'page': page,
                'limit': limit,
                'has_more': (page * limit) < total_count
            }

        except Exception as e:
            logger.error(f"Error fetching search analysis tasks: {e}")
            raise

    def get_repeat_visit_tasks(self, tenant_id: str, page: int, limit: int, 
                               query: Optional[str] = None, location_id: Optional[str] = None, 
                               start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Get repeat visit tasks with pagination and filtering."""
        try:
            # Step 1: Find sessions with more than 3 page views
            base_query = self.client.table('page_view').select(
                'param_ga_session_id, user_prop_webuserid, param_page_title, param_page_location, event_timestamp'
            ).eq('tenant_id', tenant_id)

            if location_id:
                base_query = base_query.eq('user_prop_default_branch_id', location_id)
            if start_date:
                base_query = base_query.gte('event_date', start_date.replace('-', ''))
            if end_date:
                base_query = base_query.lte('event_date', end_date.replace('-', ''))
            
            # Fetch all page views for the given filters
            page_views_result = base_query.execute()

            # Group by session and count unique pages
            session_page_counts = {}
            for pv in page_views_result.data:
                session_id = pv.get('param_ga_session_id')
                if session_id:
                    if session_id not in session_page_counts:
                        session_page_counts[session_id] = {
                            'pages': set(),
                            'user_id': pv.get('user_prop_webuserid'),
                            'last_visit': pv.get('event_timestamp'),
                            'page_titles': set()
                        }
                    session_page_counts[session_id]['pages'].add(pv.get('param_page_location'))
                    session_page_counts[session_id]['page_titles'].add(pv.get('param_page_title'))

            # Filter for sessions with >= 3 unique page views
            repeat_visit_sessions = {
                session_id: data for session_id, data in session_page_counts.items() if len(data['pages']) >= 3
            }
            
            total_count = len(repeat_visit_sessions)
            
            # Paginate the session IDs
            session_ids = list(repeat_visit_sessions.keys())
            offset = (page - 1) * limit
            paginated_session_ids = session_ids[offset : offset + limit]

            # Step 2: Format into tasks
            tasks = []
            for session_id in paginated_session_ids:
                session_data = repeat_visit_sessions[session_id]
                user = self._get_user_details(tenant_id, session_data['user_id'])

                tasks.append({
                    'product_url': list(session_data['pages'])[0] if session_data['pages'] else '',
                    'session_count': len(session_data['pages']),
                    'last_view_date': self._format_event_date(session_data['last_visit']),
                    'total_views': len(session_data['pages']),
                    'user_id': user.get('user_id'),
                    'customer_name': user.get('customer_name'),
                    'email': user.get('email'),
                    'phone': user.get('phone'),
                    'completed': self._get_task_completion_status(tenant_id, session_id, 'repeat_visit')
                })

            return {
                'data': tasks,
                'total': total_count,
                'page': page,
                'limit': limit,
                'has_more': (page * limit) < total_count
            }

        except Exception as e:
            logger.error(f"Error fetching repeat visit tasks: {e}")
            raise

    def get_performance_tasks(self, tenant_id: str, page: int, limit: int, 
                              query: Optional[str] = None, location_id: Optional[str] = None, 
                              start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Get performance tasks with pagination and filtering."""
        try:
            # Step 1: Find sessions with only one page view (bounces)
            base_query = self.client.table('page_view').select(
                'param_ga_session_id, user_prop_webuserid, param_page_title, param_page_location, event_timestamp'
            ).eq('tenant_id', tenant_id)

            if location_id:
                base_query = base_query.eq('user_prop_default_branch_id', location_id)
            if start_date:
                base_query = base_query.gte('event_date', start_date.replace('-', ''))
            if end_date:
                base_query = base_query.lte('event_date', end_date.replace('-', ''))
            
            page_views_result = base_query.execute()

            # Group by session
            sessions = {}
            for pv in page_views_result.data:
                session_id = pv.get('param_ga_session_id')
                if session_id:
                    if session_id not in sessions:
                        sessions[session_id] = []
                    sessions[session_id].append(pv)
            
            bounce_sessions = {sid: pvs for sid, pvs in sessions.items() if len(pvs) == 1}
            
            # Step 2: Identify frequently bounced pages
            page_bounces = {}
            for session_id, page_views in bounce_sessions.items():
                page_location = page_views[0].get('param_page_location')
                if page_location:
                    if page_location not in page_bounces:
                        page_bounces[page_location] = {'count': 0, 'page_title': page_views[0].get('param_page_title')}
                    page_bounces[page_location]['count'] += 1
            
            frequently_bounced_pages = {loc: data for loc, data in page_bounces.items() if data['count'] > 2}

            # Step 3: Format into tasks
            tasks = []
            # Add individual bounce sessions
            for session_id, page_views in bounce_sessions.items():
                page_view = page_views[0]
                user = self._get_user_details(tenant_id, page_view.get('user_prop_webuserid'))
                tasks.append({
                    'session_id': session_id,
                    'event_date': self._format_event_date(page_view.get('event_timestamp')),
                    'bounce_type': 'single_page',
                    'page_views': 1,
                    'session_duration': 0,
                    'user_id': user.get('user_id'),
                    'customer_name': user.get('customer_name'),
                    'email': user.get('email'),
                    'phone': user.get('phone'),
                    'completed': self._get_task_completion_status(tenant_id, session_id, 'performance_bounce')
                })

            # Add frequently bounced pages
            for page_location, data in frequently_bounced_pages.items():
                tasks.append({
                    'session_id': None,
                    'event_date': None,
                    'bounce_type': 'frequent_page_bounce',
                    'page_views': data['count'],
                    'session_duration': None,
                    'user_id': None,
                    'customer_name': 'System Alert',
                    'email': None,
                    'phone': None,
                    'completed': self._get_task_completion_status(tenant_id, page_location, 'performance_page_bounce')
                })
            
            total_count = len(tasks)
            offset = (page - 1) * limit
            paginated_tasks = tasks[offset : offset + limit]

            return {
                'data': paginated_tasks,
                'total': total_count,
                'page': page,
                'limit': limit,
                'has_more': (page * limit) < total_count
            }

        except Exception as e:
            logger.error(f"Error fetching performance tasks: {e}")
            raise

    def _parse_cart_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Helper to parse cart items."""
        if not items:
            return []
        
        return [{
            'item_id': item.get('first_item_item_id'),
            'item_name': item.get('first_item_item_name'),
            'item_category': item.get('first_item_item_category'),
            'price': float(item.get('first_item_price', 0) or 0),
            'quantity': int(item.get('first_item_quantity', 0) or 0)
        } for item in items]

    def _get_user_details(self, tenant_id: str, web_user_id: Optional[str]) -> Dict[str, Any]:
        """Helper to get user details."""
        if not web_user_id:
            return {}
        try:
            # Supabase user_id is integer, so we need to cast
            user_id_int = int(web_user_id)
            result = self.client.table('users').select(
                'user_id, name, email, phone, customer_name'
            ).eq('tenant_id', tenant_id).eq('user_id', user_id_int).limit(1).execute()
            
            if result.data:
                return result.data[0]
            return {}
        except (ValueError, TypeError):
            # Handle cases where web_user_id is not a valid integer
            return {}
        except Exception as e:
            logger.warning(f"Could not fetch user details for {web_user_id}: {e}")
            return {}

    def _parse_items_json(self, items_json: Optional[str]) -> List[Dict[str, Any]]:
        """Helper to parse items_json string."""
        if not items_json:
            return []
        try:
            import json
            items = json.loads(items_json)
            # Ensure items is a list
            if not isinstance(items, list):
                return []

            return [{
                'item_id': item.get('item_id'),
                'item_name': item.get('item_name'),
                'item_category': item.get('item_category'),
                'price': float(item.get('price', 0) or 0),
                'quantity': int(item.get('quantity', 0) or 0)
            } for item in items]
        except Exception:
            return []
            
    def _format_event_date(self, event_timestamp: Optional[str]) -> str:
        """Helper to format event timestamp."""
        if not event_timestamp:
            return ''
        try:
            # Timestamp is in microseconds
            ts = int(event_timestamp) / 1_000_000
            return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        except Exception:
            return ''
    
    def _get_task_completion_status(self, tenant_id: str, task_id: Optional[str], task_type: str) -> bool:
        """Helper to get task completion status."""
        if not task_id:
            return False
        try:
            status = self.get_task_status(tenant_id, task_id, task_type)
            return status.get('completed', False)
        except Exception:
            return False
