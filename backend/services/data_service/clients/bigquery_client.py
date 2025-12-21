"""
Enhanced BigQuery client for comprehensive GA4 analytics data extraction
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
from loguru import logger

# Dedicated thread pool for BigQuery operations
# Allows parallel extraction of all 6 event types
_BIGQUERY_EXECUTOR = ThreadPoolExecutor(
    max_workers=6,  # One per event type
    thread_name_prefix="bigquery-worker"
)


class BigQueryClient:
    """Enhanced BigQuery client for event-specific GA4 data extraction."""

    def __init__(self, bigquery_config: Dict[str, Any]):
        """Initialize BigQuery client with configuration."""
        self.project_id = bigquery_config["project_id"]
        self.dataset_id = bigquery_config["dataset_id"]

        # Initialize credentials from service account dict
        credentials = service_account.Credentials.from_service_account_info(
            bigquery_config["service_account"]
        )

        # Initialize BigQuery client
        self.client = bigquery.Client(credentials=credentials, project=self.project_id)

        logger.info(
            f"Initialized Enhanced BigQuery client for {self.project_id}.{self.dataset_id}"
        )

    def get_date_range_events(
        self, start_date: str, end_date: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all event types for a date range, properly structured for analytics.
        (Legacy synchronous method - kept for backward compatibility)

        Returns:
            Dictionary with event types as keys and lists of records as values
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

    async def get_date_range_events_async(
        self, start_date: str, end_date: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all event types in parallel for maximum performance.
        
        Runs all 6 event type extractions concurrently using thread pool,
        providing up to 6x performance improvement over sequential extraction.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            Dictionary with event types as keys and lists of records as values
        """
        logger.info(f"Starting parallel extraction for {start_date} to {end_date}")
        
        event_extractors = {
            "purchase": self._extract_purchase_events,
            "add_to_cart": self._extract_add_to_cart_events,
            "page_view": self._extract_page_view_events,
            "view_search_results": self._extract_view_search_results_events,
            "no_search_results": self._extract_no_search_results_events,
            "view_item": self._extract_view_item_events,
        }

        # Run all extractors in parallel using thread pool
        loop = asyncio.get_event_loop()
        tasks = []
        for event_type, extractor in event_extractors.items():
            logger.info(f"Scheduling {event_type} extraction")
            task = loop.run_in_executor(
                _BIGQUERY_EXECUTOR, 
                extractor, 
                start_date, 
                end_date
            )
            tasks.append((event_type, task))

        # Wait for all tasks to complete
        results = {}
        for event_type, task in tasks:
            try:
                events = await task
                results[event_type] = events
                logger.info(f"Extracted {len(events)} {event_type} events")
            except Exception as e:
                logger.error(f"Error extracting {event_type} events: {e}")
                results[event_type] = []

        total_events = sum(len(events) for events in results.values())
        logger.info(f"Parallel extraction complete: {total_events} total events across all types")
        
        return results

    def _execute_query(self, query: str) -> pd.DataFrame:
        """Execute BigQuery query and return DataFrame."""
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
        """Extract purchase events with revenue and transaction details."""
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
