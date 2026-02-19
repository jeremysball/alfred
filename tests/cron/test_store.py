"""Tests for cron job persistence (CronStore).

TDD approach: write tests first, then implement to make them pass.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from src.cron.models import ExecutionRecord, ExecutionStatus, Job
from src.cron.store import CronStore


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Create temporary data directory."""
    return tmp_path / "data"


@pytest.fixture
def store(temp_data_dir: Path) -> CronStore:
    """Create CronStore with temp directory."""
    return CronStore(data_dir=temp_data_dir)


class TestCronStoreInit:
    """Tests for CronStore initialization."""

    def test_creates_data_directory(self, temp_data_dir: Path):
        """Store creates data directory if it doesn't exist."""
        assert not temp_data_dir.exists()
        
        CronStore(data_dir=temp_data_dir)
        
        assert temp_data_dir.exists()
        assert temp_data_dir.is_dir()

    def test_uses_existing_directory(self, temp_data_dir: Path):
        """Store works with existing data directory."""
        temp_data_dir.mkdir(parents=True)
        
        store = CronStore(data_dir=temp_data_dir)
        
        # Path is set but file doesn't exist until first write
        assert store.jobs_path == temp_data_dir / "cron.jsonl"
        assert not store.jobs_path.exists()  # File created on first write


class TestSaveJob:
    """Tests for saving jobs to disk."""

    async def test_save_job_creates_file(self, store: CronStore, temp_data_dir: Path):
        """Saving first job creates cron.jsonl."""
        job = Job(
            job_id="test-1",
            name="Test Job",
            expression="* * * * *",
            code="async def run(): pass",
            status="active",
        )
        
        await store.save_job(job)
        
        assert store.jobs_path.exists()

    async def test_save_job_writes_json(self, store: CronStore):
        """Job is serialized as JSON."""
        job = Job(
            job_id="test-1",
            name="Test Job",
            expression="* * * * *",
            code="async def run(): pass",
            status="active",
            last_run=datetime(2026, 2, 18, 10, 0, 0, tzinfo=UTC),
        )
        
        await store.save_job(job)
        
        content = store.jobs_path.read_text()
        data = json.loads(content)
        
        assert data["job_id"] == "test-1"
        assert data["name"] == "Test Job"
        assert data["expression"] == "* * * * *"
        assert data["code"] == "async def run(): pass"
        assert data["status"] == "active"
        assert data["last_run"] == "2026-02-18T10:00:00+00:00"

    async def test_save_multiple_jobs_rewrites_file(self, store: CronStore):
        """Saving multiple jobs rewrites entire file."""
        job1 = Job(job_id="job-1", name="Job 1", expression="* * * * *", code="pass", status="active")
        job2 = Job(job_id="job-2", name="Job 2", expression="*/5 * * * *", code="pass", status="active")
        
        await store.save_job(job1)
        await store.save_job(job2)
        
        content = store.jobs_path.read_text()
        lines = content.strip().split("\n")
        
        assert len(lines) == 2
        assert json.loads(lines[0])["job_id"] == "job-1"
        assert json.loads(lines[1])["job_id"] == "job-2"

    async def test_save_updates_existing_job(self, store: CronStore):
        """Saving job with same ID updates existing."""
        job1 = Job(job_id="test-1", name="Original", expression="* * * * *", code="pass", status="active")
        job2 = Job(job_id="test-1", name="Updated", expression="*/5 * * * *", code="pass", status="paused")
        
        await store.save_job(job1)
        await store.save_job(job2)
        
        content = store.jobs_path.read_text()
        lines = content.strip().split("\n")
        
        assert len(lines) == 1
        assert json.loads(lines[0])["name"] == "Updated"
        assert json.loads(lines[0])["status"] == "paused"


class TestLoadJobs:
    """Tests for loading jobs from disk."""

    async def test_load_jobs_empty_file(self, store: CronStore):
        """Loading from non-existent file returns empty list."""
        jobs = await store.load_jobs()
        
        assert jobs == []

    async def test_load_jobs_single(self, store: CronStore):
        """Load single job from file."""
        job = Job(
            job_id="test-1",
            name="Test Job",
            expression="* * * * *",
            code="async def run(): pass",
            status="active",
            last_run=datetime(2026, 2, 18, 10, 0, 0, tzinfo=UTC),
        )
        await store.save_job(job)
        
        jobs = await store.load_jobs()
        
        assert len(jobs) == 1
        assert jobs[0].job_id == "test-1"
        assert jobs[0].name == "Test Job"
        assert jobs[0].code == "async def run(): pass"

    async def test_load_jobs_multiple(self, store: CronStore):
        """Load multiple jobs from file."""
        job1 = Job(job_id="job-1", name="Job 1", expression="* * * * *", code="pass", status="active")
        job2 = Job(job_id="job-2", name="Job 2", expression="*/5 * * * *", code="pass", status="active")
        await store.save_job(job1)
        await store.save_job(job2)
        
        jobs = await store.load_jobs()
        
        assert len(jobs) == 2
        assert {j.job_id for j in jobs} == {"job-1", "job-2"}

    async def test_load_jobs_skips_corrupt_lines(self, store: CronStore, caplog):
        """Skip corrupt JSON lines and log warning."""
        store.jobs_path.parent.mkdir(parents=True, exist_ok=True)
        store.jobs_path.write_text(
            '{"job_id": "valid", "name": "Valid", "expression": "* * * * *", "code": "pass", "status": "active"}\n'
            'invalid json here\n'
            '{"job_id": "also-valid", "name": "Also Valid", "expression": "*/5 * * * *", "code": "pass", "status": "active"}\n'
        )
        
        jobs = await store.load_jobs()
        
        assert len(jobs) == 2
        assert "valid" in [j.job_id for j in jobs]
        assert "also-valid" in [j.job_id for j in jobs]
        assert "Skipping corrupt line" in caplog.text


class TestDeleteJob:
    """Tests for deleting jobs."""

    async def test_delete_job_removes_from_file(self, store: CronStore):
        """Delete job removes it from cron.jsonl."""
        job1 = Job(job_id="job-1", name="Job 1", expression="* * * * *", code="pass", status="active")
        job2 = Job(job_id="job-2", name="Job 2", expression="*/5 * * * *", code="pass", status="active")
        await store.save_job(job1)
        await store.save_job(job2)
        
        await store.delete_job("job-1")
        
        jobs = await store.load_jobs()
        assert len(jobs) == 1
        assert jobs[0].job_id == "job-2"

    async def test_delete_nonexistent_job_silently_succeeds(self, store: CronStore):
        """Deleting non-existent job doesn't raise error."""
        await store.delete_job("does-not-exist")  # Should not raise


class TestRecordExecution:
    """Tests for recording execution history."""

    async def test_record_execution_creates_file(self, store: CronStore):
        """Recording first execution creates cron_history.jsonl."""
        record = ExecutionRecord(
            execution_id="exec-1",
            job_id="job-1",
            started_at=datetime(2026, 2, 18, 10, 0, 0, tzinfo=UTC),
            ended_at=datetime(2026, 2, 18, 10, 0, 2, tzinfo=UTC),
            status=ExecutionStatus.SUCCESS,
            duration_ms=2000,
        )
        
        await store.record_execution(record)
        
        assert store.history_path.exists()

    async def test_record_execution_appends(self, store: CronStore):
        """Execution records are appended to history file."""
        record1 = ExecutionRecord(
            execution_id="exec-1",
            job_id="job-1",
            started_at=datetime(2026, 2, 18, 10, 0, 0, tzinfo=UTC),
            ended_at=datetime(2026, 2, 18, 10, 0, 1, tzinfo=UTC),
            status=ExecutionStatus.SUCCESS,
            duration_ms=1000,
        )
        record2 = ExecutionRecord(
            execution_id="exec-2",
            job_id="job-1",
            started_at=datetime(2026, 2, 18, 10, 1, 0, tzinfo=UTC),
            ended_at=datetime(2026, 2, 18, 10, 1, 2, tzinfo=UTC),
            status=ExecutionStatus.FAILED,
            duration_ms=2000,
            error_message="Test error",
        )
        
        await store.record_execution(record1)
        await store.record_execution(record2)
        
        content = store.history_path.read_text()
        lines = content.strip().split("\n")
        
        assert len(lines) == 2
        assert json.loads(lines[0])["execution_id"] == "exec-1"
        assert json.loads(lines[1])["execution_id"] == "exec-2"

    async def test_record_execution_includes_error(self, store: CronStore):
        """Failed executions include error message."""
        record = ExecutionRecord(
            execution_id="exec-1",
            job_id="job-1",
            started_at=datetime(2026, 2, 18, 10, 0, 0, tzinfo=UTC),
            ended_at=datetime(2026, 2, 18, 10, 0, 1, tzinfo=UTC),
            status=ExecutionStatus.FAILED,
            duration_ms=1000,
            error_message="Something went wrong",
        )
        
        await store.record_execution(record)
        
        content = store.history_path.read_text()
        data = json.loads(content)
        
        assert data["status"] == "failed"
        assert data["error_message"] == "Something went wrong"


class TestGetJobHistory:
    """Tests for querying execution history."""

    async def test_get_history_for_job(self, store: CronStore):
        """Get execution history for specific job."""
        record1 = ExecutionRecord(
            execution_id="exec-1", job_id="job-1",
            started_at=datetime(2026, 2, 18, 10, 0, 0, tzinfo=UTC),
            ended_at=datetime(2026, 2, 18, 10, 0, 1, tzinfo=UTC),
            status=ExecutionStatus.SUCCESS, duration_ms=1000,
        )
        record2 = ExecutionRecord(
            execution_id="exec-2", job_id="job-2",
            started_at=datetime(2026, 2, 18, 10, 1, 0, tzinfo=UTC),
            ended_at=datetime(2026, 2, 18, 10, 1, 1, tzinfo=UTC),
            status=ExecutionStatus.SUCCESS, duration_ms=1000,
        )
        await store.record_execution(record1)
        await store.record_execution(record2)
        
        history = await store.get_job_history("job-1")
        
        assert len(history) == 1
        assert history[0].execution_id == "exec-1"

    async def test_get_history_empty(self, store: CronStore):
        """Get history for job with no executions."""
        history = await store.get_job_history("no-such-job")
        
        assert history == []

    async def test_get_history_limit(self, store: CronStore):
        """Limit number of history records returned."""
        for i in range(10):
            record = ExecutionRecord(
                execution_id=f"exec-{i}", job_id="job-1",
                started_at=datetime(2026, 2, 18, 10, i, 0, tzinfo=UTC),
                ended_at=datetime(2026, 2, 18, 10, i, 1, tzinfo=UTC),
                status=ExecutionStatus.SUCCESS, duration_ms=1000,
            )
            await store.record_execution(record)
        
        history = await store.get_job_history("job-1", limit=5)
        
        assert len(history) == 5


class TestAtomicWrites:
    """Tests for atomic write operations."""

    async def test_save_job_creates_temp_file_then_renames(self, store: CronStore, temp_data_dir: Path):
        """Job save uses atomic write (temp file + rename)."""
        job = Job(job_id="test-1", name="Test", expression="* * * * *", code="pass", status="active")
        
        await store.save_job(job)
        
        # Temp file should not exist after successful write
        temp_path = store.jobs_path.with_suffix(".tmp")
        assert not temp_path.exists()
        
        # Actual file should exist
        assert store.jobs_path.exists()