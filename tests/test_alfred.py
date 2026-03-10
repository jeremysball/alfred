"""Tests for Alfred core engine."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alfred.alfred import Alfred


@pytest.fixture
def mock_config():
    """Create a mock config."""
    config = MagicMock()
    config.default_llm_provider = "kimi"
    config.context_files = {
        "agents": MagicMock(),
        "soul": MagicMock(),
        "user": MagicMock(),
        "tools": MagicMock(),
    }
    config.data_dir = Path("/tmp/test_data")
    return config


@pytest.fixture
def mock_context():
    """Create a mock assembled context."""
    context = MagicMock()
    context.system_prompt = "You are Alfred, a helpful assistant."
    context.memories = []
    return context


class MockStream:
    """Mock async iterator that records calls and yields chunks."""

    def __init__(self, chunks):
        self.chunks = chunks
        self.call_args = None
        self.call_kwargs = None

    def __call__(self, *args, **kwargs):
        self.call_args = args
        self.call_kwargs = kwargs
        return self

    def __aiter__(self):
        self._idx = 0
        return self

    async def __anext__(self):
        if self._idx >= len(self.chunks):
            raise StopAsyncIteration
        chunk = self.chunks[self._idx]
        self._idx += 1
        return chunk


@pytest.mark.asyncio
async def test_chat_returns_response(mock_config, mock_context):
    """Test that chat returns a response string from streaming."""
    with (
        patch("alfred.core.LLMFactory") as mock_factory,
        patch("alfred.alfred.ContextLoader") as mock_loader_class,
        patch("alfred.core.create_provider") as mock_embedder_class,
        patch("alfred.core.SQLiteMemoryStore") as mock_memory_class,
        patch("alfred.core.CronStore"),
        patch("alfred.core.CronScheduler"),
        patch("alfred.alfred.register_builtin_tools"),
        patch("alfred.alfred.get_registry") as mock_registry,
        patch("alfred.alfred.Agent") as mock_agent_class,
    ):
        # Create a mock stream that yields chunks
        mock_stream = MockStream(["Hello! ", "How ", "can ", "I ", "help ", "you?"])

        mock_llm = MagicMock()
        mock_llm.stream_chat_with_tools = mock_stream
        mock_factory.create.return_value = mock_llm

        mock_loader = AsyncMock()
        mock_loader.assemble.return_value = mock_context
        mock_loader_class.return_value = mock_loader

        mock_embedder = AsyncMock()
        mock_embedder.embed.return_value = [0.1, 0.2, 0.3]
        mock_embedder_class.return_value = mock_embedder

        mock_memory = AsyncMock()
        mock_memory.get_all_entries.return_value = []
        mock_memory_class.return_value = mock_memory

        mock_registry.return_value.list_tools.return_value = []

        mock_agent = AsyncMock()
        mock_agent.run.return_value = "Hello! How can I help you?"
        mock_agent_class.return_value = mock_agent

        alfred = Alfred(mock_config)
        response = await alfred.chat("Hello Alfred")

        assert isinstance(response, str)
        assert response == "Hello! How can I help you?"


@pytest.mark.asyncio
async def test_chat_builds_correct_messages(mock_config, mock_context):
    """Test that chat builds messages with system prompt and user input."""
    with (
        patch("alfred.core.LLMFactory") as mock_factory,
        patch("alfred.alfred.ContextLoader") as mock_loader_class,
        patch("alfred.core.create_provider") as mock_embedder_class,
        patch("alfred.core.SQLiteMemoryStore") as mock_memory_class,
        patch("alfred.core.CronStore"),
        patch("alfred.core.CronScheduler"),
        patch("alfred.alfred.register_builtin_tools"),
        patch("alfred.alfred.get_registry") as mock_registry,
        patch("alfred.alfred.Agent") as mock_agent_class,
    ):
        mock_llm = MagicMock()
        mock_factory.create.return_value = mock_llm

        mock_loader = AsyncMock()
        mock_loader.assemble.return_value = mock_context
        mock_loader_class.return_value = mock_loader

        mock_embedder = AsyncMock()
        mock_embedder.embed.return_value = [0.1, 0.2, 0.3]
        mock_embedder_class.return_value = mock_embedder

        mock_memory = AsyncMock()
        mock_memory.get_all_entries.return_value = []
        mock_memory_class.return_value = mock_memory

        mock_registry.return_value.list_tools.return_value = []

        mock_agent = AsyncMock()
        mock_agent.run.return_value = "Test response"
        mock_agent_class.return_value = mock_agent

        alfred = Alfred(mock_config)
        await alfred.chat("Test message")

        # Verify agent.run was called
        assert mock_agent.run.called


@pytest.mark.asyncio
async def test_compact_returns_placeholder(mock_config):
    """Test that compact returns placeholder message."""
    with (
        patch("alfred.core.LLMFactory"),
        patch("alfred.alfred.ContextLoader"),
        patch("alfred.core.create_provider"),
        patch("alfred.core.SQLiteMemoryStore"),
        patch("alfred.core.CronStore"),
        patch("alfred.core.CronScheduler"),
        patch("alfred.alfred.register_builtin_tools"),
        patch("alfred.alfred.get_registry"),
        patch("alfred.alfred.Agent"),
    ):
        alfred = Alfred(mock_config)
        result = await alfred.compact()

        assert result == "Compaction not yet implemented"


def test_sync_token_tracker_from_session(mock_config):
    """Test that token tracker is synced from messages with stored token counts.

    Legacy messages without stored counts contribute 0. Only messages with
    input_tokens/output_tokens > 0 are counted.
    """
    from datetime import UTC, datetime

    from alfred.session import Message, Role

    with (
        patch("alfred.core.LLMFactory"),
        patch("alfred.alfred.ContextLoader"),
        patch("alfred.core.create_provider"),
        patch("alfred.core.SQLiteMemoryStore"),
        patch("alfred.core.CronStore"),
        patch("alfred.core.CronScheduler"),
        patch("alfred.alfred.register_builtin_tools"),
        patch("alfred.alfred.get_registry"),
        patch("alfred.alfred.Agent"),
    ):
        alfred = Alfred(mock_config)

        # Create mock messages - some with token counts, some without (legacy)
        mock_messages = [
            Message(
                idx=0,
                role=Role.USER,
                content="Hello, this is a test message from user.",
                timestamp=datetime.now(UTC),
                input_tokens=100,  # Has stored count
                output_tokens=0,
            ),
            Message(
                idx=1,
                role=Role.ASSISTANT,
                content=(
                    "Hello! I am the assistant responding to your test message "
                    "with more content."
                ),
                timestamp=datetime.now(UTC),
                input_tokens=0,
                output_tokens=250,  # Has stored count
            ),
            Message(
                idx=2,
                role=Role.USER,
                content="Legacy message without stored tokens.",
                timestamp=datetime.now(UTC),
                input_tokens=0,  # Legacy - no stored count
                output_tokens=0,
            ),
        ]

        # Mock the session manager's get_session_messages
        alfred.core.session_manager.get_session_messages = MagicMock(return_value=mock_messages)

        # Verify tracker starts at 0
        assert alfred.token_tracker.usage.input_tokens == 0
        assert alfred.token_tracker.usage.output_tokens == 0

        # Sync token tracker
        alfred.sync_token_tracker_from_session()

        # Verify only stored token counts are used (legacy messages contribute 0)
        assert alfred.token_tracker.usage.input_tokens == 100  # Only first user message
        assert alfred.token_tracker.usage.output_tokens == 250  # Only assistant message


def test_sync_token_tracker_empty_session(mock_config):
    """Test that sync handles empty sessions gracefully."""
    with (
        patch("alfred.core.LLMFactory"),
        patch("alfred.alfred.ContextLoader"),
        patch("alfred.core.create_provider"),
        patch("alfred.core.SQLiteMemoryStore"),
        patch("alfred.core.CronStore"),
        patch("alfred.core.CronScheduler"),
        patch("alfred.alfred.register_builtin_tools"),
        patch("alfred.alfred.get_registry"),
        patch("alfred.alfred.Agent"),
    ):
        alfred = Alfred(mock_config)

        # Mock empty session
        alfred.core.session_manager.get_session_messages = MagicMock(return_value=[])

        # Should not raise
        alfred.sync_token_tracker_from_session()

        # Tokens should remain at 0
        assert alfred.token_tracker.usage.input_tokens == 0
        assert alfred.token_tracker.usage.output_tokens == 0
