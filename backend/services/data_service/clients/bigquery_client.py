import asyncio
import pandas as pd
from datetime import date
from typing import Dict, List, Optional, Any
from google.cloud import bigquery
from google.oauth2 import service_account
from loguru import logger


class BigQueryClient:
    """Enhanced BigQuery client for multi-tenant GA4 data access."""
    
    def __init__(self, tenant_config: Dict[str, Any]):
        """
        Initialize BigQuery client with tenant-specific configuration.
        
        Args:
            tenant_config: Dictionary containing:
                - tenant_id: Tenant identifier
                - project_id: BigQuery project ID
                - dataset_id: BigQuery dataset ID
                - service_account: Service account credentials dict
        """
        self.tenant_id = tenant_config['tenant_id']
        self.project_id = tenant_config['project_id']
        self.dataset_id = tenant_config['dataset_id']
        
        # Initialize credentials from service account dict
        credentials = service_account.Credentials.from_service_account_info(
            tenant_config['service_account']
        )
        
        # Initialize BigQuery client
        self.client = bigquery.Client(
            credentials=credentials,
            project=self.project_id
        )
        
        logger.info(f"Initialized BigQuery client for tenant {self.tenant_id}")
    
    async def get_events_for_date_range(
        self, 
        start_date: date, 
        end_date: date,
        event_types: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get GA4 events for a specific date range.
        
        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            event_types: Optional list of event types to filter
            limit: Optional limit on number of records
            
        Returns:
            DataFrame containing the events data
        """
        # Convert dates to BigQuery table suffix format
        start_suffix = start_date.strftime("%Y%m%d")
        end_suffix = end_date.strftime("%Y%m%d")
        
        # Build the base query
        query = f"""
        SELECT 
            event_date,
            event_timestamp,
            event_name,
            user_pseudo_id,
            user_properties,
            event_params,
            items,
            device,
            geo
        FROM `{self.project_id}.{self.dataset_id}.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '{start_suffix}' AND '{end_suffix}'
        """
        
        # Add event type filter if specified
        if event_types:
            event_filter = "', '".join(event_types)
            query += f" AND event_name IN ('{event_filter}')"
        
        # Add ordering for consistent results
        query += " ORDER BY event_timestamp"
        
        # Add limit if specified
        if limit:
            query += f" LIMIT {limit}"
        
        logger.info(f"Querying BigQuery for {start_date} to {end_date}, tenant: {self.tenant_id}")
        logger.debug(f"Query: {query}")
        
        try:
            # Execute query in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None, 
                self._execute_query, 
                query
            )
            
            logger.info(f"Retrieved {len(df)} events for tenant {self.tenant_id}")
            return df
            
        except Exception as e:
            logger.error(f"Error querying BigQuery for tenant {self.tenant_id}: {e}")
            raise
    
    def _execute_query(self, query: str) -> pd.DataFrame:
        """Execute BigQuery query and return DataFrame."""
        query_job = self.client.query(query)
        return query_job.to_dataframe()
    
    async def get_available_dates(
        self, 
        start_date: date, 
        end_date: date
    ) -> List[str]:
        """
        Check which dates have data available in the dataset.
        
        Args:
            start_date: Start date to check
            end_date: End date to check
            
        Returns:
            List of available dates in YYYYMMDD format
        """
        start_suffix = start_date.strftime("%Y%m%d")
        end_suffix = end_date.strftime("%Y%m%d")
        
        query = f"""
        SELECT table_name
        FROM `{self.project_id}.{self.dataset_id}.INFORMATION_SCHEMA.TABLES`
        WHERE table_name LIKE 'events_%'
        AND table_name BETWEEN 'events_{start_suffix}' AND 'events_{end_suffix}'
        ORDER BY table_name
        """
        
        try:
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                self._execute_query,
                query
            )
            
            # Extract dates from table names
            dates = [table.replace('events_', '') for table in df['table_name']]
            logger.info(f"Found {len(dates)} available dates for tenant {self.tenant_id}")
            return dates
            
        except Exception as e:
            logger.error(f"Error checking available dates for tenant {self.tenant_id}: {e}")
            raise
    
    async def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get information about a specific table.
        
        Args:
            table_name: Name of the table (e.g., 'events_20240115')
            
        Returns:
            Dictionary containing table information
        """
        try:
            table_ref = self.client.dataset(self.dataset_id).table(table_name)
            table = self.client.get_table(table_ref)
            
            return {
                'table_id': table.table_id,
                'created': table.created,
                'modified': table.modified,
                'num_rows': table.num_rows,
                'num_bytes': table.num_bytes,
                'description': table.description,
            }
            
        except Exception as e:
            logger.error(f"Error getting table info for {table_name}: {e}")
            raise
    
    def close(self) -> None:
        """Close the BigQuery client connection."""
        if hasattr(self.client, 'close'):
            self.client.close()
        logger.info(f"Closed BigQuery client for tenant {self.tenant_id}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
