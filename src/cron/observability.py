"""Observability stack for cron scheduler.

Provides structured logging, metrics collection, health checks,
and alerting for job execution monitoring.
"""

import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any

from src.cron.models import ExecutionRecord, ExecutionStatus

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Types of alerts that can be generated."""

    CONSECUTIVE_FAILURES = auto()
    SLOW_EXECUTION = auto()
    JOB_STUCK = auto()
    SCHEDULER_DOWN = auto()


@dataclass
class Alert:
    """An alert indicating an issue with job execution."""

    alert_type: AlertType
    job_id: str | None
    message: str
    severity: str  # "warning" or "error"
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "alert_type": self.alert_type.name,
            "job_id": self.job_id,
            "message": self.message,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class HealthStatus:
    """Health check result for the scheduler."""

    healthy: bool
    scheduler_running: bool
    stuck_jobs: list[str] = field(default_factory=list)
    storage_accessible: bool = True
    message: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert health status to dictionary."""
        return {
            "healthy": self.healthy,
            "scheduler_running": self.scheduler_running,
            "stuck_jobs": self.stuck_jobs,
            "storage_accessible": self.storage_accessible,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


class Counter:
    """Simple counter metric."""

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self._value: int = 0
        self._lock = asyncio.Lock()

    async def increment(self, amount: int = 1) -> None:
        """Increment counter by amount."""
        async with self._lock:
            self._value += amount

    @property
    def value(self) -> int:
        """Get current counter value."""
        return self._value

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": "counter",
            "value": self._value,
            "description": self.description,
        }


class Histogram:
    """Histogram metric with configurable buckets (in milliseconds)."""

    DEFAULT_BUCKETS = [10, 50, 100, 250, 500, 1000, 2500, 5000, 10000]

    def __init__(
        self,
        name: str,
        description: str = "",
        buckets: list[int] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.buckets = buckets or self.DEFAULT_BUCKETS
        self._counts: dict[str, int] = {f"le_{b}": 0 for b in self.buckets}
        self._counts["+Inf"] = 0
        self._sum: float = 0.0
        self._count: int = 0
        self._lock = asyncio.Lock()

    async def observe(self, value: float) -> None:
        """Record an observation (value in milliseconds)."""
        async with self._lock:
            self._sum += value
            self._count += 1
            for bucket in self.buckets:
                if value <= bucket:
                    self._counts[f"le_{bucket}"] += 1
            self._counts["+Inf"] += 1

    @property
    def count(self) -> int:
        """Get total number of observations."""
        return self._count

    @property
    def sum_ms(self) -> float:
        """Get sum of all observations in milliseconds."""
        return self._sum

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": "histogram",
            "count": self._count,
            "sum_ms": self._sum,
            "buckets": self._counts.copy(),
            "description": self.description,
        }


class Gauge:
    """Gauge metric that can go up and down."""

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self._values: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def set(self, label: str, value: float) -> None:
        """Set gauge value for a label."""
        async with self._lock:
            self._values[label] = value

    async def remove(self, label: str) -> None:
        """Remove a label from the gauge."""
        async with self._lock:
            self._values.pop(label, None)

    def get(self, label: str) -> float | None:
        """Get gauge value for a label."""
        return self._values.get(label)

    @property
    def total(self) -> float:
        """Get sum of all gauge values."""
        return sum(self._values.values())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": "gauge",
            "values": self._values.copy(),
            "total": self.total,
            "description": self.description,
        }


@dataclass
class CronMetrics:
    """Collection of all cron metrics."""

    jobs_executed: Counter = field(
        default_factory=lambda: Counter(
            "jobs_executed_total",
            "Total number of jobs executed",
        )
    )
    job_duration_ms: Histogram = field(
        default_factory=lambda: Histogram(
            "job_duration_ms",
            "Job execution duration in milliseconds",
        )
    )
    job_failures: Counter = field(
        default_factory=lambda: Counter(
            "job_failures_total",
            "Total number of job failures",
        )
    )
    queue_depth: Gauge = field(
        default_factory=lambda: Gauge(
            "queue_depth",
            "Current number of queued jobs per job_id",
        )
    )
    scheduler_uptime_seconds: Counter = field(
        default_factory=lambda: Counter(
            "scheduler_uptime_seconds",
            "Total seconds the scheduler has been running",
        )
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert all metrics to dictionary."""
        return {
            "jobs_executed": self.jobs_executed.to_dict(),
            "job_duration_ms": self.job_duration_ms.to_dict(),
            "job_failures": self.job_failures.to_dict(),
            "queue_depth": self.queue_depth.to_dict(),
            "scheduler_uptime_seconds": self.scheduler_uptime_seconds.to_dict(),
        }


class StructuredLogger:
    """Structured JSON logger for cron job execution.

    Writes log entries to a JSONL file for audit and debugging.
    """

    def __init__(self, log_file: Path) -> None:
        self.log_file = log_file
        self._lock = asyncio.Lock()

    async def _write_log(self, entry: dict[str, Any]) -> None:
        """Write a log entry to file."""
        async with self._lock:
            # Ensure directory exists
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")

    async def log_job_start(
        self,
        job_id: str,
        job_name: str,
        code_snapshot: str | None = None,
    ) -> None:
        """Log job execution start.

        Args:
            job_id: Unique job identifier
            job_name: Human-readable job name
            code_snapshot: Optional code that will be executed
        """
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": "INFO",
            "event": "job_start",
            "job_id": job_id,
            "job_name": job_name,
            "code_snapshot": code_snapshot,
        }
        await self._write_log(entry)
        logger.info(f"Job {job_name} ({job_id}) started")

    async def log_job_end(
        self,
        job_id: str,
        job_name: str,
        execution_record: ExecutionRecord,
        code_snapshot: str | None = None,
    ) -> None:
        """Log job execution end.

        Args:
            job_id: Unique job identifier
            job_name: Human-readable job name
            execution_record: Record of the execution
            code_snapshot: Optional code that was executed
        """
        level = "INFO" if execution_record.status == ExecutionStatus.SUCCESS else "ERROR"
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": level,
            "event": "job_end",
            "job_id": job_id,
            "job_name": job_name,
            "execution_id": execution_record.execution_id,
            "status": execution_record.status.value,
            "duration_ms": execution_record.duration_ms,
            "error_message": execution_record.error_message,
            "stdout": execution_record.stdout,
            "stderr": execution_record.stderr,
            "code_snapshot": code_snapshot,
        }
        await self._write_log(entry)
        if execution_record.status == ExecutionStatus.SUCCESS:
            logger.info(
                f"Job {job_name} ({job_id}) completed in {execution_record.duration_ms}ms"
            )
        else:
            logger.error(
                f"Job {job_name} ({job_id}) failed: {execution_record.error_message}"
            )

    async def log_scheduler_event(self, event: str, message: str) -> None:
        """Log scheduler-level events (start, stop, etc.)."""
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": "INFO",
            "event": event,
            "message": message,
        }
        await self._write_log(entry)
        logger.info(f"Scheduler event '{event}': {message}")

    async def log_warning(self, job_id: str | None, message: str) -> None:
        """Log a warning event."""
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": "WARNING",
            "event": "warning",
            "job_id": job_id,
            "message": message,
        }
        await self._write_log(entry)
        logger.warning(message)


class HealthChecker:
    """Health checker for the cron scheduler.

    Monitors scheduler status and detects stuck jobs.
    """

    def __init__(self, stuck_threshold_seconds: float = 300) -> None:
        """Initialize health checker.

        Args:
            stuck_threshold_seconds: Time after which a running job is considered stuck
        """
        self.stuck_threshold_seconds = stuck_threshold_seconds
        self._scheduler_running = False
        self._job_start_times: dict[str, datetime] = {}
        self._lock = asyncio.Lock()

    def set_scheduler_running(self, running: bool) -> None:
        """Update scheduler running status."""
        self._scheduler_running = running

    async def record_job_start(self, job_id: str) -> None:
        """Record that a job has started running."""
        async with self._lock:
            self._job_start_times[job_id] = datetime.now(UTC)

    async def record_job_end(self, job_id: str) -> None:
        """Record that a job has finished."""
        async with self._lock:
            self._job_start_times.pop(job_id, None)

    async def check_health(self) -> HealthStatus:
        """Check overall health of the scheduler.

        Returns:
            HealthStatus with details about any issues
        """
        now = datetime.now(UTC)
        stuck_jobs: list[str] = []

        async with self._lock:
            for job_id, start_time in self._job_start_times.items():
                elapsed = (now - start_time).total_seconds()
                if elapsed > self.stuck_threshold_seconds:
                    stuck_jobs.append(job_id)

        healthy = self._scheduler_running and not stuck_jobs

        message_parts = []
        if not self._scheduler_running:
            message_parts.append("Scheduler is not running")
        if stuck_jobs:
            message_parts.append(f"Stuck jobs: {', '.join(stuck_jobs)}")
        if healthy:
            message_parts.append("All systems healthy")

        return HealthStatus(
            healthy=healthy,
            scheduler_running=self._scheduler_running,
            stuck_jobs=stuck_jobs,
            message="; ".join(message_parts),
        )


class AlertManager:
    """Alert manager for job execution issues.

    Tracks consecutive failures and generates alerts when thresholds are exceeded.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        slow_execution_threshold_ms: float = 30000,
    ) -> None:
        """Initialize alert manager.

        Args:
            failure_threshold: Number of consecutive failures before alerting
            slow_execution_threshold_ms: Duration threshold for slow execution alerts
        """
        self.failure_threshold = failure_threshold
        self.slow_execution_threshold_ms = slow_execution_threshold_ms
        self._failure_counts: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def record_execution(
        self,
        job_id: str,
        success: bool,
        duration_ms: float,
    ) -> list[Alert]:
        """Record a job execution and generate any relevant alerts.

        Args:
            job_id: The job that executed
            success: Whether execution succeeded
            duration_ms: Execution duration in milliseconds

        Returns:
            List of alerts generated from this execution
        """
        alerts: list[Alert] = []

        async with self._lock:
            if success:
                self._failure_counts[job_id] = 0
            else:
                self._failure_counts[job_id] += 1
                if self._failure_counts[job_id] >= self.failure_threshold:
                    alerts.append(
                        Alert(
                            alert_type=AlertType.CONSECUTIVE_FAILURES,
                            job_id=job_id,
                            message=(
                                f"Job {job_id} has failed "
                                f"{self._failure_counts[job_id]} times consecutively"
                            ),
                            severity="error",
                        )
                    )

        if duration_ms > self.slow_execution_threshold_ms:
            alerts.append(
                Alert(
                    alert_type=AlertType.SLOW_EXECUTION,
                    job_id=job_id,
                    message=(
                        f"Job {job_id} took {duration_ms:.0f}ms, "
                        f"exceeding threshold of {self.slow_execution_threshold_ms:.0f}ms"
                    ),
                    severity="warning",
                )
            )

        return alerts

    async def check_stuck_jobs(
        self,
        stuck_jobs: list[str],
        health_status: HealthStatus,
    ) -> list[Alert]:
        """Generate alerts for stuck jobs and scheduler issues.

        Args:
            stuck_jobs: List of job IDs that are stuck
            health_status: Current health status

        Returns:
            List of alerts
        """
        alerts: list[Alert] = []

        for job_id in stuck_jobs:
            alerts.append(
                Alert(
                    alert_type=AlertType.JOB_STUCK,
                    job_id=job_id,
                    message=f"Job {job_id} has been running longer than expected",
                    severity="error",
                )
            )

        if not health_status.scheduler_running:
            alerts.append(
                Alert(
                    alert_type=AlertType.SCHEDULER_DOWN,
                    job_id=None,
                    message="Cron scheduler is not running",
                    severity="error",
                )
            )

        return alerts


class Observability:
    """Combined observability stack for cron scheduler.

    Provides structured logging, metrics, health checks, and alerting
    in a single interface.
    """

    def __init__(
        self,
        log_file: Path,
        failure_threshold: int = 3,
        slow_execution_threshold_ms: float = 30000,
        stuck_threshold_seconds: float = 300,
    ) -> None:
        """Initialize the observability stack.

        Args:
            log_file: Path to JSONL log file
            failure_threshold: Consecutive failures before alerting
            slow_execution_threshold_ms: Duration threshold for slow alerts
            stuck_threshold_seconds: Time before a job is considered stuck
        """
        self.logger = StructuredLogger(log_file)
        self.metrics = CronMetrics()
        self.health = HealthChecker(stuck_threshold_seconds)
        self.alerts = AlertManager(
            failure_threshold=failure_threshold,
            slow_execution_threshold_ms=slow_execution_threshold_ms,
        )

    async def to_dict(self) -> dict[str, Any]:
        """Convert observability state to dictionary."""
        health = await self.health.check_health()
        return {
            "metrics": self.metrics.to_dict(),
            "health": health.to_dict(),
        }
