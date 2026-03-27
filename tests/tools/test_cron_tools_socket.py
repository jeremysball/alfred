"""Tests for cron tools using SocketClient.

Tests that the cron tools properly use SocketClient instead of CronScheduler.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from alfred.cron.socket_protocol import (
    ApproveJobResponse,
    QueryJobsResponse,
    RejectJobResponse,
    SubmitJobResponse,
)
from alfred.tools.approve_job import ApproveJobTool
from alfred.tools.list_jobs import ListJobsTool
from alfred.tools.reject_job import RejectJobTool
from alfred.tools.schedule_job import ScheduleJobTool


class TestListJobsTool:
    """Test ListJobsTool with SocketClient."""

    @pytest.fixture
    def mock_socket_client(self):
        """Create a mock SocketClient."""
        client = MagicMock()
        client.query_jobs = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_list_jobs_uses_socket_client(self, mock_socket_client):
        """Test that ListJobsTool uses socket client to query jobs."""
        # Setup mock response
        mock_socket_client.query_jobs.return_value = QueryJobsResponse(
            request_id="test-123",
            jobs=[
                {
                    "job_id": "job-1",
                    "name": "Test Job",
                    "expression": "0 9 * * *",
                    "status": "active",
                    "created_at": datetime.now().isoformat(),
                }
            ],
            recent_failures=[],
        )

        tool = ListJobsTool(socket_client=mock_socket_client)
        result = []
        async for chunk in tool.execute_stream(status_filter="all"):
            result.append(chunk)

        # Verify socket client was called
        mock_socket_client.query_jobs.assert_called_once()

        # Verify output contains job info
        output = "".join(result)
        assert "Test Job" in output
        assert "active" in output

    @pytest.mark.asyncio
    async def test_list_jobs_handles_none_response_with_fallback(self, mock_socket_client, tmp_path):
        """Test that ListJobsTool falls back to store when socket returns None."""
        mock_socket_client.query_jobs.return_value = None

        tool = ListJobsTool(socket_client=mock_socket_client, data_dir=tmp_path)
        result = []
        async for chunk in tool.execute_stream(status_filter="all"):
            result.append(chunk)

        output = "".join(result)
        # With no jobs in store, should show "no jobs" message
        assert "don't have any jobs" in output or "No jobs" in output

    @pytest.mark.asyncio
    async def test_list_jobs_filters_by_status(self, mock_socket_client):
        """Test that ListJobsTool filters jobs by status."""
        mock_socket_client.query_jobs.return_value = QueryJobsResponse(
            request_id="test-123",
            jobs=[
                {
                    "job_id": "job-1",
                    "name": "Active Job",
                    "expression": "0 9 * * *",
                    "status": "active",
                    "created_at": datetime.now().isoformat(),
                },
                {
                    "job_id": "job-2",
                    "name": "Pending Job",
                    "expression": "0 10 * * *",
                    "status": "pending",
                    "created_at": datetime.now().isoformat(),
                },
            ],
            recent_failures=[],
        )

        tool = ListJobsTool(socket_client=mock_socket_client)
        result = []
        async for chunk in tool.execute_stream(status_filter="pending"):
            result.append(chunk)

        output = "".join(result)
        assert "Pending Job" in output
        assert "Active Job" not in output


class TestApproveJobTool:
    """Test ApproveJobTool with SocketClient."""

    @pytest.fixture
    def mock_socket_client(self):
        """Create a mock SocketClient."""
        client = MagicMock()
        client.approve_job = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_approve_job_uses_socket_client(self, mock_socket_client):
        """Test that ApproveJobTool uses socket client."""
        mock_socket_client.approve_job.return_value = ApproveJobResponse(
            request_id="test-123",
            success=True,
            job_id="job-456",
            job_name="Test Job",
            message="Job approved successfully",
        )

        tool = ApproveJobTool(socket_client=mock_socket_client)
        result = []
        async for chunk in tool.execute_stream(job_identifier="Test Job"):
            result.append(chunk)

        # Verify socket client was called
        mock_socket_client.approve_job.assert_called_once_with("Test Job")

        # Verify output
        output = "".join(result)
        assert "approved" in output.lower()

    @pytest.mark.asyncio
    async def test_approve_job_handles_failure(self, mock_socket_client):
        """Test that ApproveJobTool handles failure response."""
        mock_socket_client.approve_job.return_value = ApproveJobResponse(
            request_id="test-123",
            success=False,
            job_id="",
            job_name="",
            message="Job not found",
        )

        tool = ApproveJobTool(socket_client=mock_socket_client)
        result = []
        async for chunk in tool.execute_stream(job_identifier="Unknown Job"):
            result.append(chunk)

        output = "".join(result)
        assert "Error" in output
        assert "Job not found" in output

    @pytest.mark.asyncio
    async def test_approve_job_handles_none_response(self, mock_socket_client):
        """Test that ApproveJobTool handles None response."""
        mock_socket_client.approve_job.return_value = None

        tool = ApproveJobTool(socket_client=mock_socket_client)
        result = []
        async for chunk in tool.execute_stream(job_identifier="Test Job"):
            result.append(chunk)

        output = "".join(result)
        assert "Error" in output
        assert "daemon may not be running" in output


class TestRejectJobTool:
    """Test RejectJobTool with SocketClient."""

    @pytest.fixture
    def mock_socket_client(self):
        """Create a mock SocketClient."""
        client = MagicMock()
        client.reject_job = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_reject_job_uses_socket_client(self, mock_socket_client):
        """Test that RejectJobTool uses socket client."""
        mock_socket_client.reject_job.return_value = RejectJobResponse(
            request_id="test-123",
            success=True,
            job_id="job-456",
            job_name="Test Job",
            message="Job deleted",
        )

        tool = RejectJobTool(socket_client=mock_socket_client)
        result = []
        async for chunk in tool.execute_stream(job_identifier="Test Job"):
            result.append(chunk)

        # Verify socket client was called
        mock_socket_client.reject_job.assert_called_once_with("Test Job")

        # Verify output
        output = "".join(result)
        assert "deleted" in output.lower() or "removed" in output.lower()


class TestScheduleJobTool:
    """Test ScheduleJobTool with SocketClient."""

    @pytest.fixture
    def mock_socket_client(self):
        """Create a mock SocketClient."""
        client = MagicMock()
        client.submit_job = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_schedule_job_uses_socket_client(self, mock_socket_client):
        """Test that ScheduleJobTool uses socket client."""
        mock_socket_client.submit_job.return_value = SubmitJobResponse(
            request_id="test-123",
            success=True,
            job_id="job-789",
            message="Job submitted successfully",
        )

        tool = ScheduleJobTool(socket_client=mock_socket_client)
        result = []
        async for chunk in tool.execute_stream(
            name="Daily Report",
            description="Send daily report",
            cron_expression="0 9 * * *",
        ):
            result.append(chunk)

        # Verify socket client was called
        mock_socket_client.submit_job.assert_called_once()
        call_args = mock_socket_client.submit_job.call_args
        assert call_args.kwargs["name"] == "Daily Report"
        assert call_args.kwargs["expression"] == "0 9 * * *"

        # Verify output
        output = "".join(result)
        assert "submitted" in output.lower()

    @pytest.mark.asyncio
    async def test_schedule_job_validates_cron_expression(self, mock_socket_client):
        """Test that ScheduleJobTool validates cron expression."""
        tool = ScheduleJobTool(socket_client=mock_socket_client)
        result = []
        async for chunk in tool.execute_stream(
            name="Invalid Job",
            description="Test",
            cron_expression="invalid",
        ):
            result.append(chunk)

        # Verify socket client was NOT called (validation failed first)
        mock_socket_client.submit_job.assert_not_called()

        # Verify error message
        output = "".join(result)
        assert "Error" in output
        assert "Invalid cron expression" in output

    @pytest.mark.asyncio
    async def test_schedule_job_handles_failure(self, mock_socket_client):
        """Test that ScheduleJobTool handles failure response."""
        mock_socket_client.submit_job.return_value = SubmitJobResponse(
            request_id="test-123",
            success=False,
            job_id="",
            message="Job with this name already exists",
        )

        tool = ScheduleJobTool(socket_client=mock_socket_client)
        result = []
        async for chunk in tool.execute_stream(
            name="Existing Job",
            description="Test",
            cron_expression="0 9 * * *",
        ):
            result.append(chunk)

        output = "".join(result)
        assert "Error" in output
