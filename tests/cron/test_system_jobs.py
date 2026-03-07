"""Tests for system jobs."""

from pathlib import Path
import inspect
from unittest.mock import MagicMock

import pytest

from src.cron.scheduler import CronScheduler
from src.cron.store import CronStore
from src.cron.system_jobs import (
    get_system_job,
    get_system_job_handler,
    list_system_jobs,
)


class TestSystemJobRegistry:
    """Tests for system job registry."""

    def test_list_system_jobs_returns_expected(self) -> None:
        """Should return list of system job IDs."""
        jobs = list_system_jobs()
        assert "session_ttl" in jobs
        assert "session_summarizer" in jobs

    def test_get_system_job_returns_definition(self) -> None:
        """Should return definition for valid job ID."""
        job = get_system_job("session_ttl")
        assert job is not None

        assert job.expression == "*/5 * * * *"
        assert inspect.iscoroutinefunction(job.handler)

    def test_get_system_job_handler_returns_callable(self) -> None:
        """Should return handler for valid handler_id."""
        handler = get_system_job_handler("session_ttl")
        assert handler is not None
        assert inspect.iscoroutinefunction(handler)

    def test_get_system_job_invalid(self) -> None:
        """Should return None for invalid job ID."""
        job = get_system_job("nonexistent_job")
        assert job is None


class TestSystemJobRegistration:
    """Tests for registering system jobs with scheduler."""

    @pytest.fixture
    async def scheduler(self, tmp_path: Path):
        """Create scheduler with temp storage."""
        store = CronStore(data_dir=tmp_path / "data")
        sched = CronScheduler(store=store, check_interval=0.1)
        yield sched
        await sched.stop()

    async def test_register_system_jobs_creates_jobs(self, scheduler: CronScheduler) -> None:
        """Should create system jobs when called."""
        await scheduler.register_system_jobs()

        assert "session_ttl" in scheduler._jobs
        assert "session_summarizer" in scheduler._jobs

        ttl_job = scheduler._jobs["session_ttl"]
        assert ttl_job.name == "Session Ttl"
        assert ttl_job.expression == "*/5 * * * *"

        summarize_job = scheduler._jobs["session_summarizer"]
        assert summarize_job.name == "Session Summarizer"
        assert summarize_job.expression == "*/5 * * * *"

    async def test_register_system_jobs_persists_handler_id(self, scheduler: CronScheduler) -> None:
        """Should persist system jobs with handler_id."""
        await scheduler.register_system_jobs()

        jobs = await scheduler._store.load_jobs()
        job_by_id = {job.job_id: job for job in jobs}

        assert job_by_id["session_ttl"].handler_id == "session_ttl"
        assert job_by_id["session_summarizer"].handler_id == "session_summarizer"

    async def test_register_system_jobs_idempotent(self, scheduler: CronScheduler) -> None:
        """Should not duplicate jobs on multiple calls."""
        await scheduler.register_system_jobs()
        await scheduler.register_system_jobs()

        jobs = await scheduler._store.load_jobs()
        session_jobs = [j for j in jobs if j.job_id == "session_ttl"]
        summarizer_jobs = [j for j in jobs if j.job_id == "session_summarizer"]

        assert len(session_jobs) == 1
        assert len(summarizer_jobs) == 1

    async def test_register_system_jobs_uses_config_interval(self, tmp_path: Path) -> None:
        """Should use config cron interval for summarizer job."""
        store = CronStore(data_dir=tmp_path / "data")
        config = MagicMock()
        config.session_cron_interval_minutes = 7
        scheduler = CronScheduler(store=store, check_interval=0.1, config=config)

        await scheduler.register_system_jobs()

        job = scheduler._jobs["session_summarizer"]
        assert job.expression == "*/7 * * * *"


class TestSystemJobLoading:
    """Tests for loading system jobs from store."""

    async def test_load_jobs_uses_system_handler(self, tmp_path: Path) -> None:
        """Should load system job handler by handler_id."""
        store = CronStore(data_dir=tmp_path / "data")
        job = get_system_job("session_ttl")
        assert job is not None

        await store.save_job(job.to_job())

        scheduler = CronScheduler(store=store, check_interval=0.1)
        await scheduler.start()

        assert "session_ttl" in scheduler._jobs
        handler = scheduler._jobs["session_ttl"].handler
        assert handler is get_system_job_handler("session_ttl")

        await scheduler.stop()
