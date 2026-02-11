"""
BigQuery client for Azure Functions.

This is an adapted version of the original BigQuery client that removes
ThreadPoolExecutor patterns since Azure Functions handles parallelism
through Durable Functions activities.
"""

from typing import Any

import logging
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd

logger = logging.getLogger(__name__)


class BigQueryClient:
    """
    BigQuery client for extracting Google Analytics 4 (GA4) event data.

    This client provides methods to query BigQuery for GA4 events across multiple
    event types including purchases, cart events, page views, searches, and product
    views. It uses service account credentials for authentication and returns
    data in a format suitable for database insertion.

    The client is designed for serverless environments (Azure Functions) and
    handles large date range queries efficiently. Each event type has a dedicated
    extraction method with optimized SQL queries.

    Attributes:
        project_id: Google Cloud project ID containing the BigQuery dataset.
        dataset_id: BigQuery dataset ID containing GA4 event tables.
        client: Authenticated BigQuery client instance.

    Example:
        >>> config = {
        ...     "project_id": "my-project",
        ...     "dataset_id": "analytics_123456789",
        ...     "service_account": {...}
        ... }
        >>> client = BigQueryClient(config)
        >>> events = client.get_date_range_events("2024-01-01", "2024-01-07")
    """

    def __init__(self, bigquery_config: dict[str, Any]) -> None:
        """
        Initialize BigQuery client with tenant-specific configuration.

        Creates an authenticated BigQuery client using service account credentials
        from the configuration. The client is configured for the specific
        project and dataset containing GA4 event data.

        Args:
            bigquery_config: Dictionary containing:
                - project_id: Google Cloud project ID (str)
                - dataset_id: BigQuery dataset ID (str)
                - service_account: Service account credentials dictionary

        Raises:
            ValueError: If required configuration fields are missing.
            google.auth.exceptions.GoogleAuthError: If authentication fails.

        Note:
            - Service account credentials must have BigQuery read permissions
            - Client is created fresh for each operation (stateless)
            - Credentials are loaded from service account info dictionary
        """
        self.project_id = bigquery_config["project_id"]
        self.dataset_id = bigquery_config["dataset_id"]

        # Initialize credentials from service account dict
        credentials = service_account.Credentials.from_service_account_info(
            bigquery_config["service_account"]
        )

        # Initialize BigQuery client
        self.client = bigquery.Client(credentials=credentials, project=self.project_id)

        logger.info(
            f"Initialized BigQuery client for {self.project_id}.{self.dataset_id}"
        )

    def get_date_range_events(
        self, start_date: str, end_date: str
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Extract all GA4 event types for a specified date range.

        This method queries BigQuery for all supported event types in parallel,
        returning a dictionary mapping event type names to their respective
        event records. Each event type is extracted using optimized SQL queries
        that select relevant fields and preserve raw data in JSON format.

        Args:
            start_date: Start date in YYYY-MM-DD format (inclusive).
            end_date: End date in YYYY-MM-DD format (inclusive).

        Returns:
            dict[str, list[dict[str, Any]]]: Dictionary mapping event type names
            to lists of event records. Event types include:
                - purchase: Completed purchase transactions
                - add_to_cart: Items added to shopping cart
                - page_view: Page view events
                - view_search_results: Successful search queries
                - no_search_results: Failed search queries (no results)
                - view_item: Product detail page views

        Raises:
            Exception: If BigQuery query execution fails or authentication errors occur.

        Note:
            - Queries use wildcard table matching (events_*) for date partitioning
            - Each event type is extracted independently (failures don't cascade)
            - Raw event data is preserved in JSON format for future analysis
            - Events are ordered by timestamp for consistent processing
            - Empty results are returned as empty lists, not None

        Example:
            >>> events = client.get_date_range_events("2024-01-01", "2024-01-07")
            >>> len(events["purchase"])
            150
            >>> events["purchase"][0]["param_transaction_id"]
            'TXN-12345'
        """
        results = {}

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
        Execute a BigQuery SQL query and return results as a pandas DataFrame.

        This internal method handles query execution, error handling, and
        result conversion to pandas DataFrame for easy data manipulation.

        Args:
            query: SQL query string to execute against BigQuery.

        Returns:
            pd.DataFrame: Query results as a pandas DataFrame with columns
                        matching the SELECT clause.

        Raises:
            Exception: If query execution fails, with detailed error logging
                      including the query text for debugging.

        Note:
            - Uses BigQuery client's query method with automatic result conversion
            - Errors are logged with full query text for troubleshooting
            - Large result sets are handled efficiently by BigQuery
        """
        try:
            query_job = self.client.query(query)
            return query_job.to_dataframe()
        except Exception as e:
            logger.error(f"BigQuery execution error: {e}")
            logger.error(f"Query: {query}")
            raise

    def _extract_purchase_events(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """
        Extract purchase events from GA4 BigQuery tables.

        Queries BigQuery for purchase events within the date range, extracting
        transaction details, revenue, customer information, and product data.
        Includes e-commerce data and preserves raw event structure.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            list[dict[str, Any]]: List of purchase event dictionaries containing
                                transaction IDs, revenue, items, customer data, etc.

        Note:
            - Extracts ecommerce.purchase_revenue for revenue calculations
            - Includes items array as JSON string for product details
            - Preserves user properties and event parameters
            - Includes device and geo information for analytics
        """
        start_suffix = start_date.replace("-", "")
        end_suffix = end_date.replace("-", "")

        query = f"""
        SELECT
            event_date,
            CAST(event_timestamp AS STRING) as event_timestamp,
            user_pseudo_id,
            (SELECT COALESCE(CAST(value.int_value AS STRING), value.string_value) FROM UNNEST(user_properties) WHERE key = 'WebUserId') as user_prop_webuserid,
            (SELECT COALESCE(value.string_value, CAST(value.int_value AS STRING)) FROM UNNEST(user_properties) WHERE key = 'default_branch_id') as user_prop_default_branch_id,
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
    ) -> list[dict[str, Any]]:
        """
        Extract add_to_cart events from GA4 BigQuery tables.

        Queries BigQuery for cart addition events, extracting item details,
        customer information, and session data for cart abandonment analysis.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            list[dict[str, Any]]: List of add_to_cart event dictionaries.

        Note:
            - Extracts first item details for quick access
            - Includes full items array as JSON for complete cart contents
            - Preserves session and user identification data
        """
        start_suffix = start_date.replace("-", "")
        end_suffix = end_date.replace("-", "")

        query = f"""
        SELECT
            event_date,
            CAST(event_timestamp AS STRING) as event_timestamp,
            user_pseudo_id,
            (SELECT COALESCE(CAST(value.int_value AS STRING), value.string_value) FROM UNNEST(user_properties) WHERE key = 'WebUserId') as user_prop_webuserid,
            (SELECT COALESCE(value.string_value, CAST(value.int_value AS STRING)) FROM UNNEST(user_properties) WHERE key = 'default_branch_id') as user_prop_default_branch_id,
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
    ) -> list[dict[str, Any]]:
        """
        Extract page_view events from GA4 BigQuery tables.

        Queries BigQuery for page view events, extracting page information,
        referrer data, and user session details for traffic analysis.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            list[dict[str, Any]]: List of page_view event dictionaries.

        Note:
            - Includes page title, location (URL), and referrer
            - Preserves device and geo information
            - Used for traffic pattern analysis
        """
        start_suffix = start_date.replace("-", "")
        end_suffix = end_date.replace("-", "")

        query = f"""
        SELECT
            event_date,
            CAST(event_timestamp AS STRING) as event_timestamp,
            user_pseudo_id,
            (SELECT COALESCE(CAST(value.int_value AS STRING), value.string_value) FROM UNNEST(user_properties) WHERE key = 'WebUserId') as user_prop_webuserid,
            (SELECT COALESCE(value.string_value, CAST(value.int_value AS STRING)) FROM UNNEST(user_properties) WHERE key = 'default_branch_id') as user_prop_default_branch_id,
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
    ) -> list[dict[str, Any]]:
        """
        Extract view_search_results events from GA4 BigQuery tables.

        Queries BigQuery for successful search events where results were returned,
        extracting search terms and user interaction data.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            list[dict[str, Any]]: List of view_search_results event dictionaries.

        Note:
            - Extracts search_term parameter
            - Used for search success rate analysis
        """
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
    ) -> list[dict[str, Any]]:
        """
        Extract no_search_results events from GA4 BigQuery tables.

        Queries BigQuery for failed search events where no results were returned,
        extracting search terms for search optimization analysis.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            list[dict[str, Any]]: List of no_search_results event dictionaries.

        Note:
            - Handles both 'no_search_results' and 'view_search_results_no_results' events
            - Extracts no_search_results_term parameter
            - Used for identifying search optimization opportunities
        """
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
    ) -> list[dict[str, Any]]:
        """
        Extract view_item events from GA4 BigQuery tables.

        Queries BigQuery for product detail page view events, extracting
        product information and user interaction data.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.

        Returns:
            list[dict[str, Any]]: List of view_item event dictionaries.

        Note:
            - Extracts product details from items array
            - Includes product ID, name, category, and price
            - Used for product interest analysis
        """
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
