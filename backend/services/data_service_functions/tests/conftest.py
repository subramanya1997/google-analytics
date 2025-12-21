"""
Pytest configuration and fixtures for Azure Functions tests.
"""

import os
import pytest
from datetime import date, datetime
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock


# Set test environment variables before importing modules
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "postgres")
os.environ.setdefault("POSTGRES_DATABASE", "analytics_test")
os.environ.setdefault("DATA_INGESTION_CRON", "0 2 * * *")
os.environ.setdefault("SCHEDULER_API_URL", "http://localhost:8080")


@pytest.fixture
def sample_tenant_id() -> str:
    """Return a sample tenant ID for testing."""
    return "123e4567-e89b-12d3-a456-426614174000"


@pytest.fixture
def sample_job_id() -> str:
    """Return a sample job ID for testing."""
    return "job_abc123def456"


@pytest.fixture
def sample_ingestion_request() -> Dict[str, Any]:
    """Return a sample ingestion request body."""
    return {
        "start_date": date.today().isoformat(),
        "end_date": date.today().isoformat(),
        "data_types": ["events", "users", "locations"]
    }


@pytest.fixture
def sample_job_data(sample_job_id, sample_tenant_id) -> Dict[str, Any]:
    """Return a sample job data dictionary."""
    return {
        "job_id": sample_job_id,
        "tenant_id": sample_tenant_id,
        "status": "queued",
        "data_types": ["events", "users", "locations"],
        "start_date": date.today(),
        "end_date": date.today(),
        "created_at": datetime.now(),
    }


@pytest.fixture
def mock_repository():
    """Return a mock repository for testing."""
    mock = AsyncMock()
    
    # Configure default return values
    mock.create_processing_job.return_value = {
        "job_id": "job_test123",
        "status": "queued"
    }
    mock.update_job_status.return_value = True
    mock.get_job_by_id.return_value = {
        "job_id": "job_test123",
        "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
        "status": "completed"
    }
    mock.get_tenant_jobs.return_value = {
        "jobs": [],
        "total": 0
    }
    mock.get_data_availability_with_breakdown.return_value = {
        "summary": {
            "earliest_date": None,
            "latest_date": None,
            "total_events": 0
        }
    }
    mock.get_tenant_service_status.return_value = {
        "bigquery": {"enabled": True, "error": None},
        "sftp": {"enabled": True, "error": None}
    }
    
    return mock


@pytest.fixture
def mock_bigquery_client():
    """Return a mock BigQuery client for testing."""
    mock = MagicMock()
    
    # Configure extraction methods to return empty data
    mock._extract_purchase_events.return_value = []
    mock._extract_add_to_cart_events.return_value = []
    mock._extract_page_view_events.return_value = []
    mock._extract_view_search_results_events.return_value = []
    mock._extract_no_search_results_events.return_value = []
    mock._extract_view_item_events.return_value = []
    
    return mock


@pytest.fixture
def mock_sftp_client():
    """Return a mock SFTP client for testing."""
    import pandas as pd
    
    mock = MagicMock()
    
    # Configure data methods to return empty DataFrames
    mock._get_users_data_sync.return_value = pd.DataFrame()
    mock._get_locations_data_sync.return_value = pd.DataFrame()
    
    return mock


@pytest.fixture
def mock_http_request():
    """Create a mock HTTP request factory."""
    def _create_request(
        method: str = "GET",
        url: str = "/api/v1/test",
        headers: Dict[str, str] = None,
        body: bytes = None,
        route_params: Dict[str, str] = None,
        params: Dict[str, str] = None
    ):
        mock = MagicMock()
        mock.method = method
        mock.url = url
        mock.headers = headers or {}
        mock.route_params = route_params or {}
        mock.params = params or {}
        
        if body:
            mock.get_body.return_value = body
            mock.get_json.return_value = __import__("json").loads(body)
        else:
            mock.get_body.return_value = b""
            mock.get_json.return_value = {}
        
        return mock
    
    return _create_request

