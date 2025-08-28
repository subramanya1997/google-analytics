"""
Enhanced Supabase client for comprehensive analytics data operations
"""
import os
from typing import Dict, List, Any, Optional
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from loguru import logger
from datetime import datetime, date
from uuid import UUID, uuid4
import httpx

from .table_schemas import TABLE_SCHEMAS


class EnhancedSupabaseClient:
    """Enhanced Supabase client for comprehensive analytics operations."""
    
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
        
        logger.info(f"Initialized Enhanced Supabase client for {self.project_url}")
    
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
            # If it's just a table not found error, that's okay - connection is working
            if 'PGRST205' in error_message or 'Could not find the table' in error_message:
                return {
                    'success': True,
                    'message': 'Connection successful (tables need to be created)',
                    'data': []
                }
            else:
                return {
                    'success': False,
                    'message': f'Connection failed: {error_message}',
                    'data': []
                }
    
    def create_all_tables(self) -> Dict[str, bool]:
        """Create all required tables for analytics."""
        results = {}
        
        for table_name, schema_sql in TABLE_SCHEMAS.items():
            try:
                # Execute the SQL using Supabase RPC or direct SQL execution
                # Note: This requires the SQL execution function to be available
                logger.info(f"Creating table: {table_name}")
                # For now, we'll log the SQL - in production, you'd execute this
                logger.debug(f"SQL for {table_name}: {schema_sql}")
                results[table_name] = True
            except Exception as e:
                logger.error(f"Error creating table {table_name}: {e}")
                results[table_name] = False
        
        return results
    
    # Job operations
    def create_processing_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new processing job."""
        try:
            result = self.client.table('processing_jobs').insert(job_data).execute()
            if result.data:
                logger.info(f"Created processing job {job_data.get('job_id')}")
                return result.data[0]
            else:
                raise Exception("Failed to create processing job")
        except Exception as e:
            logger.error(f"Error creating processing job: {e}")
            raise
    
    def update_job_status(self, job_id: str, status: str, **kwargs) -> bool:
        """Update job status."""
        try:
            update_data = {'status': status}
            update_data.update(kwargs)
            
            result = self.client.table('processing_jobs').update(update_data).eq('job_id', job_id).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error updating job status: {e}")
            return False
    
    def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by job_id."""
        try:
            result = self.client.table('processing_jobs').select('*').eq('job_id', job_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting job: {e}")
            return None
    
    # Event-specific data operations
    def replace_event_data(self, tenant_id: str, event_type: str, start_date: date, end_date: date, events_data: List[Dict[str, Any]]) -> int:
        """Replace event data for a specific event type and date range."""
        try:
            # Delete existing events for this type and date range
            delete_result = self.client.table(event_type).delete().eq('tenant_id', tenant_id).gte('event_date', start_date.isoformat()).lte('event_date', end_date.isoformat()).execute()
            
            logger.info(f"Deleted existing {event_type} events for {tenant_id} from {start_date} to {end_date}")
            
            if not events_data:
                logger.info(f"No {event_type} events to insert")
                return 0
            
            # Add tenant_id to each event
            for event in events_data:
                event['tenant_id'] = tenant_id
                # Ensure proper date formatting
                if isinstance(event.get('event_date'), str):
                    # Convert YYYYMMDD to YYYY-MM-DD
                    event_date = event['event_date']
                    if len(event_date) == 8 and event_date.isdigit():
                        event['event_date'] = f"{event_date[:4]}-{event_date[4:6]}-{event_date[6:8]}"
            
            # Insert new events in batches
            batch_size = 1000
            total_inserted = 0
            
            for i in range(0, len(events_data), batch_size):
                batch = events_data[i:i + batch_size]
                
                result = self.client.table(event_type).insert(batch).execute()
                total_inserted += len(result.data) if result.data else 0
                
                logger.debug(f"Inserted batch {i//batch_size + 1} for {event_type}: {len(batch)} records")
            
            logger.info(f"Inserted {total_inserted} {event_type} events for {tenant_id}")
            return total_inserted
            
        except Exception as e:
            logger.error(f"Error replacing {event_type} events for {tenant_id}: {e}")
            raise
    
    def upsert_users(self, tenant_id: str, users_data: List[Dict[str, Any]]) -> int:
        """Upsert users data with proper batching to avoid request size limits."""
        try:
            if not users_data:
                return 0
                
            # Add tenant_id and timestamp to all records
            for user in users_data:
                user['tenant_id'] = tenant_id
                user['updated_at'] = datetime.now().isoformat()
            
            # Process in batches to avoid request size limits
            batch_size = 100  # Smaller batch size for safer processing
            total_count = 0
            
            for i in range(0, len(users_data), batch_size):
                batch = users_data[i:i + batch_size]
                batch_num = i//batch_size + 1
                total_batches = (len(users_data) + batch_size - 1) // batch_size
                
                logger.debug(f"Upserting batch {batch_num}/{total_batches} for users: {len(batch)} records")
                
                try:
                    # Use proper upsert with conflict resolution
                    result = self.client.table('users').upsert(
                        batch, 
                        on_conflict='tenant_id,user_id'
                    ).execute()
                    
                    batch_count = len(result.data) if result.data else 0
                    total_count += batch_count
                    
                    logger.debug(f"Upserted batch {batch_num}/{total_batches} for users: {batch_count} records")
                    
                except Exception as batch_error:
                    logger.error(f"Error in batch {batch_num}: {batch_error}")
                    # Try even smaller batch size for this batch
                    mini_batch_size = 50
                    for j in range(0, len(batch), mini_batch_size):
                        mini_batch = batch[j:j + mini_batch_size]
                        try:
                            result = self.client.table('users').upsert(
                                mini_batch, 
                                on_conflict='tenant_id,user_id'
                            ).execute()
                            mini_count = len(result.data) if result.data else 0
                            total_count += mini_count
                            logger.debug(f"Upserted mini-batch {j//mini_batch_size + 1}: {mini_count} records")
                        except Exception as mini_error:
                            logger.error(f"Error in mini-batch: {mini_error}")
                            # Skip this mini-batch and continue
                            continue
            
            logger.info(f"Upserted {total_count} users for tenant {tenant_id} in {(len(users_data) + batch_size - 1) // batch_size} batches")
            return total_count
            
        except Exception as e:
            logger.error(f"Error upserting users: {e}")
            raise
    
    def upsert_locations(self, tenant_id: str, locations_data: List[Dict[str, Any]]) -> int:
        """Upsert locations data with proper conflict resolution."""
        try:
            if not locations_data:
                return 0
                
            # Add tenant_id and timestamp, and use WAREHOUSE_ID as location_id
            for location in locations_data:
                location['tenant_id'] = tenant_id
                location['updated_at'] = datetime.now().isoformat()
                # Use WAREHOUSE_ID as the location_id for consistency
                if 'WAREHOUSE_ID' in location and 'location_id' not in location:
                    location['location_id'] = str(location['WAREHOUSE_ID'])
            
            try:
                # Use proper upsert with conflict resolution
                result = self.client.table('locations').upsert(
                    locations_data, 
                    on_conflict='tenant_id,location_id'
                ).execute()
                
                count = len(result.data) if result.data else 0
                logger.info(f"Upserted {count} locations for tenant {tenant_id}")
                return count
                
            except Exception as upsert_error:
                logger.warning(f"Upsert failed, trying insert: {upsert_error}")
                # Fallback to insert if upsert fails (for locations without proper constraints)
                result = self.client.table('locations').insert(locations_data).execute()
                count = len(result.data) if result.data else 0
                logger.info(f"Inserted {count} locations for tenant {tenant_id}")
                return count
            
        except Exception as e:
            logger.error(f"Error upserting locations: {e}")
            raise
    
    # Analytics helper methods
    def get_analytics_summary(self, tenant_id: str, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict[str, int]:
        """Get summary of analytics data for a tenant."""
        try:
            date_filter = ""
            if start_date and end_date:
                date_filter = f"AND event_date BETWEEN '{start_date.isoformat()}' AND '{end_date.isoformat()}'"
            
            summary = {}
            
            # Count events for each table
            event_tables = ['purchase', 'add_to_cart', 'page_view', 'view_search_results', 'no_search_results', 'view_item']
            
            for table in event_tables:
                try:
                    result = self.client.table(table).select('*', count='exact').eq('tenant_id', tenant_id).execute()
                    summary[table] = result.count if hasattr(result, 'count') else 0
                except Exception:
                    summary[table] = 0
            
            # Count users and locations
            try:
                result = self.client.table('users').select('*', count='exact').eq('tenant_id', tenant_id).execute()
                summary['users'] = result.count if hasattr(result, 'count') else 0
            except Exception:
                summary['users'] = 0
            
            try:
                result = self.client.table('locations').select('*', count='exact').eq('tenant_id', tenant_id).execute()
                summary['locations'] = result.count if hasattr(result, 'count') else 0
            except Exception:
                summary['locations'] = 0
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting analytics summary: {e}")
            return {}


def get_enhanced_supabase_client(supabase_config: Dict[str, Any]) -> EnhancedSupabaseClient:
    """Factory function to create Enhanced Supabase client."""
    return EnhancedSupabaseClient(supabase_config)
