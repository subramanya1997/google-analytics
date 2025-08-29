"""
Comprehensive data processing service for complete analytics pipeline
"""
import json
from datetime import datetime, date
from typing import Dict, Any, List
from uuid import uuid4
from loguru import logger
import pandas as pd

from app.database.enhanced_supabase_client import EnhancedSupabaseClient
from app.models.data_ingestion import DataIngestionRequest
from app.clients.enhanced_bigquery_client import EnhancedBigQueryClient
from app.clients.azure_sftp_client import AzureSFTPClient
from app.core.config import settings


class ComprehensiveDataProcessingService:
    """Comprehensive service for handling all analytics data processing."""
    
    def __init__(self):
        supabase_config = settings.get_supabase_client_config()
        self.supabase = EnhancedSupabaseClient(supabase_config)
    
    def create_processing_job(self, job_id: str, request: DataIngestionRequest) -> Dict[str, Any]:
        """Create a new processing job."""
        try:
            job_data = {
                'job_id': job_id,
                'tenant_id': request.tenant_id,
                'status': 'queued',
                'data_types': request.data_types,
                'start_date': request.start_date.isoformat(),
                'end_date': request.end_date.isoformat(),
                'created_at': datetime.now().isoformat()
            }
            
            job = self.supabase.create_processing_job(job_data)
            logger.info(f"Created processing job {job_id}")
            return job
            
        except Exception as e:
            logger.error(f"Error creating processing job {job_id}: {e}")
            raise
    
    async def process_data_ingestion(self, job_id: str, request: DataIngestionRequest) -> Dict[str, Any]:
        """Process comprehensive data ingestion request."""
        try:
            # Update job status to processing
            self.supabase.update_job_status(job_id, 'processing', started_at=datetime.now().isoformat())
            
            results = {
                'purchase': 0,
                'add_to_cart': 0,
                'page_view': 0,
                'view_search_results': 0,
                'no_search_results': 0,
                'view_item': 0,
                'users_processed': 0,
                'locations_processed': 0
            }
            
            # Process events from BigQuery
            if 'events' in request.data_types:
                try:
                    logger.info(f"Processing events for job {job_id}")
                    event_results = self._process_bigquery_events(request)
                    results.update(event_results)
                    
                except Exception as e:
                    logger.error(f"Error processing events: {e}")
                    raise
            
            # Process users from SFTP
            if 'users' in request.data_types:
                try:
                    logger.info(f"Processing users for job {job_id}")
                    users_count = await self._process_users(request.tenant_id)
                    results['users_processed'] = users_count
                    
                except Exception as e:
                    logger.error(f"Error processing users: {e}")
                    raise
            
            # Process locations from SFTP
            if 'locations' in request.data_types:
                try:
                    logger.info(f"Processing locations for job {job_id}")
                    locations_count = await self._process_locations(request.tenant_id)
                    results['locations_processed'] = locations_count
                    
                except Exception as e:
                    logger.error(f"Error processing locations: {e}")
                    raise
            
            # Update job status to completed
            self.supabase.update_job_status(
                job_id, 
                'completed', 
                completed_at=datetime.now().isoformat(),
                records_processed=results
            )
            
            logger.info(f"Completed processing job {job_id}: {results}")
            return results
            
        except Exception as e:
            # Update job status to failed
            self.supabase.update_job_status(
                job_id, 
                'failed', 
                completed_at=datetime.now().isoformat(),
                error_message=str(e)
            )
            logger.error(f"Failed processing job {job_id}: {e}")
            raise
    
    def _process_bigquery_events(self, request: DataIngestionRequest) -> Dict[str, int]:
        """Process all event types from BigQuery."""
        try:
            # Initialize BigQuery client
            bigquery_config = settings.get_bigquery_config()
            bigquery_client = EnhancedBigQueryClient(bigquery_config)
            
            # Get all events for date range
            events_by_type = bigquery_client.get_date_range_events(
                request.start_date.isoformat(),
                request.end_date.isoformat()
            )
            
            results = {}
            
            # Process each event type
            for event_type, events_data in events_by_type.items():
                try:
                    if events_data:
                        count = self.supabase.replace_event_data(
                            request.tenant_id,
                            event_type,
                            request.start_date,
                            request.end_date,
                            events_data
                        )
                        results[event_type] = count
                        logger.info(f"Processed {count} {event_type} events")
                    else:
                        results[event_type] = 0
                        logger.info(f"No {event_type} events found")
                        
                except Exception as e:
                    logger.error(f"Error processing {event_type} events: {e}")
                    results[event_type] = 0
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing BigQuery events: {e}")
            raise
    
    async def _process_users(self, tenant_id: str) -> int:
        """Process users from SFTP."""
        try:
            sftp_config = settings.get_sftp_config()
            
            # Create a fresh Azure SFTP client for each operation
            sftp_client = AzureSFTPClient(sftp_config)
            
            # Get users data (Azure client handles connections internally)
            users_data = await sftp_client.get_latest_users_data()
            
            if users_data is not None and len(users_data) > 0:
                # Clean the data: replace NaN values with None
                import numpy as np
                users_data = users_data.replace({np.nan: None})
                
                # Convert DataFrame to list of dictionaries
                users_list = users_data.to_dict('records')
                
                # Clean the records for JSON compatibility
                cleaned_users = []
                for record in users_list:
                    cleaned_record = {}
                    for key, value in record.items():
                        if pd.isna(value) if hasattr(pd, 'isna') else (value is None or str(value) == 'nan'):
                            cleaned_record[key] = None
                        else:
                            cleaned_record[key] = value
                    cleaned_users.append(cleaned_record)
                
                count = self.supabase.upsert_users(tenant_id, cleaned_users)
                logger.info(f"Processed {count} users from SFTP")
                return count
            else:
                logger.info("No users data found")
                return 0
                
        except Exception as e:
            logger.error(f"Error processing users: {e}")
            raise
    
    async def _process_locations(self, tenant_id: str) -> int:
        """Process locations from local temp_data directory (temporarily) or SFTP."""
        try:
            # TEMPORARY: Read from local temp_data directory
            # TODO: Switch back to SFTP when locations file is available on server
            import pandas as pd
            from pathlib import Path
            
            # Local file path
            temp_data_dir = Path(__file__).parent.parent.parent / "temp_data"
            locations_file = temp_data_dir / "Locations_List1750281613134.xlsx"
            
            if locations_file.exists():
                logger.info(f"Reading locations from local file: {locations_file}")
                locations_data = pd.read_excel(locations_file)
                
                if locations_data is not None and len(locations_data) > 0:
                    # Clean the data: replace NaN values with None and convert to proper types
                    import numpy as np
                    locations_data = locations_data.replace({np.nan: None})
                    
                    # Map Excel columns to database columns (only include columns that exist in DB schema)
                    # Database schema: location_id, warehouse_code, warehouse_name, name, city, state, country
                    column_mapping = {
                        'WAREHOUSE_ID': 'location_id',      # Maps to location_id in DB
                        'WAREHOUSE_CODE': 'warehouse_code',  # Maps to warehouse_code in DB
                        'WAREHOUSE_NAME': 'warehouse_name',  # Maps to warehouse_name in DB
                        'CITY': 'city',                     # Maps to city in DB
                        'STATE': 'state',                   # Maps to state in DB
                        'COUNTRY': 'country'                # Maps to country in DB
                        # Note: name field will be set to warehouse_name
                    }
                    
                    # Filter columns to only include those that exist in our mapping AND in the Excel file
                    available_columns = [col for col in column_mapping.keys() if col in locations_data.columns]
                    filtered_data = locations_data[available_columns].copy()
                    
                    # Rename columns to match database schema
                    filtered_data = filtered_data.rename(columns=column_mapping)
                    
                    # Add name field (use warehouse_name as name)
                    if 'warehouse_name' in filtered_data.columns:
                        filtered_data['name'] = filtered_data['warehouse_name']
                    
                    # Convert DataFrame to list of dictionaries
                    locations_list = filtered_data.to_dict('records')
                    
                    # Further clean the records to ensure JSON compatibility
                    cleaned_locations = []
                    for record in locations_list:
                        cleaned_record = {}
                        for key, value in record.items():
                            # Convert pandas NaT, NaN, and other problematic types to None
                            if pd.isna(value) if hasattr(pd, 'isna') else (value is None or str(value) == 'nan'):
                                cleaned_record[key] = None
                            else:
                                cleaned_record[key] = value
                        cleaned_locations.append(cleaned_record)
                    
                    final_columns = list(filtered_data.columns)
                    logger.info(f"Mapped locations data from {len(available_columns)} Excel columns to {len(final_columns)} DB columns")
                    logger.info(f"Final DB columns: {final_columns}")
                    count = self.supabase.upsert_locations(tenant_id, cleaned_locations)
                    logger.info(f"Processed {count} locations from local file")
                    return count
                else:
                    logger.info("Local locations file is empty")
                    return 0
            else:
                logger.warning(f"Local locations file not found: {locations_file}")
                return 0
            
            # COMMENTED: SFTP code for future use when file is available on server
            """
            # SFTP version (commented for future use)
            sftp_config = settings.get_sftp_config()
            sftp_client = SFTPClient(sftp_config)
            
            locations_data = await sftp_client.get_latest_locations_data()
            
            if locations_data is not None and len(locations_data) > 0:
                # Convert DataFrame to list of dictionaries
                locations_list = locations_data.to_dict('records')
                count = self.supabase.upsert_locations(tenant_id, locations_list)
                logger.info(f"Processed {count} locations from SFTP")
                return count
            else:
                logger.info("No locations data found on SFTP")
                return 0
            """
                
        except Exception as e:
            logger.error(f"Error processing locations: {e}")
            raise
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status."""
        job = self.supabase.get_job_by_id(job_id)
        if not job:
            raise Exception(f"Job {job_id} not found")
        return job
    
    def get_analytics_summary(self, tenant_id: str, start_date: date = None, end_date: date = None) -> Dict[str, Any]:
        """Get analytics summary for a tenant."""
        return self.supabase.get_analytics_summary(tenant_id, start_date, end_date)
