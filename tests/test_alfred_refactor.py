"""Tests for Alfred refactoring to use AlfredCore."""

from unittest.mock import MagicMock, patch

import pytest

from alfred.alfred import Alfred
from alfred.config import Config
from alfred.container import ServiceLocator
from alfred.core import AlfredCore


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


class TestAlfredUsesAlfredCore:
    """Tests that Alfred properly uses AlfredCore for services."""

    def test_alfred_creates_alfredcore_instance(self, test_config):
        """Alfred should create an AlfredCore instance."""
        with (
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.SQLiteMemoryStore"),
            patch("alfred.alfred.ContextLoader"),
            patch("alfred.alfred.register_builtin_tools"),
            patch("alfred.alfred.get_registry"),
            patch("alfred.alfred.Agent"),
        ):
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            alfred = Alfred(test_config)

        assert hasattr(alfred, "core")
        assert isinstance(alfred.core, AlfredCore)

    def test_alfred_accesses_services_via_core(self, test_config):
        """Alfred should access services through core properties."""
        with (
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.SQLiteMemoryStore"),
            patch("alfred.alfred.ContextLoader"),
            patch("alfred.alfred.register_builtin_tools"),
            patch("alfred.alfred.get_registry"),
            patch("alfred.alfred.Agent"),
        ):
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            alfred = Alfred(test_config)

        # Services should be accessible via core
        assert alfred.core.llm is not None
        assert alfred.core.embedder is not None
        assert alfred.core.memory_store is not None
        assert alfred.core.sqlite_store is not None
        assert alfred.core.session_manager is not None
        assert alfred.core.summarizer is not None
        assert alfred.core.cron_scheduler is not None

    def test_alfred_no_duplicate_service_init(self, test_config):
        """Alfred should not initialize services directly - core should."""
        with (
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.SQLiteMemoryStore") as mock_memory,
            patch("alfred.alfred.ContextLoader"),
            patch("alfred.alfred.register_builtin_tools"),
            patch("alfred.alfred.get_registry"),
            patch("alfred.alfred.Agent"),
        ):
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            Alfred(test_config)

        # Services should be created by AlfredCore, not Alfred
        # LLMFactory.create called once (by AlfredCore)
        mock_llm.create.assert_called_once()
        # create_provider called once (by AlfredCore)
        mock_embedder.assert_called_once()
        # create_memory_store called once (by AlfredCore)
        mock_memory.assert_called_once()

    def test_alfred_registers_services_in_locator(self, test_config):
        """Alfred should have services registered in ServiceLocator via core."""
        from alfred.embeddings.provider import EmbeddingProvider
        from alfred.llm import LLMProvider
        from alfred.session import SessionManager
        from alfred.storage.sqlite import SQLiteStore
        from alfred.tools.search_sessions import SessionSummarizer

        with (
            patch("alfred.core.LLMFactory") as mock_llm,
            patch("alfred.core.create_provider") as mock_embedder,
            patch("alfred.core.SQLiteMemoryStore"),
            patch("alfred.alfred.ContextLoader"),
            patch("alfred.alfred.register_builtin_tools"),
            patch("alfred.alfred.get_registry"),
            patch("alfred.alfred.Agent"),
        ):
            mock_llm.create.return_value = MagicMock()
            mock_embedder.return_value = MagicMock()

            Alfred(test_config)

        # All services should be registered
        assert ServiceLocator.has(SQLiteStore)
        assert ServiceLocator.has(EmbeddingProvider)
        assert ServiceLocator.has(LLMProvider)
        assert ServiceLocator.has(SessionManager)
        assert ServiceLocator.has(SessionSummarizer)
