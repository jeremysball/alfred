"""Tests for AlfredDaemon - standalone cron daemon."""

import asyncio
from unittest.mock import MagicMock, patch

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
    """Reset SessionManager singleton before each test."""
    from alfred.session import SessionManager
    SessionManager._instance = None
    yield
    SessionManager._instance = None


class TestAlfredDaemonInitialization:
    """Tests for AlfredDaemon initialization."""

    def test_creates_alfredcore_instance(self):
        """Daemon should create an AlfredCore instance."""
        with (
            patch("alfred.cron.daemon_runner.load_daemon_config") as mock_load_config,
            patch("alfred.cron.daemon_runner.setup_logging"),
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.create_memory_store"),
        ):
            mock_config = MagicMock()
            mock_config.data_dir = MagicMock()
            mock_config.kimi_api_key = "test-key"
            mock_config.openai_api_key = "test-key"
            mock_load_config.return_value = mock_config

            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            daemon = AlfredDaemon()

        assert hasattr(daemon, "core")
        assert daemon.core is not None

    def test_has_all_services_via_core(self):
        """Daemon should have all services accessible via core."""
        with (
            patch("alfred.cron.daemon_runner.load_daemon_config") as mock_load_config,
            patch("alfred.cron.daemon_runner.setup_logging"),
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.create_memory_store"),
        ):
            mock_config = MagicMock()
            mock_config.data_dir = MagicMock()
            mock_config.kimi_api_key = "test-key"
            mock_config.openai_api_key = "test-key"
            mock_load_config.return_value = mock_config

            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            daemon = AlfredDaemon()

        # Services accessible via core
        assert daemon.core.llm is not None
        assert daemon.core.embedder is not None
        assert daemon.core.memory_store is not None
        assert daemon.core.cron_scheduler is not None


class TestAlfredDaemonRun:
    """Tests for AlfredDaemon run behavior."""

    def test_run_method_exists(self):
        """Daemon should have a run method."""
        with (
            patch("alfred.cron.daemon_runner.load_daemon_config") as mock_load_config,
            patch("alfred.cron.daemon_runner.setup_logging"),
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.create_memory_store"),
        ):
            mock_config = MagicMock()
            mock_config.data_dir = MagicMock()
            mock_config.kimi_api_key = "test-key"
            mock_config.openai_api_key = "test-key"
            mock_load_config.return_value = mock_config

            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            daemon = AlfredDaemon()

            # Should have run method
            assert hasattr(daemon, 'run')
            assert asyncio.iscoroutinefunction(daemon.run)


class TestAlfredDaemonServices:
    """Tests for AlfredDaemon service registration."""

    def test_registers_services_in_locator(self):
        """Daemon should register services in ServiceLocator via core."""
        from alfred.embeddings.provider import EmbeddingProvider
        from alfred.llm import LLMProvider
        from alfred.session import SessionManager
        from alfred.storage.sqlite import SQLiteStore
        from alfred.tools.search_sessions import SessionSummarizer

        with (
            patch("alfred.cron.daemon_runner.load_daemon_config") as mock_load_config,
            patch("alfred.cron.daemon_runner.setup_logging"),
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.create_memory_store"),
        ):
            mock_config = MagicMock()
            mock_config.data_dir = MagicMock()
            mock_config.kimi_api_key = "test-key"
            mock_config.openai_api_key = "test-key"
            mock_load_config.return_value = mock_config

            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            AlfredDaemon()

        # All services should be registered
        assert ServiceLocator.has(SQLiteStore)
        assert ServiceLocator.has(EmbeddingProvider)
        assert ServiceLocator.has(LLMProvider)
        assert ServiceLocator.has(SessionManager)
        assert ServiceLocator.has(SessionSummarizer)
