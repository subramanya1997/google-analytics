"""
Tests for activity functions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date
import pandas as pd


class TestProcessEventsActivity:
    """Tests for the process events activity."""
    
    @pytest.mark.asyncio
    async def test_process_events_with_no_client_raises_error(
        self, sample_job_id, sample_tenant_id
    ):
        """Test that missing BigQuery client raises error."""
        from activities.process_events import process_events
        
        with patch("activities.process_events.get_tenant_bigquery_client", return_value=None):
            with pytest.raises(ValueError, match="BigQuery configuration not found"):
                await process_events(
                    job_id=sample_job_id,
                    tenant_id=sample_tenant_id,
                    start_date="2024-01-01",
                    end_date="2024-01-31",
                    event_type="purchase"
                )
    
    @pytest.mark.asyncio
    async def test_process_events_with_empty_data_returns_zero(
        self, sample_job_id, sample_tenant_id, mock_bigquery_client, mock_repository
    ):
        """Test that empty event data returns 0."""
        from activities.process_events import process_events
        
        mock_bigquery_client._extract_purchase_events.return_value = []
        
        with patch("activities.process_events.get_tenant_bigquery_client", return_value=mock_bigquery_client):
            with patch("activities.process_events.create_repository", return_value=mock_repository):
                count = await process_events(
                    job_id=sample_job_id,
                    tenant_id=sample_tenant_id,
                    start_date="2024-01-01",
                    end_date="2024-01-31",
                    event_type="purchase"
                )
        
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_process_events_with_data_returns_count(
        self, sample_job_id, sample_tenant_id, mock_bigquery_client, mock_repository
    ):
        """Test that event data is processed and count returned."""
        from activities.process_events import process_events
        
        # Mock events data
        mock_events = [
            {"event_date": "20240101", "event_timestamp": "123456", "user_pseudo_id": "user1"},
            {"event_date": "20240101", "event_timestamp": "123457", "user_pseudo_id": "user2"},
        ]
        mock_bigquery_client._extract_purchase_events.return_value = mock_events
        mock_repository.replace_event_data.return_value = 2
        
        with patch("activities.process_events.get_tenant_bigquery_client", return_value=mock_bigquery_client):
            with patch("activities.process_events.create_repository", return_value=mock_repository):
                count = await process_events(
                    job_id=sample_job_id,
                    tenant_id=sample_tenant_id,
                    start_date="2024-01-01",
                    end_date="2024-01-31",
                    event_type="purchase"
                )
        
        assert count == 2


class TestProcessUsersActivity:
    """Tests for the process users activity."""
    
    @pytest.mark.asyncio
    async def test_process_users_with_no_client_returns_zero(
        self, sample_job_id, sample_tenant_id
    ):
        """Test that missing SFTP client returns 0."""
        from activities.process_users import process_users
        
        with patch("activities.process_users.get_tenant_sftp_client", return_value=None):
            count = await process_users(
                job_id=sample_job_id,
                tenant_id=sample_tenant_id
            )
        
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_process_users_with_empty_data_returns_zero(
        self, sample_job_id, sample_tenant_id, mock_sftp_client, mock_repository
    ):
        """Test that empty user data returns 0."""
        from activities.process_users import process_users
        
        mock_sftp_client._get_users_data_sync.return_value = pd.DataFrame()
        
        with patch("activities.process_users.get_tenant_sftp_client", return_value=mock_sftp_client):
            with patch("activities.process_users.create_repository", return_value=mock_repository):
                count = await process_users(
                    job_id=sample_job_id,
                    tenant_id=sample_tenant_id
                )
        
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_process_users_with_data_returns_count(
        self, sample_job_id, sample_tenant_id, mock_sftp_client, mock_repository
    ):
        """Test that user data is processed and count returned."""
        from activities.process_users import process_users
        
        # Mock users data
        mock_users = pd.DataFrame({
            "user_id": ["user1", "user2"],
            "email": ["user1@test.com", "user2@test.com"]
        })
        mock_sftp_client._get_users_data_sync.return_value = mock_users
        mock_repository.upsert_users.return_value = 2
        
        with patch("activities.process_users.get_tenant_sftp_client", return_value=mock_sftp_client):
            with patch("activities.process_users.create_repository", return_value=mock_repository):
                count = await process_users(
                    job_id=sample_job_id,
                    tenant_id=sample_tenant_id
                )
        
        assert count == 2


class TestProcessLocationsActivity:
    """Tests for the process locations activity."""
    
    @pytest.mark.asyncio
    async def test_process_locations_with_no_client_returns_zero(
        self, sample_job_id, sample_tenant_id
    ):
        """Test that missing SFTP client returns 0."""
        from activities.process_locations import process_locations
        
        with patch("activities.process_locations.get_tenant_sftp_client", return_value=None):
            count = await process_locations(
                job_id=sample_job_id,
                tenant_id=sample_tenant_id
            )
        
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_process_locations_with_data_returns_count(
        self, sample_job_id, sample_tenant_id, mock_sftp_client, mock_repository
    ):
        """Test that locations data is processed and count returned."""
        from activities.process_locations import process_locations
        
        # Mock locations data
        mock_locations = pd.DataFrame({
            "warehouse_id": ["wh1", "wh2"],
            "warehouse_name": ["Warehouse 1", "Warehouse 2"]
        })
        mock_sftp_client._get_locations_data_sync.return_value = mock_locations
        mock_repository.upsert_locations.return_value = 2
        
        with patch("activities.process_locations.get_tenant_sftp_client", return_value=mock_sftp_client):
            with patch("activities.process_locations.create_repository", return_value=mock_repository):
                count = await process_locations(
                    job_id=sample_job_id,
                    tenant_id=sample_tenant_id
                )
        
        assert count == 2


class TestJobManagementActivities:
    """Tests for job management activities."""
    
    @pytest.mark.asyncio
    async def test_update_job_status_success(self, sample_job_id, mock_repository):
        """Test successful job status update."""
        from activities.job_management import update_job_status
        
        mock_repository.update_job_status.return_value = True
        
        with patch("activities.job_management.create_repository", return_value=mock_repository):
            result = await update_job_status(
                job_id=sample_job_id,
                status="completed"
            )
        
        assert result is True
        mock_repository.update_job_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_job_success(self, sample_job_data, mock_repository):
        """Test successful job creation."""
        from activities.job_management import create_job
        
        mock_repository.create_processing_job.return_value = sample_job_data
        
        with patch("activities.job_management.create_repository", return_value=mock_repository):
            result = await create_job(sample_job_data)
        
        assert result == sample_job_data
        mock_repository.create_processing_job.assert_called_once()

