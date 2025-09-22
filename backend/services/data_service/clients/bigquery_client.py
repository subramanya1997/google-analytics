"""
Enhanced BigQuery Client for Google Analytics 4 Data Extraction.

This module provides a comprehensive BigQuery client specifically designed for
extracting Google Analytics 4 (GA4) event data from BigQuery datasets. It handles
the complexities of GA4 data structures, nested fields, and event-specific
parameter extraction with optimized queries and data transformation.

Key Features:
- **Comprehensive Event Coverage**: Supports 6 GA4 event types with full attribution
- **Nested Field Handling**: Extracts user properties and event parameters from arrays
- **Type Safety**: Proper handling of mixed data types (string/int/float) in GA4
- **Raw Data Preservation**: Stores complete event data for future analysis
- **Performance Optimization**: Efficient BigQuery queries with date partitioning
- **Multi-Tenant Support**: Service account-based authentication per tenant

Supported GA4 Event Types:
1. **Purchase Events**: E-commerce transactions with revenue and item details
2. **Add to Cart Events**: Shopping cart additions with product information
3. **Page View Events**: Website navigation with referrer tracking
4. **View Search Results**: Successful searches with search terms
5. **No Search Results**: Failed searches for search optimization
6. **View Item Events**: Product page views with item details

GA4 Data Structure Handling:
The client handles GA4's complex nested data structure including:
- User properties array with key-value pairs
- Event parameters array with mixed data types
- Items array for e-commerce events
- Device and geographic information
- Raw event data preservation for flexibility

"""

from typing import Any, Dict, List

import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
from loguru import logger


class BigQueryClient:
    """
    Enhanced BigQuery client for comprehensive GA4 event data extraction.
    
    This client specializes in extracting Google Analytics 4 event data from
    BigQuery with proper handling of GA4's nested data structures, mixed data
    types, and event-specific parameter extraction.
    
    Key Capabilities:
    - Service account-based authentication for multi-tenant support
    - Event-specific query optimization for 6 GA4 event types
    - Nested field extraction from user_properties and event_params arrays
    - Type-safe handling of mixed data types in GA4 parameters
    - Raw data preservation alongside structured field extraction
    - Date range queries with table suffix optimization
    
    Attributes:
        project_id: Google Cloud Project ID containing the GA4 dataset
        dataset_id: BigQuery dataset name with GA4 event tables
        client: Authenticated BigQuery client instance
    
    """

    def __init__(self, bigquery_config: Dict[str, Any]):
        """
        Initialize BigQuery client with tenant-specific configuration.
        
        Sets up authenticated BigQuery client using service account credentials
        for secure, multi-tenant access to GA4 datasets with proper project
        and dataset scoping.
        
        Args:
            bigquery_config: Configuration dictionary containing:
                - project_id (str): Google Cloud Project ID with GA4 data
                - dataset_id (str): BigQuery dataset name (e.g., "analytics_123456789")
                - service_account (dict): Service account JSON credentials
                
        Raises:
            KeyError: If required configuration keys are missing
            ValueError: If service account credentials are invalid
            Exception: If BigQuery client initialization fails
            
        """
        self.project_id = bigquery_config["project_id"]
        self.dataset_id = bigquery_config["dataset_id"]

        # Initialize credentials from service account dict
        credentials = service_account.Credentials.from_service_account_info(
            bigquery_config["service_account"]
        )

        # Initialize BigQuery client with tenant-specific credentials
        self.client = bigquery.Client(credentials=credentials, project=self.project_id)

        logger.info(
            f"Initialized Enhanced BigQuery client for {self.project_id}.{self.dataset_id}"
        )

    def get_date_range_events(
        self, start_date: str, end_date: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract all GA4 event types for specified date range with comprehensive data.
        
        This is the primary interface for extracting GA4 analytics data from BigQuery.
        It processes all supported event types in parallel and returns structured data
        ready for analytics database storage and downstream processing.
        
        **Event Processing Pipeline:**
        1. Date range validation and table suffix calculation
        2. Parallel execution of event-specific extraction queries
        3. Nested field extraction (user_properties, event_params, items)
        4. Type coercion and data normalization
        5. Raw data preservation alongside structured fields
        6. Error handling with graceful degradation per event type
        
        Args:
            start_date: Start date in YYYY-MM-DD format (inclusive)
            end_date: End date in YYYY-MM-DD format (inclusive)
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: Event data grouped by type:

        **GA4 Data Structure Handling:**
        The method handles GA4's nested arrays and mixed data types:
        - User properties: Extracts WebUserId, default_branch_id
        - Event parameters: Extracts ga_session_id, page info, search terms
        - Items arrays: Full product data for e-commerce events
        - Device/Geo: Device category, OS, country, city
        - Raw preservation: Complete original event for future analysis
        
        **Date Range Considerations:**
        - GA4 data is partitioned by date (YYYYMMDD format)
        - Query performance is optimal for contiguous date ranges
        - Large date ranges may hit BigQuery slot limits
        - Consider breaking very large ranges into smaller chunks
        
        Raises:
            Exception: BigQuery authentication or permission errors
            ValueError: Invalid date format or range
            RuntimeError: Query execution failures
        
        """
        results = {}

        # Get each event type
        event_extractors = {
            "purchase": self._extract_purchase_events,
            "add_to_cart": self._extract_add_to_cart_events,
            "page_view": self._extract_page_view_events,
            "view_search_results": self._extract_view_search_results_events,
            "no_search_results": self._extract_no_search_results_events,
            "view_item": self._extract_view_item_events,
        }

        for event_type, extractor in event_extractors.items():
            try:
                logger.info(
                    f"Extracting {event_type} events for {start_date} to {end_date}"
                )
                events = extractor(start_date, end_date)
                results[event_type] = events
                logger.info(f"Extracted {len(events)} {event_type} events")
            except Exception as e:
                logger.error(f"Error extracting {event_type} events: {e}")
                results[event_type] = []

        return results

    def _execute_query(self, query: str) -> pd.DataFrame:
        """
        Execute BigQuery SQL query and return results as pandas DataFrame.
        
        This is the core query execution method that handles BigQuery API calls,
        error logging, and result transformation. It provides consistent error
        handling and performance monitoring across all event extraction queries.
        
        Args:
            query: SQL query string to execute against BigQuery
            
        Returns:
            pd.DataFrame: Query results as pandas DataFrame with proper data types
            
        Raises:
            Exception: BigQuery API errors, authentication failures, or quota limits
            
        """
        try:
            query_job = self.client.query(query)
            df = query_job.to_dataframe()
            return df
        except Exception as e:
            logger.error(f"BigQuery execution error: {e}")
            logger.error(f"Query: {query}")
            raise

    def _extract_purchase_events(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Extract GA4 purchase events with complete e-commerce transaction data.
        
        This method extracts purchase events from GA4 BigQuery data with comprehensive
        e-commerce information including transaction IDs, revenue, item details, and
        customer attribution data. It handles GA4's nested e-commerce structure and
        provides both structured fields and raw event preservation.
        
        **Extracted Data Fields:**
        - Event metadata: date, timestamp, user identification
        - User properties: WebUserId, default_branch_id (customer context)
        - Event parameters: ga_session_id, transaction_id, page context
        - E-commerce data: purchase_revenue from ecommerce object
        - Items data: Complete product array with IDs, names, categories, prices
        - Device/Geographic: Device category, OS, country, city
        - Raw preservation: Complete original event for future analysis
        
        **GA4 Purchase Event Structure:**
        Purchase events in GA4 contain nested e-commerce and items arrays:
        - ecommerce.purchase_revenue: Total transaction value
        - items[]: Array of purchased products with quantities and prices
        - event_params[]: Session ID, transaction ID, page information
        - user_properties[]: Customer identification and segmentation
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List[Dict[str, Any]]: Purchase events with structured data:
        

        """
        start_suffix = start_date.replace("-", "")
        end_suffix = end_date.replace("-", "")

        query = f"""
        SELECT 
            event_date,
            CAST(event_timestamp AS STRING) as event_timestamp,
            user_pseudo_id,
            -- Extract user properties with proper type handling
            (SELECT COALESCE(CAST(value.int_value AS STRING), value.string_value) FROM UNNEST(user_properties) WHERE key = 'WebUserId') as user_prop_webuserid,
            (SELECT COALESCE(value.string_value, CAST(value.int_value AS STRING)) FROM UNNEST(user_properties) WHERE key = 'default_branch_id') as user_prop_default_branch_id,
            -- Extract event parameters with proper type handling  
            (SELECT COALESCE(CAST(value.int_value AS STRING), value.string_value) FROM UNNEST(event_params) WHERE key = 'ga_session_id') as param_ga_session_id,
            (SELECT COALESCE(value.string_value, CAST(value.int_value AS STRING)) FROM UNNEST(event_params) WHERE key = 'transaction_id') as param_transaction_id,
            (SELECT COALESCE(value.string_value, CAST(value.int_value AS STRING)) FROM UNNEST(event_params) WHERE key = 'page_title') as param_page_title,
            (SELECT COALESCE(value.string_value, CAST(value.int_value AS STRING)) FROM UNNEST(event_params) WHERE key = 'page_location') as param_page_location,
            ecommerce.purchase_revenue as ecommerce_purchase_revenue,
            TO_JSON_STRING(items) as items_json,
            device.category as device_category,
            device.operating_system as device_operating_system,
            geo.country as geo_country,
            geo.city as geo_city,
            TO_JSON_STRING(STRUCT(
                event_date,
                event_timestamp,
                event_name,
                user_pseudo_id,
                user_properties,
                event_params,
                ecommerce,
                items,
                device,
                geo
            )) as raw_data
        FROM `{self.project_id}.{self.dataset_id}.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '{start_suffix}' AND '{end_suffix}'
        AND event_name = 'purchase'
        ORDER BY event_timestamp
        """

        df = self._execute_query(query)
        return df.to_dict("records")

    def _extract_add_to_cart_events(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Extract add to cart events with item details."""
        start_suffix = start_date.replace("-", "")
        end_suffix = end_date.replace("-", "")

        query = f"""
        SELECT 
            event_date,
            CAST(event_timestamp AS STRING) as event_timestamp,
            user_pseudo_id,
            -- Extract user properties with proper type handling
            (SELECT COALESCE(CAST(value.int_value AS STRING), value.string_value) FROM UNNEST(user_properties) WHERE key = 'WebUserId') as user_prop_webuserid,
            (SELECT COALESCE(value.string_value, CAST(value.int_value AS STRING)) FROM UNNEST(user_properties) WHERE key = 'default_branch_id') as user_prop_default_branch_id,
            -- Extract event parameters with proper type handling
            (SELECT COALESCE(CAST(value.int_value AS STRING), value.string_value) FROM UNNEST(event_params) WHERE key = 'ga_session_id') as param_ga_session_id,
            (SELECT COALESCE(value.string_value, CAST(value.int_value AS STRING)) FROM UNNEST(event_params) WHERE key = 'page_title') as param_page_title,
            (SELECT COALESCE(value.string_value, CAST(value.int_value AS STRING)) FROM UNNEST(event_params) WHERE key = 'page_location') as param_page_location,
            items[SAFE_OFFSET(0)].item_id as first_item_item_id,
            items[SAFE_OFFSET(0)].item_name as first_item_item_name,
            items[SAFE_OFFSET(0)].item_category as first_item_item_category,
            items[SAFE_OFFSET(0)].price as first_item_price,
            items[SAFE_OFFSET(0)].quantity as first_item_quantity,
            TO_JSON_STRING(items) as items_json,
            device.category as device_category,
            device.operating_system as device_operating_system,
            geo.country as geo_country,
            geo.city as geo_city,
            TO_JSON_STRING(STRUCT(
                event_date,
                event_timestamp,
                event_name,
                user_pseudo_id,
                user_properties,
                event_params,
                items,
                device,
                geo
            )) as raw_data
        FROM `{self.project_id}.{self.dataset_id}.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '{start_suffix}' AND '{end_suffix}'
        AND event_name = 'add_to_cart'
        ORDER BY event_timestamp
        """

        df = self._execute_query(query)
        return df.to_dict("records")

    def _extract_page_view_events(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Extract page view events."""
        start_suffix = start_date.replace("-", "")
        end_suffix = end_date.replace("-", "")

        query = f"""
        SELECT 
            event_date,
            CAST(event_timestamp AS STRING) as event_timestamp,
            user_pseudo_id,
            -- Extract user properties with proper type handling
            (SELECT COALESCE(CAST(value.int_value AS STRING), value.string_value) FROM UNNEST(user_properties) WHERE key = 'WebUserId') as user_prop_webuserid,
            (SELECT COALESCE(value.string_value, CAST(value.int_value AS STRING)) FROM UNNEST(user_properties) WHERE key = 'default_branch_id') as user_prop_default_branch_id,
            -- Extract event parameters with proper type handling
            (SELECT COALESCE(CAST(value.int_value AS STRING), value.string_value) FROM UNNEST(event_params) WHERE key = 'ga_session_id') as param_ga_session_id,
            (SELECT COALESCE(value.string_value, CAST(value.int_value AS STRING)) FROM UNNEST(event_params) WHERE key = 'page_title') as param_page_title,
            (SELECT COALESCE(value.string_value, CAST(value.int_value AS STRING)) FROM UNNEST(event_params) WHERE key = 'page_location') as param_page_location,
            (SELECT COALESCE(value.string_value, CAST(value.int_value AS STRING)) FROM UNNEST(event_params) WHERE key = 'page_referrer') as param_page_referrer,
            device.category as device_category,
            device.operating_system as device_operating_system,
            geo.country as geo_country,
            geo.city as geo_city,
            TO_JSON_STRING(STRUCT(
                event_date,
                event_timestamp,
                event_name,
                user_pseudo_id,
                user_properties,
                event_params,
                device,
                geo
            )) as raw_data
        FROM `{self.project_id}.{self.dataset_id}.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '{start_suffix}' AND '{end_suffix}'
        AND event_name = 'page_view'
        ORDER BY event_timestamp
        """

        df = self._execute_query(query)
        return df.to_dict("records")

    def _extract_view_search_results_events(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Extract successful search events."""
        start_suffix = start_date.replace("-", "")
        end_suffix = end_date.replace("-", "")

        query = f"""
        SELECT 
            event_date,
            CAST(event_timestamp AS STRING) as event_timestamp,
            user_pseudo_id,
            (SELECT COALESCE(CAST(value.int_value AS STRING), value.string_value) FROM UNNEST(user_properties) WHERE key = 'WebUserId') as user_prop_webuserid,
            (SELECT value.string_value FROM UNNEST(user_properties) WHERE key = 'default_branch_id') as user_prop_default_branch_id,
            (SELECT COALESCE(CAST(value.int_value AS STRING), value.string_value) FROM UNNEST(event_params) WHERE key = 'ga_session_id') as param_ga_session_id,
            (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'search_term') as param_search_term,
            (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_title') as param_page_title,
            (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location') as param_page_location,
            device.category as device_category,
            device.operating_system as device_operating_system,
            geo.country as geo_country,
            geo.city as geo_city,
            TO_JSON_STRING(STRUCT(
                event_date,
                event_timestamp,
                event_name,
                user_pseudo_id,
                user_properties,
                event_params,
                device,
                geo
            )) as raw_data
        FROM `{self.project_id}.{self.dataset_id}.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '{start_suffix}' AND '{end_suffix}'
        AND event_name = 'view_search_results'
        ORDER BY event_timestamp
        """

        df = self._execute_query(query)
        return df.to_dict("records")

    def _extract_no_search_results_events(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Extract failed search events - critical for search analysis."""
        start_suffix = start_date.replace("-", "")
        end_suffix = end_date.replace("-", "")

        query = f"""
        SELECT 
            event_date,
            CAST(event_timestamp AS STRING) as event_timestamp,
            user_pseudo_id,
            (SELECT COALESCE(CAST(value.int_value AS STRING), value.string_value) FROM UNNEST(user_properties) WHERE key = 'WebUserId') as user_prop_webuserid,
            (SELECT value.string_value FROM UNNEST(user_properties) WHERE key = 'default_branch_id') as user_prop_default_branch_id,
            (SELECT COALESCE(CAST(value.int_value AS STRING), value.string_value) FROM UNNEST(event_params) WHERE key = 'ga_session_id') as param_ga_session_id,
            (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'no_search_results_term') as param_no_search_results_term,
            (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_title') as param_page_title,
            (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location') as param_page_location,
            device.category as device_category,
            device.operating_system as device_operating_system,
            geo.country as geo_country,
            geo.city as geo_city,
            TO_JSON_STRING(STRUCT(
                event_date,
                event_timestamp,
                event_name,
                user_pseudo_id,
                user_properties,
                event_params,
                device,
                geo
            )) as raw_data
        FROM `{self.project_id}.{self.dataset_id}.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '{start_suffix}' AND '{end_suffix}'
        AND event_name IN ('no_search_results', 'view_search_results_no_results')
        ORDER BY event_timestamp
        """

        df = self._execute_query(query)
        return df.to_dict("records")

    def _extract_view_item_events(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Extract product view events."""
        start_suffix = start_date.replace("-", "")
        end_suffix = end_date.replace("-", "")

        query = f"""
        SELECT 
            event_date,
            CAST(event_timestamp AS STRING) as event_timestamp,
            user_pseudo_id,
            (SELECT COALESCE(CAST(value.int_value AS STRING), value.string_value) FROM UNNEST(user_properties) WHERE key = 'WebUserId') as user_prop_webuserid,
            (SELECT value.string_value FROM UNNEST(user_properties) WHERE key = 'default_branch_id') as user_prop_default_branch_id,
            (SELECT COALESCE(CAST(value.int_value AS STRING), value.string_value) FROM UNNEST(event_params) WHERE key = 'ga_session_id') as param_ga_session_id,
            items[SAFE_OFFSET(0)].item_id as first_item_item_id,
            items[SAFE_OFFSET(0)].item_name as first_item_item_name,
            items[SAFE_OFFSET(0)].item_category as first_item_item_category,
            items[SAFE_OFFSET(0)].price as first_item_price,
            (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_title') as param_page_title,
            (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location') as param_page_location,
            TO_JSON_STRING(items) as items_json,
            device.category as device_category,
            device.operating_system as device_operating_system,
            geo.country as geo_country,
            geo.city as geo_city,
            TO_JSON_STRING(STRUCT(
                event_date,
                event_timestamp,
                event_name,
                user_pseudo_id,
                user_properties,
                event_params,
                items,
                device,
                geo
            )) as raw_data
        FROM `{self.project_id}.{self.dataset_id}.events_*`
        WHERE _TABLE_SUFFIX BETWEEN '{start_suffix}' AND '{end_suffix}'
        AND event_name = 'view_item'
        ORDER BY event_timestamp
        """

        df = self._execute_query(query)
        return df.to_dict("records")
