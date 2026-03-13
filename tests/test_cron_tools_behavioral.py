"""Behavioral tests for cron tools with real socket communication.

Verifies that tools work end-to-end with actual socket communication:
User Input -> Tool -> SocketClient -> SocketServer -> Scheduler -> Store
"""

import asyncio

import pytest

from alfred.cron.scheduler import CronScheduler
from alfred.cron.socket_client import SocketClient
from alfred.cron.socket_server import SocketServer
from alfred.cron.store import CronStore
from alfred.tools.approve_job import ApproveJobTool
from alfred.tools.list_jobs import ListJobsTool
from alfred.tools.reject_job import RejectJobTool
from alfred.tools.schedule_job import ScheduleJobTool


class TestCronToolsEndToEnd:
    """Test cron tools with real socket communication."""

    @pytest.fixture
    async def tools_system(self, tmp_path):
        """Create a complete system with tools connected via socket.

        Returns:
            Dict with tools, scheduler, and cleanup function
        """
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create scheduler with real store
        store = CronStore(data_dir=data_dir)
        scheduler = CronScheduler(store=store, data_dir=data_dir)

        # Create socket server with real handlers that use scheduler
        async def handle_query_jobs(request):
            from alfred.cron.socket_protocol import QueryJobsResponse
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

        async def handle_submit_job(request):
            from alfred.cron.socket_protocol import SubmitJobResponse
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

        async def handle_approve_job(request):
            from alfred.cron.socket_protocol import ApproveJobResponse
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

        async def handle_reject_job(request):
            from alfred.cron.socket_protocol import RejectJobResponse
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
        server.socket_path = tmp_path / "test.sock"
        await server.start()

        # Create socket client
        client = SocketClient()
        client.socket_path = tmp_path / "test.sock"
        await client.start()

        # Wait for connection
        await asyncio.sleep(0.1)

        # Create tools with real socket client
        tools = {
            "list_jobs": ListJobsTool(socket_client=client),
            "schedule_job": ScheduleJobTool(socket_client=client),
            "approve_job": ApproveJobTool(socket_client=client),
            "reject_job": RejectJobTool(socket_client=client),
            "scheduler": scheduler,
        }

        yield tools

        # Cleanup
        await client.stop()
        await server.stop()

    @pytest.mark.asyncio
    async def test_schedule_job_creates_job_in_store(self, tools_system):
        """Behavior: schedule_job tool creates job in store via socket API."""
        scheduler = tools_system["scheduler"]
        schedule_tool = tools_system["schedule_job"]

        # Verify no jobs
        jobs = await scheduler._store.load_jobs()
        assert len(jobs) == 0

        # Schedule job via tool
        result = []
        async for chunk in schedule_tool.execute_stream(
            name="Daily Report",
            description="Send daily summary",
            cron_expression="0 9 * * *",
        ):
            result.append(chunk)

        output = "".join(result)

        # Verify tool output indicates success
        assert "submitted" in output.lower()

        # Verify job was actually created in store
        jobs = await scheduler._store.load_jobs()
        assert len(jobs) == 1
        assert jobs[0].name == "Daily Report"
        assert jobs[0].status == "pending"

    @pytest.mark.asyncio
    async def test_list_jobs_shows_created_jobs(self, tools_system):
        """Behavior: list_jobs tool shows jobs created via schedule_job."""
        schedule_tool = tools_system["schedule_job"]
        list_tool = tools_system["list_jobs"]

        # Create jobs
        async for _ in schedule_tool.execute_stream(
            name="Job A",
            description="First job",
            cron_expression="0 9 * * *",
        ):
            pass

        async for _ in schedule_tool.execute_stream(
            name="Job B",
            description="Second job",
            cron_expression="0 10 * * *",
        ):
            pass

        # List jobs
        result = []
        async for chunk in list_tool.execute_stream(status_filter="all"):
            result.append(chunk)

        output = "".join(result)

        # Verify both jobs appear in output
        assert "Job A" in output
        assert "Job B" in output
        assert "2 job" in output.lower()

    @pytest.mark.asyncio
    async def test_approve_job_activates_pending_job(self, tools_system):
        """Behavior: approve_job tool activates job via socket API."""
        scheduler = tools_system["scheduler"]
        schedule_tool = tools_system["schedule_job"]
        approve_tool = tools_system["approve_job"]

        # Create pending job
        async for _ in schedule_tool.execute_stream(
            name="Job To Approve",
            description="Test job",
            cron_expression="0 9 * * *",
        ):
            pass

        # Verify pending
        jobs = await scheduler._store.load_jobs()
        assert jobs[0].status == "pending"

        # Approve via tool
        result = []
        async for chunk in approve_tool.execute_stream(job_identifier="Job To Approve"):
            result.append(chunk)

        output = "".join(result)

        # Verify output indicates success
        assert "approved" in output.lower()

        # Verify job is active in store
        jobs = await scheduler._store.load_jobs()
        assert jobs[0].status == "active"

    @pytest.mark.asyncio
    async def test_reject_job_deletes_job(self, tools_system):
        """Behavior: reject_job tool deletes job via socket API."""
        scheduler = tools_system["scheduler"]
        schedule_tool = tools_system["schedule_job"]
        reject_tool = tools_system["reject_job"]

        # Create job
        async for _ in schedule_tool.execute_stream(
            name="Job To Delete",
            description="Test job",
            cron_expression="0 9 * * *",
        ):
            pass

        # Verify job exists
        jobs = await scheduler._store.load_jobs()
        assert len(jobs) == 1

        # Reject via tool
        result = []
        async for chunk in reject_tool.execute_stream(job_identifier="Job To Delete"):
            result.append(chunk)

        output = "".join(result)

        # Verify output indicates deletion
        assert "deleted" in output.lower() or "removed" in output.lower()

        # Verify job is gone from store
        jobs = await scheduler._store.load_jobs()
        assert len(jobs) == 0

    @pytest.mark.asyncio
    async def test_list_jobs_filters_by_status(self, tools_system):
        """Behavior: list_jobs filtering works via socket API."""
        schedule_tool = tools_system["schedule_job"]
        approve_tool = tools_system["approve_job"]
        list_tool = tools_system["list_jobs"]

        # Create pending job
        async for _ in schedule_tool.execute_stream(
            name="Pending Job",
            description="Test",
            cron_expression="0 9 * * *",
        ):
            pass

        # Create and approve another job
        async for _ in schedule_tool.execute_stream(
            name="Active Job",
            description="Test",
            cron_expression="0 10 * * *",
        ):
            pass

        async for _ in approve_tool.execute_stream(job_identifier="Active Job"):
            pass

        # List only pending
        result = []
        async for chunk in list_tool.execute_stream(status_filter="pending"):
            result.append(chunk)

        output = "".join(result)
        assert "Pending Job" in output
        assert "Active Job" not in output

        # List only active
        result = []
        async for chunk in list_tool.execute_stream(status_filter="active"):
            result.append(chunk)

        output = "".join(result)
        assert "Active Job" in output
        assert "Pending Job" not in output

    @pytest.mark.asyncio
    async def test_full_workflow_via_tools(self, tools_system):
        """Behavior: Complete workflow via tools with socket API."""
        scheduler = tools_system["scheduler"]
        schedule_tool = tools_system["schedule_job"]
        approve_tool = tools_system["approve_job"]
        list_tool = tools_system["list_jobs"]
        reject_tool = tools_system["reject_job"]

        # 1. Schedule job
        result = []
        async for chunk in schedule_tool.execute_stream(
            name="Workflow Job",
            description="Test workflow",
            cron_expression="0 9 * * *",
        ):
            result.append(chunk)
        assert "submitted" in "".join(result).lower()

        # 2. List pending
        result = []
        async for chunk in list_tool.execute_stream(status_filter="pending"):
            result.append(chunk)
        assert "Workflow Job" in "".join(result)

        # 3. Approve
        result = []
        async for chunk in approve_tool.execute_stream(job_identifier="Workflow Job"):
            result.append(chunk)
        assert "approved" in "".join(result).lower()

        # 4. List active
        result = []
        async for chunk in list_tool.execute_stream(status_filter="active"):
            result.append(chunk)
        assert "Workflow Job" in "".join(result)

        # 5. Reject (delete)
        result = []
        async for chunk in reject_tool.execute_stream(job_identifier="Workflow Job"):
            result.append(chunk)
        assert "deleted" in "".join(result).lower() or "removed" in "".join(result).lower()

        # 6. Verify gone
        jobs = await scheduler._store.load_jobs()
        assert len(jobs) == 0

    @pytest.mark.asyncio
    async def test_schedule_job_rejects_invalid_cron(self, tools_system):
        """Behavior: schedule_job validates cron before submitting."""
        scheduler = tools_system["scheduler"]
        schedule_tool = tools_system["schedule_job"]

        # Try to schedule with invalid cron
        result = []
        async for chunk in schedule_tool.execute_stream(
            name="Bad Job",
            description="Test",
            cron_expression="not-a-valid-cron",
        ):
            result.append(chunk)

        output = "".join(result)

        # Verify error message
        assert "Error" in output
        assert "Invalid cron expression" in output

        # Verify no job was created
        jobs = await scheduler._store.load_jobs()
        assert len(jobs) == 0

    @pytest.mark.asyncio
    async def test_approve_job_not_found(self, tools_system):
        """Behavior: approve_job handles non-existent job gracefully."""
        approve_tool = tools_system["approve_job"]

        result = []
        async for chunk in approve_tool.execute_stream(job_identifier="Nonexistent"):
            result.append(chunk)

        output = "".join(result)

        # Verify error handling
        assert "Error" in output
