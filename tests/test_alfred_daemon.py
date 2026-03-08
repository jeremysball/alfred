"""Tests for AlfredDaemon - standalone cron daemon."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from alfred.config import Config
from alfred.container import ServiceLocator
from alfred.cron.daemon_runner import AlfredDaemon
from alfred.embeddings.provider import EmbeddingProvider
from alfred.llm import LLMProvider
from alfred.session import SessionManager
from alfred.storage.sqlite import SQLiteStore
from alfred.tools.search_sessions import SessionSummarizer


@pytest.fixture
def test_config(tmp_path):
    """Create a test configuration with isolated data directory."""
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
    """Reset SessionManager singleton before each test."""
    from alfred.session import SessionManager
    SessionManager._instance = None
    yield
    SessionManager._instance = None


class TestAlfredDaemonInitialization:
    """Tests for AlfredDaemon initialization."""

    def test_creates_alfredcore_instance(self, test_config):
        """Daemon should create an AlfredCore instance."""
        with (
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.create_memory_store"),
        ):
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            daemon = AlfredDaemon(test_config)

        assert hasattr(daemon, "core")
        assert daemon.core is not None

    def test_has_all_services_via_core(self, test_config):
        """Daemon should have all services accessible via core."""
        with (
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.create_memory_store"),
        ):
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            daemon = AlfredDaemon(test_config)

        # Services accessible via core
        assert daemon.core.llm is not None
        assert daemon.core.embedder is not None
        assert daemon.core.memory_store is not None
        assert daemon.core.cron_scheduler is not None


class TestAlfredDaemonRun:
    """Tests for AlfredDaemon run behavior."""

    def test_run_method_exists(self, test_config):
        """Daemon should have a run method."""
        with (
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.create_memory_store"),
        ):
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            daemon = AlfredDaemon(test_config)

            # Should have run method
            assert hasattr(daemon, 'run')
            assert asyncio.iscoroutinefunction(daemon.run)


class TestAlfredDaemonServices:
    """Tests for AlfredDaemon service registration."""

    def test_registers_services_in_locator(self, test_config):
        """Daemon should register services in ServiceLocator via core."""
        with (
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.create_memory_store"),
        ):
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            AlfredDaemon(test_config)

        # All services should be registered
        assert ServiceLocator.has(SQLiteStore)
        assert ServiceLocator.has(EmbeddingProvider)
        assert ServiceLocator.has(LLMProvider)
        assert ServiceLocator.has(SessionManager)
        assert ServiceLocator.has(SessionSummarizer)
