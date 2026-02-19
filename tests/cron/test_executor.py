"""Tests for cron job executor with resource limits."""

import asyncio
from datetime import UTC, datetime

import pytest

from src.cron.executor import ExecutionContext, ExecutionResult, JobExecutor
from src.cron.models import ExecutionRecord, ExecutionStatus, Job, ResourceLimits


class TestExecutionContext:
    """Test ExecutionContext safe operations."""

    def test_context_creation(self):
        """Should create context with job info."""
        context = ExecutionContext(
            job_id="test-1",
            job_name="Test Job",
            memory_store=None,
            notifier=None,
        )

        assert context.job_id == "test-1"
        assert context.job_name == "Test Job"

    async def test_notify_without_notifier(self):
        """Should silently succeed without notifier."""
        context = ExecutionContext(
            job_id="test-1",
            job_name="Test Job",
            notifier=None,
        )

        # Should not raise
        await context.notify("Hello")

    def test_store_get_returns_none(self):
        """Should return None for unimplemented store."""
        context = ExecutionContext(
            job_id="test-1",
            job_name="Test Job",
        )

        result = context.store_get("key")
        assert result is None

    def test_store_set_does_nothing(self):
        """Should silently succeed for unimplemented store."""
        context = ExecutionContext(
            job_id="test-1",
            job_name="Test Job",
        )

        # Should not raise
        context.store_set("key", "value")


class TestJobExecutorBasic:
    """Test basic JobExecutor functionality."""

    async def test_execute_successful_job(self):
        """Should execute job and return success."""
        async def handler():
            print("Hello, World!")

        job = Job(
            job_id="test-1",
            name="Test Job",
            expression="* * * * *",
            code="async def run(): print('Hello')",
        )
        limits = ResourceLimits()
        context = ExecutionContext(job_id="test-1", job_name="Test Job")

        executor = JobExecutor(job, handler, limits, context)
        result = await executor.execute()

        assert result.status == ExecutionStatus.SUCCESS
        assert result.stdout == "Hello, World!\n"
        assert result.stderr == ""
        assert result.duration_ms >= 0

    async def test_execute_with_stderr(self):
        """Should capture stderr output."""
        async def handler():
            import sys

            print("Error!", file=sys.stderr)

        job = Job(job_id="test-1", name="Test", expression="* * * * *", code="")
        limits = ResourceLimits()
        context = ExecutionContext(job_id="test-1", job_name="Test")

        executor = JobExecutor(job, handler, limits, context)
        result = await executor.execute()

        assert result.status == ExecutionStatus.SUCCESS
        assert "Error!" in result.stderr

    async def test_execute_failed_job(self):
        """Should handle job exceptions."""
        async def handler():
            raise ValueError("Something went wrong")

        job = Job(job_id="test-1", name="Test", expression="* * * * *", code="")
        limits = ResourceLimits()
        context = ExecutionContext(job_id="test-1", job_name="Test")

        executor = JobExecutor(job, handler, limits, context)
        result = await executor.execute()

        assert result.status == ExecutionStatus.FAILED
        assert "Something went wrong" in result.error_message
        assert result.duration_ms >= 0


class TestJobExecutorTimeout:
    """Test timeout enforcement."""

    async def test_job_times_out(self):
        """Should timeout if job exceeds limit."""
        async def slow_handler():
            await asyncio.sleep(10)  # Will be interrupted

        job = Job(job_id="test-1", name="Slow Job", expression="* * * * *", code="")
        limits = ResourceLimits(timeout_seconds=0.1)
        context = ExecutionContext(job_id="test-1", job_name="Slow Job")

        executor = JobExecutor(job, slow_handler, limits, context)
        result = await executor.execute()

        assert result.status == ExecutionStatus.TIMEOUT
        assert "exceeded timeout" in result.error_message
        assert result.duration_ms >= 100  # At least 100ms

    async def test_job_completes_before_timeout(self):
        """Should succeed if job completes within limit."""
        async def fast_handler():
            await asyncio.sleep(0.01)
            print("Done!")

        job = Job(job_id="test-1", name="Fast Job", expression="* * * * *", code="")
        limits = ResourceLimits(timeout_seconds=1)
        context = ExecutionContext(job_id="test-1", job_name="Fast Job")

        executor = JobExecutor(job, fast_handler, limits, context)
        result = await executor.execute()

        assert result.status == ExecutionStatus.SUCCESS
        assert "Done!" in result.stdout


class TestJobExecutorOutputLimits:
    """Test output capture and truncation."""

    async def test_output_truncation(self):
        """Should truncate output exceeding line limit."""
        async def verbose_handler():
            for i in range(100):
                print(f"Line {i}")

        job = Job(job_id="test-1", name="Verbose", expression="* * * * *", code="")
        limits = ResourceLimits(max_output_lines=10)
        context = ExecutionContext(job_id="test-1", job_name="Verbose")

        executor = JobExecutor(job, verbose_handler, limits, context)
        result = await executor.execute()

        assert result.status == ExecutionStatus.SUCCESS
        assert result.stdout_truncated is True
        assert "[... output truncated ...]" in result.stdout
        assert result.stdout.count("\n") <= 11  # 10 lines + truncation message

    async def test_output_not_truncated(self):
        """Should not truncate output within limit."""
        async def concise_handler():
            print("Line 1")
            print("Line 2")

        job = Job(job_id="test-1", name="Concise", expression="* * * * *", code="")
        limits = ResourceLimits(max_output_lines=10)
        context = ExecutionContext(job_id="test-1", job_name="Concise")

        executor = JobExecutor(job, concise_handler, limits, context)
        result = await executor.execute()

        assert result.status == ExecutionStatus.SUCCESS
        assert result.stdout_truncated is False
        assert "[... output truncated ...]" not in result.stdout


class TestJobExecutorResourceLimits:
    """Test resource limit configuration."""

    def test_default_limits(self):
        """Should have sensible defaults."""
        limits = ResourceLimits()

        assert limits.timeout_seconds == 30
        assert limits.max_memory_mb == 100
        assert limits.allow_network is False
        assert limits.max_output_lines == 1000

    def test_custom_limits(self):
        """Should accept custom limits."""
        limits = ResourceLimits(
            timeout_seconds=60,
            max_memory_mb=500,
            allow_network=True,
            max_output_lines=5000,
        )

        assert limits.timeout_seconds == 60
        assert limits.max_memory_mb == 500
        assert limits.allow_network is True
        assert limits.max_output_lines == 5000

    def test_limits_serialization(self):
        """Should serialize to dict."""
        limits = ResourceLimits(
            timeout_seconds=60,
            max_memory_mb=500,
            allow_network=True,
            max_output_lines=5000,
        )

        data = limits.to_dict()

        assert data["timeout_seconds"] == 60
        assert data["max_memory_mb"] == 500
        assert data["allow_network"] is True
        assert data["max_output_lines"] == 5000

    def test_limits_deserialization(self):
        """Should deserialize from dict."""
        data = {
            "timeout_seconds": 60,
            "max_memory_mb": 500,
            "allow_network": True,
            "max_output_lines": 5000,
        }

        limits = ResourceLimits.from_dict(data)

        assert limits.timeout_seconds == 60
        assert limits.max_memory_mb == 500
        assert limits.allow_network is True
        assert limits.max_output_lines == 5000

    def test_limits_deserialization_defaults(self):
        """Should use defaults for missing fields."""
        data = {"timeout_seconds": 60}

        limits = ResourceLimits.from_dict(data)

        assert limits.timeout_seconds == 60
        assert limits.max_memory_mb == 100  # Default
        assert limits.allow_network is False  # Default
        assert limits.max_output_lines == 1000  # Default


class TestExecutionResult:
    """Test ExecutionResult dataclass."""

    def test_result_creation(self):
        """Should create result with all fields."""
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            duration_ms=1500,
            stdout="output",
            stderr="error",
            memory_peak_mb=45,
            stdout_truncated=False,
        )

        assert result.status == ExecutionStatus.SUCCESS
        assert result.duration_ms == 1500
        assert result.stdout == "output"
        assert result.stderr == "error"
        assert result.memory_peak_mb == 45
        assert result.stdout_truncated is False

    def test_result_optional_fields(self):
        """Should create result with minimal fields."""
        result = ExecutionResult(
            status=ExecutionStatus.FAILED,
            duration_ms=100,
            stdout="",
            stderr="",
        )

        assert result.status == ExecutionStatus.FAILED
        assert result.memory_peak_mb is None
        assert result.stdout_truncated is False


class TestJobResourceLimits:
    """Test Job model with resource limits."""

    def test_job_with_default_limits(self):
        """Should create job with default resource limits."""
        job = Job(
            job_id="test-1",
            name="Test Job",
            expression="* * * * *",
            code="async def run(): pass",
        )

        assert job.resource_limits.timeout_seconds == 30
        assert job.resource_limits.max_memory_mb == 100

    def test_job_with_custom_limits(self):
        """Should create job with custom resource limits."""
        limits = ResourceLimits(timeout_seconds=60, max_memory_mb=200)

        job = Job(
            job_id="test-1",
            name="Test Job",
            expression="* * * * *",
            code="async def run(): pass",
            resource_limits=limits,
        )

        assert job.resource_limits.timeout_seconds == 60
        assert job.resource_limits.max_memory_mb == 200

    def test_job_serialization_includes_limits(self):
        """Should include resource limits in serialization."""
        limits = ResourceLimits(timeout_seconds=60, max_memory_mb=200)
        job = Job(
            job_id="test-1",
            name="Test Job",
            expression="* * * * *",
            code="async def run(): pass",
            resource_limits=limits,
        )

        data = job.to_dict()

        assert "resource_limits" in data
        assert data["resource_limits"]["timeout_seconds"] == 60
        assert data["resource_limits"]["max_memory_mb"] == 200

    def test_job_deserialization_includes_limits(self):
        """Should parse resource limits from dict."""
        data = {
            "job_id": "test-1",
            "name": "Test Job",
            "expression": "* * * * *",
            "code": "async def run(): pass",
            "status": "active",
            "last_run": None,
            "created_at": "2026-02-18T10:00:00+00:00",
            "updated_at": "2026-02-18T10:00:00+00:00",
            "resource_limits": {
                "timeout_seconds": 60,
                "max_memory_mb": 200,
                "allow_network": True,
                "max_output_lines": 500,
            },
        }

        job = Job.from_dict(data)

        assert job.resource_limits.timeout_seconds == 60
        assert job.resource_limits.max_memory_mb == 200
        assert job.resource_limits.allow_network is True
        assert job.resource_limits.max_output_lines == 500

    def test_job_deserialization_defaults_for_missing_limits(self):
        """Should use default limits when field missing."""
        data = {
            "job_id": "test-1",
            "name": "Test Job",
            "expression": "* * * * *",
            "code": "async def run(): pass",
            "status": "active",
            "last_run": None,
            "created_at": "2026-02-18T10:00:00+00:00",
            "updated_at": "2026-02-18T10:00:00+00:00",
        }

        job = Job.from_dict(data)

        assert job.resource_limits.timeout_seconds == 30
        assert job.resource_limits.max_memory_mb == 100


class TestExecutionRecordWithResources:
    """Test ExecutionRecord with resource fields."""

    def test_record_with_memory(self):
        """Should include memory_peak_mb field."""
        record = ExecutionRecord(
            execution_id="exec-1",
            job_id="job-1",
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            status=ExecutionStatus.SUCCESS,
            duration_ms=1500,
            memory_peak_mb=45,
        )

        assert record.memory_peak_mb == 45

    def test_record_with_truncation(self):
        """Should include stdout_truncated field."""
        record = ExecutionRecord(
            execution_id="exec-1",
            job_id="job-1",
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            status=ExecutionStatus.SUCCESS,
            duration_ms=1500,
            stdout_truncated=True,
        )

        assert record.stdout_truncated is True

    def test_record_serialization_includes_resources(self):
        """Should include resource fields in serialization."""
        record = ExecutionRecord(
            execution_id="exec-1",
            job_id="job-1",
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            status=ExecutionStatus.SUCCESS,
            duration_ms=1500,
            memory_peak_mb=45,
            stdout_truncated=True,
            stdout="output",
            stderr="error",
        )

        data = record.to_dict()

        assert data["memory_peak_mb"] == 45
        assert data["stdout_truncated"] is True

    def test_record_deserialization_includes_resources(self):
        """Should parse resource fields from dict."""
        data = {
            "execution_id": "exec-1",
            "job_id": "job-1",
            "started_at": "2026-02-18T10:00:00+00:00",
            "ended_at": "2026-02-18T10:05:00+00:00",
            "status": "success",
            "duration_ms": 1500,
            "memory_peak_mb": 45,
            "stdout_truncated": True,
            "stdout": "output",
            "stderr": "error",
        }

        record = ExecutionRecord.from_dict(data)

        assert record.memory_peak_mb == 45
        assert record.stdout_truncated is True

    def test_record_deserialization_defaults_for_missing_fields(self):
        """Should use defaults for missing resource fields."""
        data = {
            "execution_id": "exec-1",
            "job_id": "job-1",
            "started_at": "2026-02-18T10:00:00+00:00",
            "ended_at": "2026-02-18T10:05:00+00:00",
            "status": "success",
            "duration_ms": 1500,
        }

        record = ExecutionRecord.from_dict(data)

        assert record.memory_peak_mb is None
        assert record.stdout_truncated is False


class TestExecutionStatus:
    """Test ExecutionStatus enum."""

    def test_timeout_status(self):
        """Should have TIMEOUT status."""
        assert ExecutionStatus.TIMEOUT.value == "timeout"

    def test_success_status(self):
        """Should have SUCCESS status."""
        assert ExecutionStatus.SUCCESS.value == "success"

    def test_failed_status(self):
        """Should have FAILED status."""
        assert ExecutionStatus.FAILED.value == "failed"
