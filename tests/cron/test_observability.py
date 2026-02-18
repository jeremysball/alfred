"""Tests for cron observability stack."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.cron.models import ExecutionRecord, ExecutionStatus
from src.cron.observability import (
    Alert,
    AlertManager,
    AlertType,
    Counter,
    CronMetrics,
    Gauge,
    HealthChecker,
    HealthStatus,
    Histogram,
    Observability,
    StructuredLogger,
)


class TestCounter:
    """Tests for Counter metric."""

    async def test_initial_value_is_zero(self) -> None:
        counter = Counter("test_counter")
        assert counter.value == 0

    async def test_increment_by_one(self) -> None:
        counter = Counter("test_counter")
        await counter.increment()
        assert counter.value == 1

    async def test_increment_by_amount(self) -> None:
        counter = Counter("test_counter")
        await counter.increment(5)
        assert counter.value == 5

    async def test_increment_multiple_times(self) -> None:
        counter = Counter("test_counter")
        await counter.increment(3)
        await counter.increment(2)
        assert counter.value == 5

    async def test_concurrent_increments(self) -> None:
        counter = Counter("test_counter")

        async def increment_many() -> None:
            for _ in range(100):
                await counter.increment()

        await asyncio.gather(*[increment_many() for _ in range(5)])
        assert counter.value == 500

    async def test_to_dict(self) -> None:
        counter = Counter("jobs_done", "Total jobs done")
        await counter.increment(42)
        result = counter.to_dict()
        assert result["name"] == "jobs_done"
        assert result["type"] == "counter"
        assert result["value"] == 42
        assert result["description"] == "Total jobs done"


class TestHistogram:
    """Tests for Histogram metric."""

    async def test_initial_state(self) -> None:
        hist = Histogram("test_hist")
        assert hist.count == 0
        assert hist.sum_ms == 0.0

    async def test_observe_single_value(self) -> None:
        hist = Histogram("test_hist")
        await hist.observe(50)
        assert hist.count == 1
        assert hist.sum_ms == 50.0

    async def test_observe_multiple_values(self) -> None:
        hist = Histogram("test_hist")
        await hist.observe(50)
        await hist.observe(100)
        await hist.observe(150)
        assert hist.count == 3
        assert hist.sum_ms == 300.0

    async def test_bucket_counts(self) -> None:
        hist = Histogram("test_hist", buckets=[100, 200, 500])
        await hist.observe(50)   # le_100
        await hist.observe(150)  # le_200
        await hist.observe(300)  # le_500
        await hist.observe(600)  # +Inf

        buckets = hist.to_dict()["buckets"]
        assert buckets["le_100"] == 1
        assert buckets["le_200"] == 2
        assert buckets["le_500"] == 3
        assert buckets["+Inf"] == 4

    async def test_concurrent_observes(self) -> None:
        hist = Histogram("test_hist")

        async def observe_many() -> None:
            for _ in range(100):
                await hist.observe(50)

        await asyncio.gather(*[observe_many() for _ in range(5)])
        assert hist.count == 500
        assert hist.sum_ms == 25000.0

    async def test_to_dict(self) -> None:
        hist = Histogram("duration", "Request duration", buckets=[100, 200])
        await hist.observe(50)
        result = hist.to_dict()
        assert result["name"] == "duration"
        assert result["type"] == "histogram"
        assert result["count"] == 1
        assert result["sum_ms"] == 50.0
        assert "buckets" in result


class TestGauge:
    """Tests for Gauge metric."""

    async def test_initial_state(self) -> None:
        gauge = Gauge("test_gauge")
        assert gauge.total == 0.0
        assert gauge.get("any") is None

    async def test_set_value(self) -> None:
        gauge = Gauge("test_gauge")
        await gauge.set("job_a", 5.0)
        assert gauge.get("job_a") == 5.0
        assert gauge.total == 5.0

    async def test_update_value(self) -> None:
        gauge = Gauge("test_gauge")
        await gauge.set("job_a", 5.0)
        await gauge.set("job_a", 10.0)
        assert gauge.get("job_a") == 10.0

    async def test_multiple_labels(self) -> None:
        gauge = Gauge("test_gauge")
        await gauge.set("job_a", 5.0)
        await gauge.set("job_b", 3.0)
        assert gauge.get("job_a") == 5.0
        assert gauge.get("job_b") == 3.0
        assert gauge.total == 8.0

    async def test_remove_label(self) -> None:
        gauge = Gauge("test_gauge")
        await gauge.set("job_a", 5.0)
        await gauge.remove("job_a")
        assert gauge.get("job_a") is None
        assert gauge.total == 0.0

    async def test_to_dict(self) -> None:
        gauge = Gauge("queue_depth", "Current queue depth")
        await gauge.set("job_1", 3.0)
        result = gauge.to_dict()
        assert result["name"] == "queue_depth"
        assert result["type"] == "gauge"
        assert result["values"]["job_1"] == 3.0
        assert result["total"] == 3.0


class TestCronMetrics:
    """Tests for CronMetrics collection."""

    async def test_default_metrics_created(self) -> None:
        metrics = CronMetrics()
        assert metrics.jobs_executed.name == "jobs_executed_total"
        assert metrics.job_duration_ms.name == "job_duration_ms"
        assert metrics.job_failures.name == "job_failures_total"
        assert metrics.queue_depth.name == "queue_depth"
        assert metrics.scheduler_uptime_seconds.name == "scheduler_uptime_seconds"

    async def test_to_dict_contains_all_metrics(self) -> None:
        metrics = CronMetrics()
        await metrics.jobs_executed.increment()
        await metrics.job_duration_ms.observe(100)
        await metrics.queue_depth.set("job_1", 2.0)

        result = metrics.to_dict()
        assert "jobs_executed" in result
        assert "job_duration_ms" in result
        assert "job_failures" in result
        assert "queue_depth" in result
        assert "scheduler_uptime_seconds" in result


class TestStructuredLogger:
    """Tests for StructuredLogger."""

    @pytest.fixture
    async def log_file(self, tmp_path: Path) -> Path:
        return tmp_path / "test_logs.jsonl"

    @pytest.fixture
    async def logger(self, log_file: Path) -> StructuredLogger:
        return StructuredLogger(log_file)

    async def test_log_job_start_creates_entry(self, logger: StructuredLogger, log_file: Path) -> None:
        await logger.log_job_start("job-123", "Test Job", "print('hello')")

        with open(log_file) as f:
            lines = f.readlines()
        assert len(lines) == 1

        entry = json.loads(lines[0])
        assert entry["event"] == "job_start"
        assert entry["job_id"] == "job-123"
        assert entry["job_name"] == "Test Job"
        assert entry["code_snapshot"] == "print('hello')"
        assert entry["level"] == "INFO"

    async def test_log_job_end_success(self, logger: StructuredLogger, log_file: Path) -> None:
        record = ExecutionRecord(
            execution_id="exec-456",
            job_id="job-123",
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            status=ExecutionStatus.SUCCESS,
            duration_ms=1500,
        )
        await logger.log_job_end("job-123", "Test Job", record)

        with open(log_file) as f:
            lines = f.readlines()
        entry = json.loads(lines[0])
        assert entry["event"] == "job_end"
        assert entry["status"] == "success"
        assert entry["duration_ms"] == 1500
        assert entry["level"] == "INFO"

    async def test_log_job_end_failure(self, logger: StructuredLogger, log_file: Path) -> None:
        record = ExecutionRecord(
            execution_id="exec-456",
            job_id="job-123",
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            status=ExecutionStatus.FAILED,
            duration_ms=500,
            error_message="Something went wrong",
            stderr="Error output",
        )
        await logger.log_job_end("job-123", "Test Job", record)

        with open(log_file) as f:
            lines = f.readlines()
        entry = json.loads(lines[0])
        assert entry["status"] == "failed"
        assert entry["level"] == "ERROR"
        assert entry["error_message"] == "Something went wrong"
        assert entry["stderr"] == "Error output"

    async def test_log_scheduler_event(self, logger: StructuredLogger, log_file: Path) -> None:
        await logger.log_scheduler_event("scheduler_start", "Scheduler started")

        with open(log_file) as f:
            lines = f.readlines()
        entry = json.loads(lines[0])
        assert entry["event"] == "scheduler_start"
        assert entry["message"] == "Scheduler started"

    async def test_log_warning(self, logger: StructuredLogger, log_file: Path) -> None:
        await logger.log_warning("job-123", "Job is running slow")

        with open(log_file) as f:
            lines = f.readlines()
        entry = json.loads(lines[0])
        assert entry["level"] == "WARNING"
        assert entry["job_id"] == "job-123"
        assert entry["message"] == "Job is running slow"

    async def test_multiple_entries_in_file(self, logger: StructuredLogger, log_file: Path) -> None:
        await logger.log_job_start("job-1", "Job 1")
        await logger.log_job_start("job-2", "Job 2")
        await logger.log_scheduler_event("test", "Test event")

        with open(log_file) as f:
            lines = f.readlines()
        assert len(lines) == 3

    async def test_creates_parent_directory(self, tmp_path: Path) -> None:
        nested_dir = tmp_path / "nested" / "deep"
        log_file = nested_dir / "logs.jsonl"
        logger = StructuredLogger(log_file)

        await logger.log_scheduler_event("test", "Test")

        assert nested_dir.exists()
        assert log_file.exists()


class TestHealthChecker:
    """Tests for HealthChecker."""

    async def test_initial_state(self) -> None:
        checker = HealthChecker()
        status = await checker.check_health()
        assert not status.healthy
        assert not status.scheduler_running
        assert status.stuck_jobs == []

    async def test_scheduler_running_healthy(self) -> None:
        checker = HealthChecker()
        checker.set_scheduler_running(True)
        status = await checker.check_health()
        assert status.healthy
        assert status.scheduler_running

    async def test_scheduler_not_running_unhealthy(self) -> None:
        checker = HealthChecker()
        checker.set_scheduler_running(False)
        status = await checker.check_health()
        assert not status.healthy
        assert "not running" in status.message

    async def test_detect_stuck_job(self) -> None:
        checker = HealthChecker(stuck_threshold_seconds=0.1)
        checker.set_scheduler_running(True)

        await checker.record_job_start("job-123")
        await asyncio.sleep(0.15)

        status = await checker.check_health()
        assert not status.healthy
        assert "job-123" in status.stuck_jobs

    async def test_job_not_stuck_within_threshold(self) -> None:
        checker = HealthChecker(stuck_threshold_seconds=10)
        checker.set_scheduler_running(True)

        await checker.record_job_start("job-123")
        status = await checker.check_health()

        assert status.healthy
        assert status.stuck_jobs == []

    async def test_record_job_end_removes_tracking(self) -> None:
        checker = HealthChecker(stuck_threshold_seconds=0.1)
        checker.set_scheduler_running(True)

        await checker.record_job_start("job-123")
        await asyncio.sleep(0.05)
        await checker.record_job_end("job-123")
        await asyncio.sleep(0.1)

        status = await checker.check_health()
        assert status.healthy
        assert "job-123" not in status.stuck_jobs

    async def test_to_dict(self) -> None:
        checker = HealthChecker()
        checker.set_scheduler_running(True)
        status = await checker.check_health()

        result = status.to_dict()
        assert result["healthy"] is True
        assert result["scheduler_running"] is True
        assert result["stuck_jobs"] == []
        assert "timestamp" in result


class TestAlertManager:
    """Tests for AlertManager."""

    async def test_no_alerts_on_success(self) -> None:
        manager = AlertManager(failure_threshold=3)
        alerts = await manager.record_execution("job-1", success=True, duration_ms=100)
        assert alerts == []

    async def test_no_alert_before_threshold(self) -> None:
        manager = AlertManager(failure_threshold=3)
        await manager.record_execution("job-1", success=False, duration_ms=100)
        await manager.record_execution("job-1", success=False, duration_ms=100)
        alerts = await manager.record_execution("job-1", success=False, duration_ms=100)

        # Third failure meets threshold
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.CONSECUTIVE_FAILURES
        assert alerts[0].job_id == "job-1"
        assert "3 times" in alerts[0].message

    async def test_alert_on_subsequent_failures(self) -> None:
        manager = AlertManager(failure_threshold=3)
        # First 3 failures
        for _ in range(3):
            await manager.record_execution("job-1", success=False, duration_ms=100)

        # Fourth failure should also alert
        alerts = await manager.record_execution("job-1", success=False, duration_ms=100)
        assert len(alerts) == 1
        assert "4 times" in alerts[0].message

    async def test_resets_counter_on_success(self) -> None:
        manager = AlertManager(failure_threshold=3)
        await manager.record_execution("job-1", success=False, duration_ms=100)
        await manager.record_execution("job-1", success=False, duration_ms=100)
        await manager.record_execution("job-1", success=True, duration_ms=100)
        alerts = await manager.record_execution("job-1", success=False, duration_ms=100)

        # Should not alert, counter reset
        assert alerts == []

    async def test_slow_execution_alert(self) -> None:
        manager = AlertManager(slow_execution_threshold_ms=1000)
        alerts = await manager.record_execution("job-1", success=True, duration_ms=2000)

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.SLOW_EXECUTION
        assert alerts[0].severity == "warning"
        assert "2000ms" in alerts[0].message

    async def test_no_slow_alert_within_threshold(self) -> None:
        manager = AlertManager(slow_execution_threshold_ms=1000)
        alerts = await manager.record_execution("job-1", success=True, duration_ms=500)
        assert alerts == []

    async def test_multiple_alerts_same_execution(self) -> None:
        manager = AlertManager(failure_threshold=2, slow_execution_threshold_ms=1000)
        await manager.record_execution("job-1", success=False, duration_ms=2000)
        alerts = await manager.record_execution("job-1", success=False, duration_ms=2000)

        assert len(alerts) == 2
        alert_types = {a.alert_type for a in alerts}
        assert AlertType.CONSECUTIVE_FAILURES in alert_types
        assert AlertType.SLOW_EXECUTION in alert_types

    async def test_check_stuck_jobs_alerts(self) -> None:
        manager = AlertManager()
        health = HealthStatus(
            healthy=False,
            scheduler_running=True,
            stuck_jobs=["job-1", "job-2"],
        )
        alerts = await manager.check_stuck_jobs(["job-1", "job-2"], health)

        assert len(alerts) == 2
        assert all(a.alert_type == AlertType.JOB_STUCK for a in alerts)
        assert all(a.severity == "error" for a in alerts)

    async def test_scheduler_down_alert(self) -> None:
        manager = AlertManager()
        health = HealthStatus(
            healthy=False,
            scheduler_running=False,
            stuck_jobs=[],
        )
        alerts = await manager.check_stuck_jobs([], health)

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.SCHEDULER_DOWN
        assert alerts[0].severity == "error"

    async def test_alert_to_dict(self) -> None:
        alert = Alert(
            alert_type=AlertType.CONSECUTIVE_FAILURES,
            job_id="job-1",
            message="Job failed 5 times",
            severity="error",
        )
        result = alert.to_dict()
        assert result["alert_type"] == "CONSECUTIVE_FAILURES"
        assert result["job_id"] == "job-1"
        assert result["message"] == "Job failed 5 times"
        assert result["severity"] == "error"
        assert "timestamp" in result


class TestObservability:
    """Tests for the combined Observability class."""

    @pytest.fixture
    async def observability(self, tmp_path: Path) -> Observability:
        log_file = tmp_path / "cron_logs.jsonl"
        return Observability(
            log_file=log_file,
            failure_threshold=3,
            slow_execution_threshold_ms=1000,
            stuck_threshold_seconds=60,
        )

    async def test_components_initialized(self, observability: Observability) -> None:
        assert observability.logger is not None
        assert observability.metrics is not None
        assert observability.health is not None
        assert observability.alerts is not None

    async def test_to_dict(self, observability: Observability) -> None:
        observability.health.set_scheduler_running(True)
        result = await observability.to_dict()

        assert "metrics" in result
        assert "health" in result
        assert result["health"]["scheduler_running"] is True

    async def test_full_execution_flow(self, observability: Observability, tmp_path: Path) -> None:
        """Test a complete job execution with observability."""
        log_file = tmp_path / "cron_logs.jsonl"
        observability = Observability(log_file=log_file)

        # Set scheduler running
        observability.health.set_scheduler_running(True)

        # Record job start
        await observability.health.record_job_start("job-123")
        await observability.logger.log_job_start("job-123", "Test Job")

        # Simulate execution
        await asyncio.sleep(0.01)

        # Record execution end
        record = ExecutionRecord(
            execution_id="exec-456",
            job_id="job-123",
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
            status=ExecutionStatus.SUCCESS,
            duration_ms=50,
        )

        await observability.metrics.jobs_executed.increment()
        await observability.metrics.job_duration_ms.observe(50)
        await observability.health.record_job_end("job-123")
        await observability.logger.log_job_end("job-123", "Test Job", record)

        alerts = await observability.alerts.record_execution("job-123", True, 50)

        # Verify state
        assert observability.metrics.jobs_executed.value == 1
        assert observability.metrics.job_duration_ms.count == 1
        assert alerts == []

        # Verify log file
        with open(log_file) as f:
            lines = f.readlines()
        assert len(lines) == 2  # start and end
