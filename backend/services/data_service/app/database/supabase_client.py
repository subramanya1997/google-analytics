"""
Simple Supabase client wrapper for database operations
"""
import os
from typing import Dict, List, Any, Optional
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from loguru import logger
from datetime import datetime, date
from uuid import UUID, uuid4
import httpx


class SupabaseClient:
    """Simple wrapper for Supabase operations."""
    
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
        
        logger.info(f"Initialized Supabase client for {self.project_url}")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the Supabase connection."""
        try:
            # Try to access the client - this will test authentication
            # If tables don't exist, that's okay for now
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
    
    # Data operations
    def replace_events(self, tenant_id: str, start_date: date, end_date: date, events_data: List[Dict[str, Any]]) -> int:
        """Replace events for a date range."""
        try:
            # Delete existing events
            self.client.table('events').delete().eq('tenant_id', tenant_id).gte('event_date', start_date.isoformat()).lte('event_date', end_date.isoformat()).execute()
            
            # Insert new events in batches
            batch_size = 1000
            total_inserted = 0
            
            for i in range(0, len(events_data), batch_size):
                batch = events_data[i:i + batch_size]
                for event in batch:
                    event['tenant_id'] = tenant_id
                
                result = self.client.table('events').insert(batch).execute()
                total_inserted += len(result.data) if result.data else 0
            
            logger.info(f"Inserted {total_inserted} events")
            return total_inserted
        except Exception as e:
            logger.error(f"Error replacing events: {e}")
            raise
    
    def upsert_users(self, tenant_id: str, users_data: List[Dict[str, Any]]) -> int:
        """Upsert users data."""
        try:
            for user in users_data:
                user['tenant_id'] = tenant_id
                user['updated_at'] = datetime.now().isoformat()
            
            result = self.client.table('users').upsert(users_data).execute()
            count = len(result.data) if result.data else 0
            logger.info(f"Upserted {count} users")
            return count
        except Exception as e:
            logger.error(f"Error upserting users: {e}")
            raise
    
    def upsert_locations(self, tenant_id: str, locations_data: List[Dict[str, Any]]) -> int:
        """Upsert locations data."""
        try:
            for location in locations_data:
                location['tenant_id'] = tenant_id
                location['updated_at'] = datetime.now().isoformat()
            
            result = self.client.table('locations').upsert(locations_data).execute()
            count = len(result.data) if result.data else 0
            logger.info(f"Upserted {count} locations")
            return count
        except Exception as e:
            logger.error(f"Error upserting locations: {e}")
            raise


def get_supabase_client(supabase_config: Dict[str, Any]) -> SupabaseClient:
    """Factory function to create Supabase client."""
    return SupabaseClient(supabase_config)