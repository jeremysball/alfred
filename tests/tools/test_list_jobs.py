"""Tests for ListJobsTool."""

import pytest

from src.cron.models import Job
from src.cron.scheduler import CronScheduler
from src.cron.store import CronStore
from src.tools.list_jobs import ListJobsParams, ListJobsTool


@pytest.fixture
async def scheduler(tmp_path):
    """Create a scheduler with temporary data directory."""
    store = CronStore(data_dir=tmp_path)
    sched = CronScheduler(store=store, check_interval=60.0)
    return sched


@pytest.fixture
def list_jobs_tool(scheduler):
    """Create a ListJobsTool instance."""
    return ListJobsTool(scheduler=scheduler)


class TestListJobsTool:
    """Test ListJobsTool functionality."""

    @pytest.mark.asyncio
    async def test_list_empty_jobs(self, list_jobs_tool):
        """Should handle empty job list."""
        result = []
        async for chunk in list_jobs_tool.execute_stream(status_filter="all"):
            result.append(chunk)
        
        output = "".join(result)
        assert "don't have any jobs" in output.lower()

    @pytest.mark.asyncio
    async def test_list_pending_jobs(self, scheduler, list_jobs_tool):
        """Should list pending jobs."""
        # Create a pending job
        await scheduler.submit_user_job(
            name="Test Job",
            expression="0 8 * * *",
            code="async def run(): pass"
        )
        
        result = []
        async for chunk in list_jobs_tool.execute_stream(status_filter="pending"):
            result.append(chunk)
        
        output = "".join(result)
        assert "Test Job" in output
        assert "pending" in output.lower()

    @pytest.mark.asyncio
    async def test_list_all_jobs(self, scheduler, list_jobs_tool):
        """Should list all jobs regardless of status."""
        # Create pending job
        await scheduler.submit_user_job(
            name="Pending Job",
            expression="0 8 * * *",
            code="async def run(): pass"
        )
        
        # Create and approve an active job
        job_id = await scheduler.submit_user_job(
            name="Active Job",
            expression="0 9 * * *",
            code="async def run(): pass"
        )
        await scheduler.approve_job(job_id, "test")
        
        result = []
        async for chunk in list_jobs_tool.execute_stream(status_filter="all"):
            result.append(chunk)
        
        output = "".join(result)
        assert "Pending Job" in output
        assert "Active Job" in output
        assert "2 job" in output

    @pytest.mark.asyncio
    async def test_invalid_status_filter(self, list_jobs_tool):
        """Should handle invalid status filter."""
        result = []
        async for chunk in list_jobs_tool.execute_stream(status_filter="invalid"):
            result.append(chunk)
        
        output = "".join(result)
        assert "Error" in output
        assert "Invalid status filter" in output

    @pytest.mark.asyncio
    async def test_no_matching_jobs(self, scheduler, list_jobs_tool):
        """Should handle no matching jobs for filter."""
        # Create only pending jobs
        await scheduler.submit_user_job(
            name="Pending Job",
            expression="0 8 * * *",
            code="async def run(): pass"
        )
        
        # Ask for active jobs
        result = []
        async for chunk in list_jobs_tool.execute_stream(status_filter="active"):
            result.append(chunk)
        
        output = "".join(result)
        assert "No active jobs" in output


class TestListJobsParams:
    """Test ListJobsParams validation."""

    def test_default_status_filter(self):
        """Should default to 'all'."""
        params = ListJobsParams()
        assert params.status_filter == "all"

    def test_custom_status_filter(self):
        """Should accept custom filter."""
        params = ListJobsParams(status_filter="pending")
        assert params.status_filter == "pending"
