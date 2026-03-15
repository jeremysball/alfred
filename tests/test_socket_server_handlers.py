"""Tests for SocketServer job management handlers."""

from unittest.mock import MagicMock

import pytest

from alfred.cron.socket_protocol import (
    ApproveJobRequest,
    ApproveJobResponse,
    QueryJobsRequest,
    QueryJobsResponse,
    RejectJobRequest,
    RejectJobResponse,
    SubmitJobRequest,
    SubmitJobResponse,
)
from alfred.cron.socket_server import SocketServer


class TestSocketServerJobHandlers:
    """Test job management handlers in SocketServer."""

    @pytest.fixture
    def server(self):
        """Create a SocketServer instance."""
        return SocketServer()

    @pytest.fixture
    async def mock_writer(self):
        """Create a mock StreamWriter."""
        writer = MagicMock()
        writer.write = MagicMock()

        # Create a coroutine for drain
        async def mock_drain():
            return None

        writer.drain = mock_drain
        return writer

    @pytest.mark.asyncio
    async def test_submit_job_request_dispatched(self, server, mock_writer):
        """Test that SubmitJobRequest is dispatched to callback."""
        callback_mock = MagicMock(
            return_value=SubmitJobResponse(
                request_id="test-123", success=True, job_id="job-456", message="Job submitted"
            )
        )
        server._on_submit_job = callback_mock

        request = SubmitJobRequest(
            request_id="test-123", name="Test Job", expression="0 9 * * *", code="print('hello')"
        )

        await server._dispatch_message(request, mock_writer)

        callback_mock.assert_called_once_with(request)
        mock_writer.write.assert_called_once()
        # Verify response was written
        written_data = mock_writer.write.call_args[0][0]
        assert b"submit_job_response" in written_data

    @pytest.mark.asyncio
    async def test_approve_job_request_dispatched(self, server, mock_writer):
        """Test that ApproveJobRequest is dispatched to callback."""
        callback_mock = MagicMock(
            return_value=ApproveJobResponse(
                request_id="test-123",
                success=True,
                job_id="job-456",
                job_name="Test Job",
                message="Job approved",
            )
        )
        server._on_approve_job = callback_mock

        request = ApproveJobRequest(request_id="test-123", job_identifier="Test Job")

        await server._dispatch_message(request, mock_writer)

        callback_mock.assert_called_once_with(request)
        mock_writer.write.assert_called_once()
        written_data = mock_writer.write.call_args[0][0]
        assert b"approve_job_response" in written_data

    @pytest.mark.asyncio
    async def test_reject_job_request_dispatched(self, server, mock_writer):
        """Test that RejectJobRequest is dispatched to callback."""
        callback_mock = MagicMock(
            return_value=RejectJobResponse(
                request_id="test-123",
                success=True,
                job_id="job-456",
                job_name="Test Job",
                message="Job rejected",
            )
        )
        server._on_reject_job = callback_mock

        request = RejectJobRequest(request_id="test-123", job_identifier="Test Job")

        await server._dispatch_message(request, mock_writer)

        callback_mock.assert_called_once_with(request)
        mock_writer.write.assert_called_once()
        written_data = mock_writer.write.call_args[0][0]
        assert b"reject_job_response" in written_data

    @pytest.mark.asyncio
    async def test_query_jobs_request_dispatched(self, server, mock_writer):
        """Test that QueryJobsRequest is dispatched to callback."""
        callback_mock = MagicMock(
            return_value=QueryJobsResponse(request_id="test-123", jobs=[], recent_failures=[])
        )
        server._on_query_jobs = callback_mock

        request = QueryJobsRequest(request_id="test-123")

        await server._dispatch_message(request, mock_writer)

        callback_mock.assert_called_once_with(request)
        mock_writer.write.assert_called_once()
        written_data = mock_writer.write.call_args[0][0]
        assert b"query_jobs_response" in written_data

    @pytest.mark.asyncio
    async def test_submit_job_no_callback(self, server, mock_writer):
        """Test that SubmitJobRequest is ignored when no callback registered."""
        server._on_submit_job = None

        request = SubmitJobRequest(
            request_id="test-123", name="Test Job", expression="0 9 * * *", code="print('hello')"
        )

        # Should not raise exception
        await server._dispatch_message(request, mock_writer)

        # Nothing should be written
        mock_writer.write.assert_not_called()

    @pytest.mark.asyncio
    async def test_approve_job_no_callback(self, server, mock_writer):
        """Test that ApproveJobRequest is ignored when no callback registered."""
        server._on_approve_job = None

        request = ApproveJobRequest(request_id="test-123", job_identifier="Test Job")

        # Should not raise exception
        await server._dispatch_message(request, mock_writer)

        mock_writer.write.assert_not_called()

    @pytest.mark.asyncio
    async def test_reject_job_no_callback(self, server, mock_writer):
        """Test that RejectJobRequest is ignored when no callback registered."""
        server._on_reject_job = None

        request = RejectJobRequest(request_id="test-123", job_identifier="Test Job")

        # Should not raise exception
        await server._dispatch_message(request, mock_writer)

        mock_writer.write.assert_not_called()
