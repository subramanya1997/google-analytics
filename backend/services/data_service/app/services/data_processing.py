"""
Simple data processing service using Supabase client
"""
import json
from datetime import datetime, date
from typing import Dict, Any, List
from uuid import uuid4
from loguru import logger

from app.database.supabase_client import SupabaseClient
from app.models.data_ingestion import DataIngestionRequest
from app.clients.bigquery_client import BigQueryClient
from app.clients.sftp_client import SFTPClient
from app.core.config import settings


class DataProcessingService:
    """Simple service for handling data processing operations."""
    
    def __init__(self):
        supabase_config = settings.get_supabase_client_config()
        self.supabase = SupabaseClient(supabase_config)
    
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
    
    def process_data_ingestion(self, job_id: str, request: DataIngestionRequest) -> Dict[str, Any]:
        """Process data ingestion request."""
        try:
            # Update job status to processing
            self.supabase.update_job_status(job_id, 'processing', started_at=datetime.now().isoformat())
            
            results = {
                'events_processed': 0,
                'users_processed': 0,
                'locations_processed': 0
            }
            
            # Process events from BigQuery
            if 'events' in request.data_types:
                try:
                    bigquery_config = settings.get_bigquery_config()
                    bigquery_client = BigQueryClient(bigquery_config)
                    
                    events_data = bigquery_client.get_date_range_events(
                        request.start_date.isoformat(),
                        request.end_date.isoformat()
                    )
                    
                    if events_data:
                        count = self.supabase.replace_events(
                            request.tenant_id,
                            request.start_date,
                            request.end_date,
                            events_data
                        )
                        results['events_processed'] = count
                        logger.info(f"Processed {count} events")
                    
                except Exception as e:
                    logger.error(f"Error processing events: {e}")
                    raise
            
            # Process users from SFTP
            if 'users' in request.data_types:
                try:
                    sftp_config = settings.get_sftp_config()
                    sftp_client = SFTPClient(sftp_config)
                    
                    users_data = sftp_client.get_latest_users_data()
                    
                    if users_data:
                        count = self.supabase.upsert_users(request.tenant_id, users_data)
                        results['users_processed'] = count
                        logger.info(f"Processed {count} users")
                    
                except Exception as e:
                    logger.error(f"Error processing users: {e}")
                    raise
            
            # Process locations from SFTP
            if 'locations' in request.data_types:
                try:
                    sftp_config = settings.get_sftp_config()
                    sftp_client = SFTPClient(sftp_config)
                    
                    locations_data = sftp_client.get_latest_locations_data()
                    
                    if locations_data:
                        count = self.supabase.upsert_locations(request.tenant_id, locations_data)
                        results['locations_processed'] = count
                        logger.info(f"Processed {count} locations")
                    
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
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status."""
        job = self.supabase.get_job_by_id(job_id)
        if not job:
            raise Exception(f"Job {job_id} not found")
        return job
