"""Tests for ApproveJobTool."""

import pytest

from src.cron.scheduler import CronScheduler
from src.cron.store import CronStore
from src.tools.approve_job import ApproveJobParams, ApproveJobTool


@pytest.fixture
async def scheduler(tmp_path):
    """Create a scheduler with temporary data directory."""
    store = CronStore(data_dir=tmp_path)
    sched = CronScheduler(store=store, check_interval=60.0)
    return sched


@pytest.fixture
def approve_tool(scheduler):
    """Create an ApproveJobTool instance."""
    return ApproveJobTool(scheduler=scheduler)


class TestApproveJobTool:
    """Test ApproveJobTool functionality."""

    @pytest.mark.asyncio
    async def test_approve_by_name(self, scheduler, approve_tool):
        """Should approve job by name."""
        # Create pending job
        await scheduler.submit_user_job(
            name="Daily Report",
            expression="0 8 * * *",
            code="async def run(): pass"
        )
        
        result = []
        async for chunk in approve_tool.execute_stream(job_identifier="Daily Report"):
            result.append(chunk)
        
        output = "".join(result)
        assert "approved" in output.lower()
        assert "Daily Report" in output
        assert "active" in output.lower()

    @pytest.mark.asyncio
    async def test_approve_already_active(self, scheduler, approve_tool):
        """Should handle already active job."""
        # Create and approve job
        job_id = await scheduler.submit_user_job(
            name="Already Active",
            expression="0 8 * * *",
            code="async def run(): pass"
        )
        await scheduler.approve_job(job_id, "test")
        
        result = []
        async for chunk in approve_tool.execute_stream(job_identifier="Already Active"):
            result.append(chunk)
        
        output = "".join(result)
        assert "already active" in output.lower()

    @pytest.mark.asyncio
    async def test_approve_job_not_found(self, approve_tool):
        """Should handle job not found."""
        result = []
        async for chunk in approve_tool.execute_stream(job_identifier="Nonexistent Job"):
            result.append(chunk)
        
        output = "".join(result)
        assert "Couldn't find" in output

    @pytest.mark.asyncio
    async def test_find_job_by_id(self, scheduler, approve_tool):
        """Should find and approve job by ID."""
        # Create pending job
        job_id = await scheduler.submit_user_job(
            name="By ID Test",
            expression="0 8 * * *",
            code="async def run(): pass"
        )
        
        result = []
        async for chunk in approve_tool.execute_stream(job_identifier=job_id):
            result.append(chunk)
        
        output = "".join(result)
        assert "approved" in output.lower()
        assert "By ID Test" in output

    @pytest.mark.asyncio
    async def test_find_job_by_partial_name(self, scheduler, approve_tool):
        """Should find job by partial name match."""
        # Create pending job
        await scheduler.submit_user_job(
            name="Daily Morning Report",
            expression="0 8 * * *",
            code="async def run(): pass"
        )
        
        result = []
        async for chunk in approve_tool.execute_stream(job_identifier="Morning"):
            result.append(chunk)
        
        output = "".join(result)
        assert "approved" in output.lower()
        assert "Daily Morning Report" in output


class TestApproveJobParams:
    """Test ApproveJobParams validation."""

    def test_valid_identifier(self):
        """Should accept valid identifier."""
        params = ApproveJobParams(job_identifier="Daily Report")
        assert params.job_identifier == "Daily Report"

    def test_empty_identifier(self):
        """Should reject empty identifier."""
        with pytest.raises(ValueError):
            ApproveJobParams(job_identifier="")

    def test_whitespace_identifier(self):
        """Should reject whitespace-only identifier."""
        # After stripping, becomes empty, which fails min_length
        with pytest.raises(ValueError):
            ApproveJobParams(job_identifier="   ")

    def test_strips_whitespace(self):
        """Should strip whitespace from identifier."""
        params = ApproveJobParams(job_identifier="  Daily Report  ")
        assert params.job_identifier == "Daily Report"
