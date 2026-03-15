"""Tests that jobs can import modules while blocking call checks remain.

The fix allows imports to work during job validation by using full builtins
in _validate_job_code(), while keeping the blocking call linter intact.
"""

from unittest.mock import AsyncMock, patch

import pytest

from alfred.cron.models import Job
from alfred.cron.scheduler import CronScheduler


class TestJobImportsWork:
    """Test that jobs can import modules without restrictions."""

    @pytest.mark.asyncio
    async def test_submit_job_allows_imports(self):
        """Submitting a job with imports should work."""
        scheduler = CronScheduler()

        code = """
import os
import sys
import json
from pathlib import Path
import subprocess
import requests
import time
import asyncio

async def run():
    print(f"Python version: {sys.version}")
    print(f"Current dir: {os.getcwd()}")
    # Use asyncio sleep instead of time.sleep to avoid blocking warning
    await asyncio.sleep(0.01)
"""
        with patch.object(scheduler, "_store") as mock_store:
            mock_store.save_job = AsyncMock()
            # Should NOT raise ImportError about __import__
            job_id = await scheduler.submit_user_job(
                name="test-imports", expression="* * * * *", code=code
            )
            assert job_id is not None

    @pytest.mark.asyncio
    async def test_approve_job_allows_imports(self):
        """Approving a job with imports should work."""
        scheduler = CronScheduler()

        code = """
import subprocess
import requests
import os

async def run():
    # Using asyncio subprocess avoids blocking warning
    proc = await asyncio.create_subprocess_exec(
        "echo", "hello",
        stdout=asyncio.subprocess.PIPE
    )
    await proc.communicate()
"""
        with patch.object(scheduler, "_store") as mock_store:
            mock_store.save_job = AsyncMock()
            mock_store.load_jobs = AsyncMock(
                return_value=[
                    Job(
                        job_id="test-job-123",
                        name="test",
                        expression="* * * * *",
                        code=code,
                        status="pending",
                    )
                ]
            )

            result = await scheduler.approve_job("test-job-123", "test-user")
            assert result["success"] is True


class TestBlockingCallsStillDetected:
    """Test that blocking call detection still works."""

    @pytest.mark.asyncio
    async def test_submit_job_blocks_time_sleep(self):
        """time.sleep() should still be flagged as blocking."""
        scheduler = CronScheduler()

        code = """
import time

async def run():
    time.sleep(1)
"""
        with patch.object(scheduler, "_store") as mock_store:
            mock_store.save_job = AsyncMock()

            with pytest.raises(ValueError) as exc_info:
                await scheduler.submit_user_job(
                    name="test-blocking", expression="* * * * *", code=code
                )

            assert "time.sleep" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_submit_job_blocks_subprocess_run(self):
        """subprocess.run() should still be flagged as blocking."""
        scheduler = CronScheduler()

        code = """
import subprocess

async def run():
    subprocess.run(["echo", "hello"])
"""
        with patch.object(scheduler, "_store") as mock_store:
            mock_store.save_job = AsyncMock()

            with pytest.raises(ValueError) as exc_info:
                await scheduler.submit_user_job(
                    name="test-blocking", expression="* * * * *", code=code
                )

            assert "subprocess.run" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_submit_job_blocks_file_open(self):
        """open() should still be flagged as blocking."""
        scheduler = CronScheduler()

        code = """
async def run():
    with open("/tmp/test.txt", "r") as f:
        data = f.read()
"""
        with patch.object(scheduler, "_store") as mock_store:
            mock_store.save_job = AsyncMock()

            with pytest.raises(ValueError) as exc_info:
                await scheduler.submit_user_job(
                    name="test-blocking", expression="* * * * *", code=code
                )

            assert "open" in str(exc_info.value)


class TestAsyncPatternsAllowed:
    """Test that proper async patterns pass the linter."""

    @pytest.mark.asyncio
    async def test_asyncio_subprocess_allowed(self):
        """asyncio.create_subprocess_exec should be allowed."""
        scheduler = CronScheduler()

        code = """
import asyncio

async def run():
    proc = await asyncio.create_subprocess_exec(
        "echo", "hello",
        stdout=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    print(stdout.decode())
"""
        with patch.object(scheduler, "_store") as mock_store:
            mock_store.save_job = AsyncMock()

            job_id = await scheduler.submit_user_job(
                name="test-async", expression="* * * * *", code=code
            )
            assert job_id is not None

    @pytest.mark.asyncio
    async def test_asyncio_sleep_allowed(self):
        """asyncio.sleep should be allowed."""
        scheduler = CronScheduler()

        code = """
import asyncio

async def run():
    print("Starting...")
    await asyncio.sleep(0.01)
    print("Done!")
"""
        with patch.object(scheduler, "_store") as mock_store:
            mock_store.save_job = AsyncMock()

            # This should succeed - asyncio.sleep is the proper async pattern
            job_id = await scheduler.submit_user_job(
                name="test-async", expression="* * * * *", code=code
            )
            assert job_id is not None
