"""Tests for cron observability - StructuredLogger."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from src.cron.models import ExecutionRecord, ExecutionStatus
from src.cron.observability import StructuredLogger


class TestStructuredLogger:
    """Tests for StructuredLogger."""

    async def test_log_job_start(self, tmp_path: Path) -> None:
        """Test logging job start."""
        log_file = tmp_path / "cron_logs.jsonl"
        logger = StructuredLogger(log_file)

        await logger.log_job_start("job-123", "Test Job", "print('hello')")

        content = log_file.read_text()
        entry = json.loads(content.strip())

        assert entry["event"] == "job_start"
        assert entry["job_id"] == "job-123"
        assert entry["job_name"] == "Test Job"
        assert entry["code_snapshot"] == "print('hello')"
        assert entry["level"] == "INFO"

    async def test_log_job_end_success(self, tmp_path: Path) -> None:
        """Test logging successful job end."""
        log_file = tmp_path / "cron_logs.jsonl"
        logger = StructuredLogger(log_file)

        record = ExecutionRecord(
            execution_id="exec-1",
            job_id="job-123",
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            status=ExecutionStatus.SUCCESS,
            duration_ms=100,
        )

        await logger.log_job_end("job-123", "Test Job", record)

        content = log_file.read_text()
        entry = json.loads(content.strip())

        assert entry["event"] == "job_end"
        assert entry["job_id"] == "job-123"
        assert entry["status"] == "success"
        assert entry["level"] == "INFO"
        assert entry["duration_ms"] == 100

    async def test_log_job_end_failure(self, tmp_path: Path) -> None:
        """Test logging failed job end."""
        log_file = tmp_path / "cron_logs.jsonl"
        logger = StructuredLogger(log_file)

        record = ExecutionRecord(
            execution_id="exec-1",
            job_id="job-123",
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            status=ExecutionStatus.FAILED,
            duration_ms=50,
            error_message="Something went wrong",
        )

        await logger.log_job_end("job-123", "Test Job", record)

        content = log_file.read_text()
        entry = json.loads(content.strip())

        assert entry["event"] == "job_end"
        assert entry["status"] == "failed"
        assert entry["level"] == "ERROR"
        assert entry["error_message"] == "Something went wrong"

    async def test_log_scheduler_event(self, tmp_path: Path) -> None:
        """Test logging scheduler events."""
        log_file = tmp_path / "cron_logs.jsonl"
        logger = StructuredLogger(log_file)

        await logger.log_scheduler_event("scheduler_start", "Cron scheduler started")

        content = log_file.read_text()
        entry = json.loads(content.strip())

        assert entry["event"] == "scheduler_start"
        assert entry["message"] == "Cron scheduler started"
        assert entry["level"] == "INFO"

    async def test_log_warning(self, tmp_path: Path) -> None:
        """Test logging warnings."""
        log_file = tmp_path / "cron_logs.jsonl"
        logger = StructuredLogger(log_file)

        await logger.log_warning("job-123", "Job is slow")

        content = log_file.read_text()
        entry = json.loads(content.strip())

        assert entry["event"] == "warning"
        assert entry["job_id"] == "job-123"
        assert entry["message"] == "Job is slow"
        assert entry["level"] == "WARNING"

    async def test_concurrent_writes(self, tmp_path: Path) -> None:
        """Test concurrent writes are safe."""
        log_file = tmp_path / "cron_logs.jsonl"
        logger = StructuredLogger(log_file)

        async def write_log(i: int) -> None:
            await logger.log_job_start(f"job-{i}", f"Job {i}", None)

        await asyncio.gather(*[write_log(i) for i in range(10)])

        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 10

        job_ids = {json.loads(line)["job_id"] for line in lines}
        assert len(job_ids) == 10

    async def test_creates_parent_directory(self, tmp_path: Path) -> None:
        """Test that parent directories are created."""
        log_file = tmp_path / "nested" / "dir" / "cron_logs.jsonl"
        logger = StructuredLogger(log_file)

        await logger.log_job_start("job-1", "Test", None)

        assert log_file.exists()
