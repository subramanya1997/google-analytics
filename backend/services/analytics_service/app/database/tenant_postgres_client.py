"""
Tenant-aware PostgreSQL client for analytics service operations
"""
import json
from typing import Dict, List, Any, Optional
from sqlalchemy import text, func, select, distinct, and_, or_, desc
from sqlalchemy.orm import Session
from loguru import logger
from datetime import datetime, date

from common.database import get_tenant_session
from common.models import (
    Users, Locations, Purchase, AddToCart, PageView, 
    ViewSearchResults, NoSearchResults, ViewItem, TaskTracking
)


class TenantAnalyticsPostgresClient:
    """Tenant-aware PostgreSQL client for analytics operations."""
    
    def __init__(self, tenant_id: str):
        """
        Initialize PostgreSQL client for a specific tenant.
        
        Args:
            tenant_id: The tenant ID to use for database connections
        """
        self.tenant_id = tenant_id
        logger.info(f"Initialized Tenant Analytics PostgreSQL client for tenant {tenant_id}")
    
    def get_db_session(self) -> Session:
        """Get a database session for the tenant."""
        return get_tenant_session(self.tenant_id, "analytics-service")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the PostgreSQL connection for the tenant."""
        try:
            with self.get_db_session() as session:
                # Try to query tenants table
                result = session.execute(text("SELECT COUNT(*) FROM tenants LIMIT 1")).scalar()
                return {
                    'success': True,
                    'message': f'Connection successful for tenant {self.tenant_id}',
                    'data': {'count': result}
                }
        except Exception as e:
            error_message = str(e)
            logger.error(f"PostgreSQL connection test failed for tenant {self.tenant_id}: {error_message}")
            return {
                'success': False,
                'message': f'Connection failed for tenant {self.tenant_id}: {error_message}',
                'data': []
            }
    
    # Location operations
    def get_locations(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Get all locations with activity for the tenant."""
        try:
            with self.get_db_session() as session:
                # Query locations with activity counts
                query = text("""
                    SELECT 
                        l.warehouse_id,
                        l.warehouse_name,
                        l.city,
                        l.state,
                        l.country,
                        COALESCE(stats.total_events, 0) as total_events,
                        COALESCE(stats.unique_users, 0) as unique_users,
                        COALESCE(stats.total_purchases, 0) as total_purchases,
                        COALESCE(stats.total_revenue, 0) as total_revenue
                    FROM locations l
                    LEFT JOIN (
                        SELECT 
                            warehouse_code,
                            COUNT(*) as total_events,
                            COUNT(DISTINCT user_pseudo_id) as unique_users,
                            SUM(CASE WHEN event_name = 'purchase' THEN 1 ELSE 0 END) as total_purchases,
                            SUM(CASE WHEN event_name = 'purchase' THEN COALESCE(purchase_revenue, 0) ELSE 0 END) as total_revenue
                        FROM (
                            SELECT user_pseudo_id, warehouse_code, 'purchase' as event_name, purchase_revenue FROM purchase WHERE tenant_id = :tenant_id
                            UNION ALL
                            SELECT user_pseudo_id, warehouse_code, 'add_to_cart' as event_name, NULL as purchase_revenue FROM add_to_cart WHERE tenant_id = :tenant_id
                            UNION ALL
                            SELECT user_pseudo_id, warehouse_code, 'page_view' as event_name, NULL as purchase_revenue FROM page_view WHERE tenant_id = :tenant_id
                        ) combined_events
                        GROUP BY warehouse_code
                    ) stats ON l.warehouse_code = stats.warehouse_code
                    WHERE l.tenant_id = :tenant_id
                    ORDER BY stats.total_events DESC NULLS LAST, l.warehouse_name
                """)
                
                result = session.execute(query, {"tenant_id": tenant_id})
                locations = []
                
                for row in result:
                    locations.append({
                        'warehouse_id': row.warehouse_id,
                        'warehouse_name': row.warehouse_name,
                        'city': row.city,
                        'state': row.state,
                        'country': row.country,
                        'total_events': int(row.total_events or 0),
                        'unique_users': int(row.unique_users or 0),
                        'total_purchases': int(row.total_purchases or 0),
                        'total_revenue': float(row.total_revenue or 0)
                    })
                
                logger.info(f"Retrieved {len(locations)} locations for tenant {tenant_id}")
                return locations
                
        except Exception as e:
            logger.error(f"Error getting locations for tenant {tenant_id}: {e}")
            return []
    
    # User operations
    def get_users(self, tenant_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get users with activity for the tenant."""
        try:
            with self.get_db_session() as session:
                # Query users with activity counts
                query = text("""
                    SELECT 
                        u.user_id,
                        u.user_name,
                        u.first_name,
                        u.last_name,
                        u.email,
                        u.warehouse_code,
                        u.buying_company_name,
                        u.role_name,
                        u.last_login_date,
                        COALESCE(stats.total_events, 0) as total_events,
                        COALESCE(stats.total_purchases, 0) as total_purchases,
                        COALESCE(stats.total_revenue, 0) as total_revenue,
                        COALESCE(stats.last_activity, u.last_login_date) as last_activity
                    FROM users u
                    LEFT JOIN (
                        SELECT 
                            user_pseudo_id,
                            COUNT(*) as total_events,
                            SUM(CASE WHEN event_name = 'purchase' THEN 1 ELSE 0 END) as total_purchases,
                            SUM(CASE WHEN event_name = 'purchase' THEN COALESCE(purchase_revenue, 0) ELSE 0 END) as total_revenue,
                            MAX(event_timestamp) as last_activity
                        FROM (
                            SELECT user_pseudo_id, 'purchase' as event_name, purchase_revenue, event_timestamp FROM purchase WHERE tenant_id = :tenant_id
                            UNION ALL
                            SELECT user_pseudo_id, 'add_to_cart' as event_name, NULL as purchase_revenue, event_timestamp FROM add_to_cart WHERE tenant_id = :tenant_id
                            UNION ALL
                            SELECT user_pseudo_id, 'page_view' as event_name, NULL as purchase_revenue, event_timestamp FROM page_view WHERE tenant_id = :tenant_id
                        ) combined_events
                        GROUP BY user_pseudo_id
                    ) stats ON u.user_id = stats.user_pseudo_id
                    WHERE u.tenant_id = :tenant_id
                    ORDER BY stats.last_activity DESC NULLS LAST, u.last_login_date DESC NULLS LAST
                    LIMIT :limit OFFSET :offset
                """)
                
                result = session.execute(query, {
                    "tenant_id": tenant_id,
                    "limit": limit,
                    "offset": offset
                })
                
                users = []
                for row in result:
                    users.append({
                        'user_id': row.user_id,
                        'user_name': row.user_name,
                        'first_name': row.first_name,
                        'last_name': row.last_name,
                        'email': row.email,
                        'warehouse_code': row.warehouse_code,
                        'buying_company_name': row.buying_company_name,
                        'role_name': row.role_name,
                        'last_login_date': row.last_login_date,
                        'total_events': int(row.total_events or 0),
                        'total_purchases': int(row.total_purchases or 0),
                        'total_revenue': float(row.total_revenue or 0),
                        'last_activity': row.last_activity
                    })
                
                logger.info(f"Retrieved {len(users)} users for tenant {tenant_id}")
                return users
                
        except Exception as e:
            logger.error(f"Error getting users for tenant {tenant_id}: {e}")
            return []
    
    # Statistics operations
    def get_analytics_stats(self, tenant_id: str, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict[str, Any]:
        """Get comprehensive analytics statistics for the tenant."""
        try:
            with self.get_db_session() as session:
                # Build date filter
                date_filter = ""
                params = {"tenant_id": tenant_id}
                
                if start_date and end_date:
                    date_filter = "AND DATE(event_timestamp) BETWEEN :start_date AND :end_date"
                    params.update({
                        "start_date": start_date,
                        "end_date": end_date
                    })
                
                # Get overall statistics
                stats_query = text(f"""
                    SELECT 
                        COUNT(*) as total_events,
                        COUNT(DISTINCT user_pseudo_id) as unique_users,
                        SUM(CASE WHEN event_name = 'purchase' THEN 1 ELSE 0 END) as total_purchases,
                        SUM(CASE WHEN event_name = 'purchase' THEN COALESCE(purchase_revenue, 0) ELSE 0 END) as total_revenue,
                        SUM(CASE WHEN event_name = 'add_to_cart' THEN 1 ELSE 0 END) as total_add_to_cart,
                        SUM(CASE WHEN event_name = 'page_view' THEN 1 ELSE 0 END) as total_page_views
                    FROM (
                        SELECT user_pseudo_id, 'purchase' as event_name, purchase_revenue, event_timestamp FROM purchase WHERE tenant_id = :tenant_id {date_filter}
                        UNION ALL
                        SELECT user_pseudo_id, 'add_to_cart' as event_name, NULL as purchase_revenue, event_timestamp FROM add_to_cart WHERE tenant_id = :tenant_id {date_filter}
                        UNION ALL
                        SELECT user_pseudo_id, 'page_view' as event_name, NULL as purchase_revenue, event_timestamp FROM page_view WHERE tenant_id = :tenant_id {date_filter}
                    ) combined_events
                """)
                
                result = session.execute(stats_query, params).fetchone()
                
                stats = {
                    'total_events': int(result.total_events or 0),
                    'unique_users': int(result.unique_users or 0),
                    'total_purchases': int(result.total_purchases or 0),
                    'total_revenue': float(result.total_revenue or 0),
                    'total_add_to_cart': int(result.total_add_to_cart or 0),
                    'total_page_views': int(result.total_page_views or 0)
                }
                
                logger.info(f"Retrieved analytics stats for tenant {tenant_id}: {stats}")
                return stats
                
        except Exception as e:
            logger.error(f"Error getting analytics stats for tenant {tenant_id}: {e}")
            return {
                'total_events': 0,
                'unique_users': 0,
                'total_purchases': 0,
                'total_revenue': 0.0,
                'total_add_to_cart': 0,
                'total_page_views': 0
            }
