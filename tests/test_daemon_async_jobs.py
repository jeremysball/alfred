"""Verify AlfredDaemon runs cron jobs asynchronously."""

import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alfred.container import ServiceLocator
from alfred.cron.daemon_runner import AlfredDaemon


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

    def test_scheduler_has_async_check_jobs(self):
        """Verify scheduler has async _check_jobs method."""
        with (
            patch("alfred.cron.daemon_runner.load_daemon_config") as mock_load_config,
            patch("alfred.cron.daemon_runner.setup_logging"),
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.SQLiteMemoryStore"),
        ):
            mock_config = MagicMock()
            mock_config.data_dir = MagicMock()
            mock_config.kimi_api_key = "test-key"
            mock_config.openai_api_key = "test-key"
            mock_load_config.return_value = mock_config
            
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            daemon = AlfredDaemon()

            # _check_jobs should be async
            assert asyncio.iscoroutinefunction(
                daemon.core.cron_scheduler._check_jobs
            ), "_check_jobs must be async"

    def test_scheduler_has_async_execute_job(self):
        """Verify scheduler has async _execute_job method."""
        with (
            patch("alfred.cron.daemon_runner.load_daemon_config") as mock_load_config,
            patch("alfred.cron.daemon_runner.setup_logging"),
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.SQLiteMemoryStore"),
        ):
            mock_config = MagicMock()
            mock_config.data_dir = MagicMock()
            mock_config.kimi_api_key = "test-key"
            mock_config.openai_api_key = "test-key"
            mock_load_config.return_value = mock_config
            
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            daemon = AlfredDaemon()

            # _execute_job should be async
            assert asyncio.iscoroutinefunction(
                daemon.core.cron_scheduler._execute_job
            ), "_execute_job must be async"

    def test_scheduler_runs_monitor_loop_async(self):
        """Verify scheduler runs monitor loop as async task."""
        with (
            patch("alfred.cron.daemon_runner.load_daemon_config") as mock_load_config,
            patch("alfred.cron.daemon_runner.setup_logging"),
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.SQLiteMemoryStore"),
        ):
            mock_config = MagicMock()
            mock_config.data_dir = MagicMock()
            mock_config.kimi_api_key = "test-key"
            mock_config.openai_api_key = "test-key"
            mock_load_config.return_value = mock_config
            
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            daemon = AlfredDaemon()

            # _monitor_loop should be async
            assert asyncio.iscoroutinefunction(
                daemon.core.cron_scheduler._monitor_loop
            ), "_monitor_loop must be async"

    def test_job_handler_must_be_async(self):
        """Verify job handlers must be async functions."""
        with (
            patch("alfred.cron.daemon_runner.load_daemon_config") as mock_load_config,
            patch("alfred.cron.daemon_runner.setup_logging"),
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.SQLiteMemoryStore"),
        ):
            mock_config = MagicMock()
            mock_config.data_dir = MagicMock()
            mock_config.kimi_api_key = "test-key"
            mock_config.openai_api_key = "test-key"
            mock_load_config.return_value = mock_config
            
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            daemon = AlfredDaemon()

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

    def test_daemon_has_async_run_method(self):
        """Verify AlfredDaemon.run() is async."""
        with (
            patch("alfred.cron.daemon_runner.load_daemon_config") as mock_load_config,
            patch("alfred.cron.daemon_runner.setup_logging"),
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.SQLiteMemoryStore"),
        ):
            mock_config = MagicMock()
            mock_config.data_dir = MagicMock()
            mock_config.kimi_api_key = "test-key"
            mock_config.openai_api_key = "test-key"
            mock_load_config.return_value = mock_config
            
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            daemon = AlfredDaemon()

            # run() should be async
            assert asyncio.iscoroutinefunction(daemon.run), "run() must be async"
