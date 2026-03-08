"""Verify AlfredDaemon runs cron jobs asynchronously."""

import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alfred.config import Config
from alfred.container import ServiceLocator
from alfred.cron.daemon_runner import AlfredDaemon


@pytest.fixture
def test_config(tmp_path):
    """Create test configuration."""
    config = Config(
        kimi_api_key="test-key",
        openai_api_key="test-key",
        telegram_bot_token="test-token",
    )
    config.data_dir = tmp_path / "alfred_data"
    config.data_dir.mkdir(parents=True, exist_ok=True)
    return config


@pytest.fixture(autouse=True)
def clear_service_locator():
    """Clear ServiceLocator before each test."""
    ServiceLocator.clear()
    yield
    ServiceLocator.clear()


@pytest.fixture(autouse=True)
def reset_session_manager():
    """Reset SessionManager singleton."""
    from alfred.session import SessionManager
    SessionManager._instance = None
    yield
    SessionManager._instance = None


class TestAsyncJobExecution:
    """Tests that jobs are executed asynchronously."""

    def test_scheduler_has_async_check_jobs(self, test_config):
        """Verify scheduler has async _check_jobs method."""
        with (
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.create_memory_store"),
        ):
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            daemon = AlfredDaemon(test_config)

            # _check_jobs should be async
            assert asyncio.iscoroutinefunction(
                daemon.core.cron_scheduler._check_jobs
            ), "_check_jobs must be async"

    def test_scheduler_has_async_execute_job(self, test_config):
        """Verify scheduler has async _execute_job method."""
        with (
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.create_memory_store"),
        ):
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            daemon = AlfredDaemon(test_config)

            # _execute_job should be async
            assert asyncio.iscoroutinefunction(
                daemon.core.cron_scheduler._execute_job
            ), "_execute_job must be async"

    def test_scheduler_runs_monitor_loop_async(self, test_config):
        """Verify scheduler runs monitor loop as async task."""
        with (
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.create_memory_store"),
        ):
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            daemon = AlfredDaemon(test_config)

            # _monitor_loop should be async
            assert asyncio.iscoroutinefunction(
                daemon.core.cron_scheduler._monitor_loop
            ), "_monitor_loop must be async"

    def test_job_handler_must_be_async(self, test_config):
        """Verify job handlers must be async functions."""
        with (
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.create_memory_store"),
        ):
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            daemon = AlfredDaemon(test_config)

            # Test that non-async handlers are rejected
            with pytest.raises(ValueError, match="must be async"):
                daemon.core.cron_scheduler._compile_handler("""
def run():
    pass
""")

            # Test that async handlers are accepted
            handler = daemon.core.cron_scheduler._compile_handler("""
async def run():
    pass
""")
            assert handler is not None
            assert inspect.iscoroutinefunction(handler)

    def test_daemon_has_async_run_method(self, test_config):
        """Verify AlfredDaemon.run() is async."""
        with (
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.create_memory_store"),
        ):
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            daemon = AlfredDaemon(test_config)

            # run() should be async
            assert asyncio.iscoroutinefunction(daemon.run), "run() must be async"
