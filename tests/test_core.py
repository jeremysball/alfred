"""Tests for AlfredCore - shared services container."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from alfred.config import Config
from alfred.container import ServiceLocator
from alfred.core import AlfredCore
from alfred.cron.scheduler import CronScheduler
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
    # Clear any existing instance
    SessionManager._instance = None
    yield
    # Cleanup after test
    SessionManager._instance = None


class TestAlfredCoreInitialization:
    """Tests for AlfredCore initialization behavior."""

    def test_creates_data_directory_if_missing(self, tmp_path):
        """Core should create data directory structure on init."""
        data_dir = tmp_path / "new_alfred_data"
        config = MagicMock(spec=Config)
        config.data_dir = data_dir
        config.kimi_api_key = "test"
        config.openai_api_key = "test"

        with (
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.create_memory_store"),
        ):
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            AlfredCore(config)

        assert data_dir.exists()

    def test_makes_services_available_via_properties(self, test_config):
        """Core should provide access to initialized services."""
        with (
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.create_memory_store"),
        ):
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            core = AlfredCore(test_config)

        # Services should be accessible
        assert core.llm is not None
        assert core.embedder is not None
        assert core.memory_store is not None
        assert core.sqlite_store is not None
        assert core.session_manager is not None
        assert core.summarizer is not None

    def test_cron_scheduler_property_returns_scheduler(self, test_config):
        """Core should provide a configured cron scheduler."""
        with (
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.create_memory_store"),
            patch("alfred.core.CronScheduler") as mock_scheduler_class,
        ):
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()
            mock_scheduler = MagicMock(spec=CronScheduler)
            mock_scheduler_class.return_value = mock_scheduler

            core = AlfredCore(test_config)
            scheduler = core.cron_scheduler

        assert scheduler is mock_scheduler


class TestAlfredCoreServiceLocator:
    """Tests for ServiceLocator integration behavior."""

    def test_registers_core_services_for_global_access(self, test_config):
        """Core should register services so cron jobs can resolve them."""
        with (
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.create_memory_store"),
        ):
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            AlfredCore(test_config)

        # Services should be resolvable
        assert ServiceLocator.has(SQLiteStore)
        assert ServiceLocator.has(EmbeddingProvider)
        assert ServiceLocator.has(LLMProvider)
        assert ServiceLocator.has(SessionManager)
        assert ServiceLocator.has(SessionSummarizer)

    def test_registered_services_match_core_properties(self, test_config):
        """Services from locator should be same instances as core properties."""
        with (
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.create_memory_store"),
        ):
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            core = AlfredCore(test_config)

        # Services resolved from locator should match core's instances
        assert ServiceLocator.resolve(SQLiteStore) is core.sqlite_store
        assert ServiceLocator.resolve(EmbeddingProvider) is core.embedder
        assert ServiceLocator.resolve(LLMProvider) is core.llm
        assert ServiceLocator.resolve(SessionManager) is core.session_manager
        assert ServiceLocator.resolve(SessionSummarizer) is core.summarizer


class TestAlfredCoreReuse:
    """Tests for sharing AlfredCore between components."""

    def test_same_core_used_by_multiple_consumers(self, test_config):
        """Multiple components using same core should share services."""
        with (
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.create_memory_store"),
        ):
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            AlfredCore(test_config)

        # Simulate two different consumers accessing services
        consumer_a_store = ServiceLocator.resolve(SQLiteStore)
        consumer_b_store = ServiceLocator.resolve(SQLiteStore)

        # Should be same instance (shared)
        assert consumer_a_store is consumer_b_store


class TestAlfredCoreErrorHandling:
    """Tests for error handling during initialization."""

    def test_handles_missing_api_keys_gracefully(self, tmp_path):
        """Core should provide clear errors if configuration is invalid."""
        config = MagicMock(spec=Config)
        config.data_dir = tmp_path / "data"
        config.kimi_api_key = None
        config.openai_api_key = None

        # Should raise an informative error about configuration
        with pytest.raises(Exception):
            AlfredCore(config)
