"""Behavioral tests for cron socket API.

These tests verify the complete round-trip:
Tool -> SocketClient -> SocketServer -> Scheduler -> Response

This is a true integration test that verifies behavior, not implementation.
"""

import asyncio

import pytest

from alfred.cron.scheduler import CronScheduler
from alfred.cron.socket_client import SocketClient
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
from alfred.cron.store import CronStore


class TestSocketAPIRoundTrip:
    """Test complete socket API round-trip with real components."""

    @pytest.fixture
    async def socket_system(self, tmp_path):
        """Create a complete socket-connected system.
        
        Returns:
            Dict with scheduler, server, client, and cleanup function
        """
        # Create temp directory for socket and data
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create scheduler with real store
        store = CronStore(data_dir=data_dir)
        scheduler = CronScheduler(store=store, data_dir=data_dir)

        # Create socket server with real handlers
        async def handle_query_jobs(request: QueryJobsRequest) -> QueryJobsResponse:
            """Handle job query - returns actual jobs from scheduler."""
            jobs = await scheduler._store.load_jobs()
            job_dicts = []
            for job in jobs:
                job_dicts.append({
                    "job_id": job.job_id,
                    "name": job.name,
                    "expression": job.expression,
                    "status": job.status,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                })
            return QueryJobsResponse(
                request_id=request.request_id,
                jobs=job_dicts,
                recent_failures=[],
            )

        async def handle_submit_job(request: SubmitJobRequest) -> SubmitJobResponse:
            """Handle job submission - creates actual job in scheduler."""
            try:
                job_id = await scheduler.submit_user_job(
                    name=request.name,
                    expression=request.expression,
                    code=request.code,
                )
                return SubmitJobResponse(
                    request_id=request.request_id,
                    success=True,
                    job_id=job_id,
                    message=f"Job '{request.name}' submitted successfully",
                )
            except Exception as e:
                return SubmitJobResponse(
                    request_id=request.request_id,
                    success=False,
                    job_id="",
                    message=str(e),
                )

        async def handle_approve_job(request: ApproveJobRequest) -> ApproveJobResponse:
            """Handle job approval - approves actual job in scheduler."""
            # Find job by ID or name
            jobs = await scheduler._store.load_jobs()
            job_id = None
            job_name = None

            for job in jobs:
                if job.job_id == request.job_identifier:
                    job_id = job.job_id
                    job_name = job.name
                    break
                if job.name.lower() == request.job_identifier.lower():
                    job_id = job.job_id
                    job_name = job.name
                    break

            if not job_id:
                return ApproveJobResponse(
                    request_id=request.request_id,
                    success=False,
                    job_id="",
                    job_name="",
                    message=f"Job not found: {request.job_identifier}",
                )

            result = await scheduler.approve_job(job_id, approved_by="user")
            return ApproveJobResponse(
                request_id=request.request_id,
                success=result["success"],
                job_id=job_id,
                job_name=job_name or "",
                message=result["message"],
            )

        async def handle_reject_job(request: RejectJobRequest) -> RejectJobResponse:
            """Handle job rejection - deletes actual job from scheduler."""
            jobs = await scheduler._store.load_jobs()
            job_id = None
            job_name = None

            for job in jobs:
                if job.job_id == request.job_identifier:
                    job_id = job.job_id
                    job_name = job.name
                    break
                if job.name.lower() == request.job_identifier.lower():
                    job_id = job.job_id
                    job_name = job.name
                    break

            if not job_id:
                return RejectJobResponse(
                    request_id=request.request_id,
                    success=False,
                    job_id="",
                    job_name="",
                    message=f"Job not found: {request.job_identifier}",
                )

            await scheduler._store.delete_job(job_id)
            return RejectJobResponse(
                request_id=request.request_id,
                success=True,
                job_id=job_id,
                job_name=job_name or "",
                message=f"Job '{job_name}' deleted",
            )

        server = SocketServer(
            on_query_jobs=handle_query_jobs,
            on_submit_job=handle_submit_job,
            on_approve_job=handle_approve_job,
            on_reject_job=handle_reject_job,
        )

        # Override socket path to use temp directory
        server.socket_path = tmp_path / "test.sock"

        # Start server
        await server.start()

        # Create client pointing to same socket
        client = SocketClient()
        client.socket_path = tmp_path / "test.sock"
        await client.start()

        # Wait for connection to establish
        await asyncio.sleep(0.1)

        yield {
            "scheduler": scheduler,
            "server": server,
            "client": client,
            "data_dir": data_dir,
        }

        # Cleanup
        await client.stop()
        await server.stop()

    @pytest.mark.asyncio
    async def test_submit_job_creates_actual_job(self, socket_system):
        """Behavior: Submitting a job via socket API creates an actual job in the store."""
        client = socket_system["client"]
        scheduler = socket_system["scheduler"]

        # Verify no jobs initially
        jobs = await scheduler._store.load_jobs()
        assert len(jobs) == 0

        # Submit job via socket API
        response = await client.submit_job(
            name="Test Job",
            expression="0 9 * * *",
            code="async def run(): pass",
        )

        # Verify response
        assert response is not None
        assert response.success is True
        assert response.job_id != ""

        # Verify job was actually created in store
        jobs = await scheduler._store.load_jobs()
        assert len(jobs) == 1
        assert jobs[0].name == "Test Job"
        assert jobs[0].status == "pending"

    @pytest.mark.asyncio
    async def test_query_jobs_returns_actual_jobs(self, socket_system):
        """Behavior: Querying jobs returns actual jobs from the store."""
        client = socket_system["client"]
        scheduler = socket_system["scheduler"]

        # Create jobs directly in scheduler
        await scheduler.submit_user_job(
            name="Job 1",
            expression="0 9 * * *",
            code="async def run(): pass",
        )
        await scheduler.submit_user_job(
            name="Job 2",
            expression="0 10 * * *",
            code="async def run(): pass",
        )

        # Query via socket API
        response = await client.query_jobs()

        # Verify response contains actual jobs
        assert response is not None
        assert len(response.jobs) == 2
        job_names = {j["name"] for j in response.jobs}
        assert "Job 1" in job_names
        assert "Job 2" in job_names

    @pytest.mark.asyncio
    async def test_approve_job_activates_actual_job(self, socket_system):
        """Behavior: Approving a job via socket API activates the actual job."""
        client = socket_system["client"]
        scheduler = socket_system["scheduler"]

        # Create pending job
        job_id = await scheduler.submit_user_job(
            name="Job To Approve",
            expression="0 9 * * *",
            code="async def run(): pass",
        )

        # Verify job is pending
        jobs = await scheduler._store.load_jobs()
        assert jobs[0].status == "pending"

        # Approve via socket API
        response = await client.approve_job("Job To Approve")

        # Verify response
        assert response is not None
        assert response.success is True

        # Verify job is now active in store
        jobs = await scheduler._store.load_jobs()
        assert jobs[0].status == "active"

    @pytest.mark.asyncio
    async def test_reject_job_deletes_actual_job(self, socket_system):
        """Behavior: Rejecting a job via socket API deletes the actual job."""
        client = socket_system["client"]
        scheduler = socket_system["scheduler"]

        # Create job
        await scheduler.submit_user_job(
            name="Job To Delete",
            expression="0 9 * * *",
            code="async def run(): pass",
        )

        # Verify job exists
        jobs = await scheduler._store.load_jobs()
        assert len(jobs) == 1

        # Reject via socket API
        response = await client.reject_job("Job To Delete")

        # Verify response
        assert response is not None
        assert response.success is True

        # Verify job was actually deleted
        jobs = await scheduler._store.load_jobs()
        assert len(jobs) == 0

    @pytest.mark.asyncio
    async def test_full_lifecycle_via_socket_api(self, socket_system):
        """Behavior: Complete job lifecycle works via socket API."""
        client = socket_system["client"]
        scheduler = socket_system["scheduler"]

        # 1. Submit job
        submit_response = await client.submit_job(
            name="Lifecycle Job",
            expression="0 9 * * *",
            code="async def run(): print('hello')",
        )
        assert submit_response.success is True
        job_id = submit_response.job_id

        # 2. Query and verify pending
        query_response = await client.query_jobs()
        assert len(query_response.jobs) == 1
        assert query_response.jobs[0]["status"] == "pending"

        # 3. Approve job
        approve_response = await client.approve_job(job_id)
        assert approve_response.success is True

        # 4. Query and verify active
        query_response = await client.query_jobs()
        assert query_response.jobs[0]["status"] == "active"

        # 5. Reject/delete job
        reject_response = await client.reject_job(job_id)
        assert reject_response.success is True

        # 6. Query and verify gone
        query_response = await client.query_jobs()
        assert len(query_response.jobs) == 0


class TestSocketAPIErrorHandling:
    """Test error handling behavior in socket API."""

    @pytest.fixture
    async def error_server(self, tmp_path):
        """Create a server with handlers that simulate errors."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        store = CronStore(data_dir=data_dir)
        scheduler = CronScheduler(store=store, data_dir=data_dir)

        async def handle_submit_error(request: SubmitJobRequest) -> SubmitJobResponse:
            """Simulate submission error."""
            return SubmitJobResponse(
                request_id=request.request_id,
                success=False,
                job_id="",
                message="Invalid cron expression format",
            )

        async def handle_approve_error(request: ApproveJobRequest) -> ApproveJobResponse:
            """Simulate approval error - job not found."""
            return ApproveJobResponse(
                request_id=request.request_id,
                success=False,
                job_id="",
                job_name="",
                message=f"Job not found: {request.job_identifier}",
            )

        server = SocketServer(
            on_submit_job=handle_submit_error,
            on_approve_job=handle_approve_error,
        )
        server.socket_path = tmp_path / "test.sock"
        await server.start()

        client = SocketClient()
        client.socket_path = tmp_path / "test.sock"
        await client.start()

        await asyncio.sleep(0.1)

        yield {"client": client}

        await client.stop()
        await server.stop()

    @pytest.mark.asyncio
    async def test_submit_job_error_response(self, error_server):
        """Behavior: Submit job error is properly communicated back to client."""
        client = error_server["client"]

        response = await client.submit_job(
            name="Bad Job",
            expression="invalid",
            code="pass",
        )

        assert response is not None
        assert response.success is False
        assert "Invalid cron expression" in response.message

    @pytest.mark.asyncio
    async def test_approve_job_not_found(self, error_server):
        """Behavior: Approving non-existent job returns proper error."""
        client = error_server["client"]

        response = await client.approve_job("Nonexistent Job")

        assert response is not None
        assert response.success is False
        assert "not found" in response.message.lower()


class TestSocketClientDisconnected:
    """Test behavior when socket is disconnected."""

    @pytest.mark.asyncio
    async def test_query_jobs_returns_none_when_disconnected(self, tmp_path):
        """Behavior: Client returns None when server is not running."""
        client = SocketClient()
        client.socket_path = tmp_path / "nonexistent.sock"
        await client.start()

        # Wait a bit for connection attempt
        await asyncio.sleep(0.2)

        # Try to query - should return None since not connected
        response = await client.query_jobs()

        # Client is not connected, so it returns None
        assert response is None

        await client.stop()
