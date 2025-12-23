"""
Tests for HTTP trigger functions.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime


class TestGetDataAvailability:
    """Tests for the data availability endpoint."""
    
    @pytest.mark.asyncio
    async def test_missing_tenant_id_returns_400(self, mock_http_request):
        """Test that missing X-Tenant-Id header returns 400."""
        from function_app import get_data_availability
        
        request = mock_http_request(headers={})
        
        response = await get_data_availability(request)
        
        assert response.status_code == 400
        assert "X-Tenant-Id" in response.get_body().decode()
    
    @pytest.mark.asyncio
    async def test_valid_request_returns_data(self, mock_http_request, sample_tenant_id, mock_repository):
        """Test that valid request returns availability data."""
        from function_app import get_data_availability
        
        request = mock_http_request(
            headers={"X-Tenant-Id": sample_tenant_id}
        )
        
        with patch("function_app.create_repository", return_value=mock_repository):
            response = await get_data_availability(request)
        
        assert response.status_code == 200
        data = json.loads(response.get_body())
        assert "summary" in data


class TestListJobs:
    """Tests for the jobs list endpoint."""
    
    @pytest.mark.asyncio
    async def test_missing_tenant_id_returns_400(self, mock_http_request):
        """Test that missing X-Tenant-Id header returns 400."""
        from function_app import list_jobs
        
        request = mock_http_request(headers={})
        
        response = await list_jobs(request)
        
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_valid_request_returns_jobs(self, mock_http_request, sample_tenant_id, mock_repository):
        """Test that valid request returns job list."""
        from function_app import list_jobs
        
        request = mock_http_request(
            headers={"X-Tenant-Id": sample_tenant_id},
            params={"limit": "10", "offset": "0"}
        )
        
        with patch("function_app.create_repository", return_value=mock_repository):
            response = await list_jobs(request)
        
        assert response.status_code == 200
        data = json.loads(response.get_body())
        assert "jobs" in data
        assert "total" in data


class TestGetJobStatus:
    """Tests for the job status endpoint."""
    
    @pytest.mark.asyncio
    async def test_missing_tenant_id_returns_400(self, mock_http_request):
        """Test that missing X-Tenant-Id header returns 400."""
        from function_app import get_job_status
        
        request = mock_http_request(
            headers={},
            route_params={"job_id": "job_123"}
        )
        
        response = await get_job_status(request)
        
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_job_not_found_returns_404(self, mock_http_request, sample_tenant_id, mock_repository):
        """Test that non-existent job returns 404."""
        from function_app import get_job_status
        
        mock_repository.get_job_by_id.return_value = None
        
        request = mock_http_request(
            headers={"X-Tenant-Id": sample_tenant_id},
            route_params={"job_id": "job_nonexistent"}
        )
        
        with patch("function_app.create_repository", return_value=mock_repository):
            response = await get_job_status(request)
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_job_found_returns_details(self, mock_http_request, sample_tenant_id, mock_repository):
        """Test that existing job returns details."""
        from function_app import get_job_status
        
        mock_repository.get_job_by_id.return_value = {
            "job_id": "job_123",
            "tenant_id": sample_tenant_id,
            "status": "completed"
        }
        
        request = mock_http_request(
            headers={"X-Tenant-Id": sample_tenant_id},
            route_params={"job_id": "job_123"}
        )
        
        with patch("function_app.create_repository", return_value=mock_repository):
            response = await get_job_status(request)
        
        assert response.status_code == 200
        data = json.loads(response.get_body())
        assert data["job_id"] == "job_123"


class TestStartIngestionJob:
    """Tests for the ingestion job creation endpoint."""
    
    @pytest.mark.asyncio
    async def test_missing_tenant_id_returns_400(self, mock_http_request):
        """Test that missing X-Tenant-Id header returns 400."""
        from function_app import start_ingestion_job
        
        request = mock_http_request(headers={})
        mock_client = AsyncMock()
        
        response = await start_ingestion_job(request, mock_client)
        
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_valid_request_starts_orchestration(
        self, mock_http_request, sample_tenant_id, sample_ingestion_request, mock_repository
    ):
        """Test that valid request starts orchestration."""
        from function_app import start_ingestion_job
        
        request = mock_http_request(
            method="POST",
            headers={"X-Tenant-Id": sample_tenant_id},
            body=json.dumps(sample_ingestion_request).encode()
        )
        
        mock_client = AsyncMock()
        mock_client.start_new.return_value = "instance_123"
        
        with patch("function_app.create_repository", return_value=mock_repository):
            response = await start_ingestion_job(request, mock_client)
        
        assert response.status_code == 202
        data = json.loads(response.get_body())
        assert "job_id" in data
        assert data["status"] == "queued"
        
        # Verify orchestrator was started
        mock_client.start_new.assert_called_once()

