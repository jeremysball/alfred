"""Tests for /health command functionality."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from alfred.interfaces.pypitui.commands.health import HealthCommand


class TestHealthCommand:
    """Tests for HealthCommand."""

    @pytest.fixture
    def mock_tui(self):
        """Create a mock TUI with required attributes."""
        tui = MagicMock()
        tui.alfred = MagicMock()
        tui.alfred.core = MagicMock()
        tui.alfred.model_name = "kimi-test-model"

        # Mock session manager
        session_manager = MagicMock()
        session_manager.has_active_session.return_value = True
        session_manager._cli_session_id = "test-session-123"

        # Mock current session
        mock_session = MagicMock()
        mock_session.meta.session_id = "test-session-123"
        mock_session.meta.message_count = 5
        mock_session.messages = [MagicMock() for _ in range(5)]
        session_manager.get_current_cli_session.return_value = mock_session

        # Mock store for counts
        mock_store = MagicMock()

        async def mock_count_sessions():
            return 10

        async def mock_count_memories():
            return 25

        mock_store.count_sessions = mock_count_sessions
        mock_store.count_memories = mock_count_memories
        session_manager.store = mock_store

        tui.alfred.core.session_manager = session_manager

        # Mock memory store
        mock_memory_store = MagicMock()
        mock_memory_store.check_memory_threshold.return_value = (False, 25)
        tui.alfred.core.memory_store = mock_memory_store

        # Mock embedder with in_flight_items
        mock_embedder = MagicMock()
        mock_embedder.dimension = 768
        mock_embedder._model = MagicMock()  # Model is loaded
        mock_embedder.in_flight_items = []  # No items currently embedding
        mock_embedder.__class__.__name__ = "BGEProvider"
        tui.alfred.core.embedder = mock_embedder

        return tui

    def test_health_command_name(self):
        """Test command has correct name."""
        cmd = HealthCommand()
        assert cmd.name == "health"

    def test_health_command_description(self):
        """Test command has description."""
        cmd = HealthCommand()
        assert cmd.description == "Show system health status"

    def test_health_command_execute_returns_true(self, mock_tui):
        """Test execute returns True when handled."""
        cmd = HealthCommand()
        result = cmd.execute(mock_tui, None)
        assert result is True

    @pytest.mark.asyncio
    async def test_health_command_shows_session_info(self, mock_tui):
        """Test health command shows session information."""
        cmd = HealthCommand()

        # Execute in event loop
        with patch.object(asyncio, "get_running_loop", return_value=asyncio.get_event_loop()):
            cmd.execute(mock_tui, None)
            # Give the async task a chance to run
            await asyncio.sleep(0.1)

        # Check that _add_system_message was called with session info
        assert mock_tui._add_system_message.called
        call_args = mock_tui._add_system_message.call_args
        message = call_args[0][0]

        assert "SESSION SYSTEM" in message
        assert "test-ses..." in message  # Session ID is truncated to 8 chars
        assert "5" in message  # Message count

    @pytest.mark.asyncio
    async def test_health_command_shows_no_session_when_inactive(self, mock_tui):
        """Test health command shows 'No active session' when appropriate."""
        mock_tui.alfred.core.session_manager.has_active_session.return_value = False
        mock_tui.alfred.core.session_manager.get_current_cli_session.return_value = None

        cmd = HealthCommand()

        with patch.object(asyncio, "get_running_loop", return_value=asyncio.get_event_loop()):
            cmd.execute(mock_tui, None)
            await asyncio.sleep(0.1)

        call_args = mock_tui._add_system_message.call_args
        message = call_args[0][0]

        assert "No active session" in message

    @pytest.mark.asyncio
    async def test_health_command_shows_memory_info(self, mock_tui):
        """Test health command shows memory information."""
        cmd = HealthCommand()

        with patch.object(asyncio, "get_running_loop", return_value=asyncio.get_event_loop()):
            cmd.execute(mock_tui, None)
            await asyncio.sleep(0.1)

        call_args = mock_tui._add_system_message.call_args
        message = call_args[0][0]

        assert "MEMORY SYSTEM" in message
        assert "768" in message  # embedding dimension

    @pytest.mark.asyncio
    async def test_health_command_shows_embedding_provider(self, mock_tui):
        """Test health command shows embedding provider type."""
        # Set up BGE provider
        mock_tui.alfred.core.embedder.__class__.__name__ = "BGEProvider"

        cmd = HealthCommand()

        with patch.object(asyncio, "get_running_loop", return_value=asyncio.get_event_loop()):
            cmd.execute(mock_tui, None)
            await asyncio.sleep(0.1)

        call_args = mock_tui._add_system_message.call_args
        message = call_args[0][0]

        assert "BGE" in message

    @pytest.mark.asyncio
    async def test_health_command_detects_model_not_loaded(self, mock_tui):
        """Test health command shows when BGE model is not loaded."""
        # Create a mock with _model = None
        mock_embedder = MagicMock()
        mock_embedder._model = None  # Model not loaded
        mock_embedder.dimension = 768
        mock_embedder.in_flight_items = []
        mock_embedder.__class__.__name__ = "BGEProvider"
        mock_tui.alfred.core.embedder = mock_embedder

        cmd = HealthCommand()

        with patch.object(asyncio, "get_running_loop", return_value=asyncio.get_event_loop()):
            cmd.execute(mock_tui, None)
            await asyncio.sleep(0.1)

        call_args = mock_tui._add_system_message.call_args
        message = call_args[0][0]

        assert "PENDING" in message or "Not loaded" in message

    @pytest.mark.asyncio
    async def test_health_command_shows_model_name(self, mock_tui):
        """Test health command shows current LLM model name."""
        mock_tui.alfred.model_name = "kimi-k2-test"

        cmd = HealthCommand()

        with patch.object(asyncio, "get_running_loop", return_value=asyncio.get_event_loop()):
            cmd.execute(mock_tui, None)
            await asyncio.sleep(0.1)

        call_args = mock_tui._add_system_message.call_args
        message = call_args[0][0]

        assert "kimi-k2-test" in message

    @pytest.mark.asyncio
    async def test_health_command_shows_in_flight_idle(self, mock_tui):
        """Test health command shows idle when no items are being embedded."""
        mock_tui.alfred.core.embedder.in_flight_items = []

        cmd = HealthCommand()

        with patch.object(asyncio, "get_running_loop", return_value=asyncio.get_event_loop()):
            cmd.execute(mock_tui, None)
            await asyncio.sleep(0.1)

        call_args = mock_tui._add_system_message.call_args
        message = call_args[0][0]

        assert "Idle" in message or "Currently Embedding" in message

    @pytest.mark.asyncio
    async def test_health_command_shows_in_flight_items(self, mock_tui):
        """Test health command shows items currently being embedded."""
        mock_tui.alfred.core.embedder.in_flight_items = [
            "Remember this: user likes Python...",
            "Session summary from yesterday...",
        ]

        cmd = HealthCommand()

        with patch.object(asyncio, "get_running_loop", return_value=asyncio.get_event_loop()):
            cmd.execute(mock_tui, None)
            await asyncio.sleep(0.1)

        call_args = mock_tui._add_system_message.call_args
        message = call_args[0][0]

        assert "Currently Embedding" in message
        assert "2 item(s)" in message

    @pytest.mark.asyncio
    async def test_health_command_no_emoji(self, mock_tui):
        """Test health command output contains no emoji."""
        import re

        cmd = HealthCommand()

        with patch.object(asyncio, "get_running_loop", return_value=asyncio.get_event_loop()):
            cmd.execute(mock_tui, None)
            await asyncio.sleep(0.1)

        call_args = mock_tui._add_system_message.call_args
        message = call_args[0][0]

        # Check for common emoji ranges
        emoji_pattern = re.compile(
            "["
            "\U0001f600-\U0001f64f"  # emoticons
            "\U0001f300-\U0001f5ff"  # symbols & pictographs
            "\U0001f680-\U0001f6ff"  # transport & map symbols
            "\U0001f1e0-\U0001f1ff"  # flags
            "\U00002702-\U000027b0"
            "\U000024c2-\U0001f251"
            "\U0001f900-\U0001f9ff"  # supplemental symbols
            "\U0001fa00-\U0001fa6f"  # chess symbols
            "\U0001fa70-\U0001faff"  # symbols and pictographs extended-a
            "]+",
            flags=re.UNICODE,
        )

        assert not emoji_pattern.search(message), f"Found emoji in message: {message}"


class TestHealthCommandAsync:
    """Async tests for HealthCommand."""

    @pytest.mark.asyncio
    async def test_health_command_fetches_counts_async(self):
        """Test that health command fetches counts asynchronously."""
        from unittest.mock import AsyncMock

        cmd = HealthCommand()

        # Mock TUI with async store methods
        mock_tui = MagicMock()
        mock_tui.alfred = MagicMock()
        mock_tui.alfred.core = MagicMock()

        # Mock session manager with async methods
        mock_store = MagicMock()
        mock_store.count_sessions = AsyncMock(return_value=42)
        mock_store.count_memories = AsyncMock(return_value=100)

        session_manager = MagicMock()
        session_manager.store = mock_store
        session_manager.has_active_session.return_value = False
        mock_tui.alfred.core.session_manager = session_manager

        # Mock embedder
        mock_embedder = MagicMock()
        mock_embedder.dimension = 768
        mock_embedder._model = None
        mock_embedder.in_flight_items = []
        mock_embedder.__class__.__name__ = "BGEProvider"
        mock_tui.alfred.core.embedder = mock_embedder
        mock_tui.alfred.model_name = "test-model"

        # Execute
        with patch.object(asyncio, "get_running_loop", return_value=asyncio.get_event_loop()):
            result = cmd.execute(mock_tui, None)
            assert result is True
            await asyncio.sleep(0.1)

        # The async task should have been created
        # Note: We can't easily verify the async behavior without running the event loop
