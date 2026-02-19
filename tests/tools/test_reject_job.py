"""Tests for RejectJobTool."""

import pytest

from src.cron.scheduler import CronScheduler
from src.cron.store import CronStore
from src.tools.reject_job import RejectJobParams, RejectJobTool


@pytest.fixture
async def scheduler(tmp_path):
    """Create a scheduler with temporary data directory."""
    store = CronStore(data_dir=tmp_path)
    sched = CronScheduler(store=store, check_interval=60.0)
    return sched


@pytest.fixture
def reject_tool(scheduler):
    """Create a RejectJobTool instance."""
    return RejectJobTool(scheduler=scheduler)


class TestRejectJobTool:
    """Test RejectJobTool functionality."""

    @pytest.mark.asyncio
    async def test_reject_by_name(self, scheduler, reject_tool):
        """Should reject/delete job by name."""
        # Create pending job
        await scheduler.submit_user_job(
            name="Delete Me",
            expression="0 8 * * *",
            code="async def run(): pass"
        )
        
        result = []
        async for chunk in reject_tool.execute_stream(job_identifier="Delete Me"):
            result.append(chunk)
        
        output = "".join(result)
        assert "Deleted" in output
        assert "Delete Me" in output

    @pytest.mark.asyncio
    async def test_job_actually_deleted(self, scheduler, reject_tool):
        """Should actually remove job from store."""
        # Create pending job
        await scheduler.submit_user_job(
            name="To Delete",
            expression="0 8 * * *",
            code="async def run(): pass"
        )
        
        # Delete it
        result = []
        async for chunk in reject_tool.execute_stream(job_identifier="To Delete"):
            result.append(chunk)
        
        # Verify it's gone
        jobs = await scheduler._store.load_jobs()
        assert len(jobs) == 0

    @pytest.mark.asyncio
    async def test_reject_job_not_found(self, reject_tool):
        """Should handle job not found."""
        result = []
        async for chunk in reject_tool.execute_stream(job_identifier="Nonexistent"):
            result.append(chunk)
        
        output = "".join(result)
        assert "Couldn't find" in output

    @pytest.mark.asyncio
    async def test_can_delete_active_job(self, scheduler, reject_tool):
        """Should be able to delete active jobs too."""
        # Create and approve job
        job_id = await scheduler.submit_user_job(
            name="Active to Delete",
            expression="0 8 * * *",
            code="async def run(): pass"
        )
        await scheduler.approve_job(job_id, "test")
        
        # Delete it
        result = []
        async for chunk in reject_tool.execute_stream(job_identifier="Active to Delete"):
            result.append(chunk)
        
        output = "".join(result)
        assert "Deleted" in output
        
        # Verify it's gone
        jobs = await scheduler._store.load_jobs()
        assert len(jobs) == 0


class TestRejectJobParams:
    """Test RejectJobParams validation."""

    def test_valid_identifier(self):
        """Should accept valid identifier."""
        params = RejectJobParams(job_identifier="Daily Report")
        assert params.job_identifier == "Daily Report"

    def test_empty_identifier(self):
        """Should reject empty identifier."""
        with pytest.raises(ValueError):
            RejectJobParams(job_identifier="")

    def test_whitespace_identifier(self):
        """Should reject whitespace-only identifier."""
        # After stripping, becomes empty, which fails min_length
        with pytest.raises(ValueError):
            RejectJobParams(job_identifier="   ")

    def test_strips_whitespace(self):
        """Should strip whitespace from identifier."""
        params = RejectJobParams(job_identifier="  Daily Report  ")
        assert params.job_identifier == "Daily Report"
