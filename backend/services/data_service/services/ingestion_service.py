from datetime import datetime, date
from typing import Dict, Any
from loguru import logger
import pandas as pd

from services.data_service.database.sqlalchemy_repository import SqlAlchemyRepository
from services.data_service.api.v1.models import CreateIngestionJobRequest
from services.data_service.clients.tenant_client_factory import (
    get_tenant_enhanced_bigquery_client,
    get_tenant_azure_sftp_client
)


class IngestionService:
    """Service for handling analytics data ingestion jobs."""
    
    def __init__(self):
        self.repo = SqlAlchemyRepository()
    
    def create_job(self, job_id: str, tenant_id: str, request: CreateIngestionJobRequest) -> Dict[str, Any]:
        """Create a new ingestion job."""
        try:
            job_data = {
                'job_id': job_id,
                'tenant_id': tenant_id,  # Repository will handle UUID conversion
                'status': 'queued',
                'data_types': request.data_types,
                'start_date': request.start_date,  # Pass as date object, not string
                'end_date': request.end_date,      # Pass as date object, not string
                'created_at': datetime.now()       # Pass as datetime object, not string
            }
            
            job = self.repo.create_processing_job(job_data)
            logger.info(f"Created processing job {job_id}")
            return job
            
        except Exception as e:
            logger.error(f"Error creating processing job {job_id}: {e}")
            raise
    
    async def run_job(self, job_id: str, tenant_id: str, request: CreateIngestionJobRequest) -> Dict[str, Any]:
        """Run the data ingestion job."""
        try:
            # Update job status to processing
            self.repo.update_job_status(job_id, 'processing', started_at=datetime.now())
            
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
                    event_results = self._process_events(tenant_id, request)
                    results.update(event_results)
                    
                except Exception as e:
                    logger.error(f"Error processing events: {e}")
                    raise
            
            # Process users from SFTP
            if 'users' in request.data_types:
                try:
                    logger.info(f"Processing users for job {job_id}")
                    users_count = await self._process_users(tenant_id)
                    results['users_processed'] = users_count
                    
                except Exception as e:
                    logger.error(f"Error processing users: {e}")
                    raise
            
            # Process locations from SFTP
            if 'locations' in request.data_types:
                try:
                    logger.info(f"Processing locations for job {job_id}")
                    locations_count = await self._process_locations(tenant_id)
                    results['locations_processed'] = locations_count
                    
                except Exception as e:
                    logger.error(f"Error processing locations: {e}")
                    raise
            
            # Update job status to completed
            self.repo.update_job_status(
                job_id, 
                'completed', 
                completed_at=datetime.now(),
                records_processed=results
            )
            
            logger.info(f"Completed processing job {job_id}: {results}")
            return results
            
        except Exception as e:
            # Update job status to failed
            self.repo.update_job_status(
                job_id, 
                'failed', 
                completed_at=datetime.now(),
                error_message=str(e)
            )
            logger.error(f"Failed processing job {job_id}: {e}")
            raise
    
    def _process_events(self, tenant_id: str, request: CreateIngestionJobRequest) -> Dict[str, int]:
        """Process all event types from BigQuery."""
        try:
            # Initialize BigQuery client using tenant configuration from database
            bigquery_client = get_tenant_enhanced_bigquery_client(tenant_id)
            
            if not bigquery_client:
                raise ValueError(f"BigQuery configuration not found for tenant {tenant_id}")
            
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
                        count = self.repo.replace_event_data(
                            tenant_id,
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
            # Create a fresh Azure SFTP client using tenant configuration from database
            sftp_client = get_tenant_azure_sftp_client(tenant_id)
            
            if not sftp_client:
                raise ValueError(f"SFTP configuration not found for tenant {tenant_id}")
            
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
                
                count = self.repo.upsert_users(tenant_id, cleaned_users)
                logger.info(f"Processed {count} users from SFTP")
                return count
            else:
                logger.info("No users data found")
                return 0
                
        except Exception as e:
            logger.error(f"Error processing users: {e}")
            raise
    
    async def _process_locations(self, tenant_id: str) -> int:
        """Process locations from SFTP using tenant configuration, with local fallback."""
        try:
            import pandas as pd
            from pathlib import Path
            
            locations_data = None
            
            # First try to get from SFTP using tenant configuration
            try:
                sftp_client = get_tenant_azure_sftp_client(tenant_id)
                if sftp_client:
                    logger.info(f"Attempting to get locations from SFTP for tenant {tenant_id}")
                    locations_data = await sftp_client.get_latest_locations_data()
            except Exception as e:
                logger.warning(f"Failed to get locations from SFTP for tenant {tenant_id}: {e}")
            
            # Fallback to local file if SFTP failed or no data
            if locations_data is None or len(locations_data) == 0:
                logger.info("Falling back to local locations file")
                temp_data_dir = Path(__file__).parent.parent.parent / "temp_data"
                locations_file = temp_data_dir / "Locations_List1750281613134.xlsx"
                
                if locations_file.exists():
                    logger.info(f"Reading locations from local file: {locations_file}")
                    locations_data = pd.read_excel(locations_file)
                else:
                    logger.warning("No local locations file found")
                    return 0
                
                if locations_data is not None and len(locations_data) > 0:
                    # Clean the data: replace NaN values with None and convert to proper types
                    import numpy as np
                    locations_data = locations_data.replace({np.nan: None})
                    
                    # Map Excel columns to database columns (only include columns that exist in DB schema)
                    # Database schema: warehouse_id, warehouse_code, warehouse_name, city, state, country
                    column_mapping = {
                        'WAREHOUSE_ID': 'warehouse_id',      # Maps to warehouse_id in DB
                        'WAREHOUSE_CODE': 'warehouse_code',  # Maps to warehouse_code in DB
                        'WAREHOUSE_NAME': 'warehouse_name',  # Maps to warehouse_name in DB
                        'CITY': 'city',                     # Maps to city in DB
                        'STATE': 'state',                   # Maps to state in DB
                        'COUNTRY': 'country'                # Maps to country in DB
                    }
                    
                    # Filter columns to only include those that exist in our mapping AND in the Excel file
                    available_columns = [col for col in column_mapping.keys() if col in locations_data.columns]
                    filtered_data = locations_data[available_columns].copy()
                    
                    # Rename columns to match database schema
                    filtered_data = filtered_data.rename(columns=column_mapping)
                    
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
                    count = self.repo.upsert_locations(tenant_id, cleaned_locations)
                    logger.info(f"Processed {count} locations from local file")
                    return count
                else:
                    logger.info("Local locations file is empty")
                    return 0
            else:
                logger.warning(f"Local locations file not found: {locations_file}")
                return 0
                
        except Exception as e:
            logger.error(f"Error processing locations: {e}")
            raise
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status."""
        job = self.repo.get_job_by_id(job_id)
        if not job:
            raise Exception(f"Job {job_id} not found")
        return job
    
    def get_tenant_summary(self, tenant_id: str, start_date: date = None, end_date: date = None) -> Dict[str, Any]:
        """Get analytics summary for a tenant."""
        return self.repo.get_analytics_summary(tenant_id, start_date, end_date)
