"""End-to-end test for ScheduleJobTool.

Full workflow: create job → approve → execute → verify.
"""

import asyncio
import tempfile
from pathlib import Path

import pytest

from src.cron.models import ExecutionStatus
from src.cron.scheduler import CronScheduler
from src.cron.store import CronStore
from src.tools.schedule_job import ScheduleJobParams, ScheduleJobTool


@pytest.mark.slow
@pytest.mark.integration
async def test_e2e_full_job_lifecycle():
    """End-to-end: Create, approve, execute, verify job actually runs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup real scheduler
        store = CronStore(data_dir=Path(tmpdir) / "data")
        scheduler = CronScheduler(store=store, check_interval=0.1)
        tool = ScheduleJobTool(scheduler=scheduler)

        try:
            # Step 1: Create job via tool
            params = ScheduleJobParams(
                name="E2E Test Job",
                description="Verify execution tracking",
                cron_expression="* * * * *",  # Every minute
            )

            result = await tool.execute(params)
            assert result.error is None
            assert "approval" in result.output.lower()

            # Extract job ID
            job_id = _extract_job_id(result.output)
            assert job_id, "Job ID not found in output"

            # Step 2: Verify job is pending
            jobs = await store.load_jobs()
            assert len(jobs) == 1
            assert jobs[0].job_id == job_id
            assert jobs[0].status == "pending"

            # Step 3: Approve job
            await scheduler.approve_job(job_id, approved_by="e2e-test")

            # Step 4: Start scheduler and wait for execution
            await scheduler.start()
            await asyncio.sleep(0.25)  # Wait for at least one execution

            # Step 5: Verify execution history
            history = await store.get_job_history(job_id)
            assert len(history) >= 1, "Job did not execute"

            # Check execution details
            execution = history[0]
            assert execution.job_id == job_id
            assert execution.status == ExecutionStatus.SUCCESS
            assert execution.duration_ms >= 0
            assert execution.started_at is not None
            assert execution.ended_at is not None

            print(f"✅ E2E Success: Job executed in {execution.duration_ms}ms")

        finally:
            await scheduler.stop()


@pytest.mark.slow
@pytest.mark.integration
async def test_e2e_custom_code_execution():
    """E2E with custom Python code that modifies state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = CronStore(data_dir=Path(tmpdir) / "data")
        scheduler = CronScheduler(store=store, check_interval=0.1)
        tool = ScheduleJobTool(scheduler=scheduler)

        # Create a state file path
        state_file = Path(tmpdir) / "job_state.txt"

        try:
            # Custom code that writes to file
            custom_code = f"""
async def run():
    # Write to state file to prove execution
    with open("{state_file}", "w") as f:
        f.write("executed")
    print("Job completed successfully")
"""

            params = ScheduleJobParams(
                name="State File Job",
                description="Write to file",
                cron_expression="* * * * *",
                code=custom_code,
            )

            result = await tool.execute(params)
            job_id = _extract_job_id(result.output)

            # Approve and run
            await scheduler.approve_job(job_id, approved_by="e2e-test")
            await scheduler.start()
            await asyncio.sleep(0.25)

            # Verify state file was created
            assert state_file.exists(), "State file not created - job did not run"
            content = state_file.read_text()
            assert content == "executed"

            print("✅ E2E Success: Custom code executed and modified state")

        finally:
            await scheduler.stop()


def _extract_job_id(output: str) -> str:
    """Extract job ID from tool output."""
    # Output format includes: "Job ID: <uuid>\nTo approve..."
    if "Job ID: " in output:
        for line in output.split("\n"):
            if "Job ID: " in line:
                job_id_part = line.split("Job ID: ")[-1].strip()
                return job_id_part.split()[0] if job_id_part else ""
    return ""
