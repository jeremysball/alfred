"""Integration tests for ScheduleJobTool.

Tests with real CronScheduler and temp storage.
"""

import asyncio
from pathlib import Path

import pytest

from src.cron.scheduler import CronScheduler
from src.cron.store import CronStore
from src.tools.schedule_job import ScheduleJobParams, ScheduleJobTool


@pytest.fixture
async def temp_scheduler(tmp_path: Path):
    """Create scheduler with temp storage."""
    store = CronStore(data_dir=tmp_path / "data")
    scheduler = CronScheduler(store=store, check_interval=0.1)
    yield scheduler
    await scheduler.stop()


@pytest.fixture
def tool(temp_scheduler):
    """Create ScheduleJobTool with real scheduler."""
    return ScheduleJobTool(scheduler=temp_scheduler)


class TestScheduleJobToolIntegration:
    """Integration tests with real dependencies."""

    async def test_job_persisted_to_store(self, tool, temp_scheduler, tmp_path):
        """Created job is saved to JSONL file."""
        params = ScheduleJobParams(
            name="Persisted Job",
            description="Should be saved",
            cron_expression="0 10 * * *",
        )

        await tool.execute(params)

        # Verify job was saved
        jobs = await temp_scheduler._store.load_jobs()
        assert len(jobs) == 1
        assert jobs[0].name == "Persisted Job"
        assert jobs[0].status == "pending"

    async def test_multiple_jobs_persisted(self, tool, temp_scheduler):
        """Multiple jobs are all saved."""
        for i in range(3):
            params = ScheduleJobParams(
                name=f"Job {i}",
                description=f"Description {i}",
                cron_expression=f"{i} * * * *",
            )
            await tool.execute(params)

        jobs = await temp_scheduler._store.load_jobs()
        assert len(jobs) == 3

    async def test_job_pending_until_approved(self, tool, temp_scheduler):
        """Job stays pending, doesn't execute until approved."""
        params = ScheduleJobParams(
            name="Pending Job",
            description="Wait for approval",
            cron_expression="* * * * *",
        )

        result = await tool.execute(params)
        job_id = extract_job_id(result.output)

        # Start scheduler - job should not run (pending)
        await temp_scheduler.start()
        await asyncio.sleep(0.15)

        # Check no execution history
        history = await temp_scheduler._store.get_job_history(job_id)
        assert len(history) == 0

        # Approve job
        await temp_scheduler.approve_job(job_id, approved_by="test")

        # Wait for execution
        await asyncio.sleep(0.15)

        # Now it should have executed
        history = await temp_scheduler._store.get_job_history(job_id)
        assert len(history) >= 1

        await temp_scheduler.stop()

    async def test_generated_code_is_valid_python(self, tool, temp_scheduler):
        """Auto-generated code compiles successfully."""
        params = ScheduleJobParams(
            name="Code Gen Test",
            description="Print hello world",
            cron_expression="0 * * * *",
        )

        await tool.execute(params)

        # Load job and try to compile code
        jobs = await temp_scheduler._store.load_jobs()
        job = jobs[0]

        # Should compile without error
        compile(job.code, "<string>", "exec")

    async def test_custom_code_preserved_exactly(self, tool, temp_scheduler):
        """User-provided code is saved exactly as-is."""
        custom_code = """
async def run():
    # My custom logic
    result = 2 + 2
    print(f"Result: {result}")
    return result
"""
        params = ScheduleJobParams(
            name="Custom Code Job",
            description="Use my code",
            cron_expression="*/10 * * * *",
            code=custom_code,
        )

        await tool.execute(params)

        jobs = await temp_scheduler._store.load_jobs()
        assert jobs[0].code == custom_code


def extract_job_id(output: str) -> str:
    """Extract job ID from tool output."""
    # Output format includes: "Job ID: <uuid>\nTo approve..."
    if "Job ID: " in output:
        # Get the line with Job ID
        for line in output.split("\n"):
            if "Job ID: " in line:
                # Extract just the UUID part
                job_id_part = line.split("Job ID: ")[-1].strip()
                # Return just the UUID (before any newlines or additional text)
                return job_id_part.split()[0] if job_id_part else ""
    return ""
