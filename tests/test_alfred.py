"""Tests for Alfred core engine."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.alfred import Alfred


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
        patch("src.alfred.LLMFactory") as mock_factory,
        patch("src.alfred.ContextLoader") as mock_loader_class,
        patch("src.alfred.EmbeddingClient") as mock_embedder_class,
        patch("src.alfred.MemoryStore") as mock_memory_class,
        patch("src.alfred.CronStore") as mock_cron_store_class,
        patch("src.alfred.CronScheduler") as mock_cron_scheduler_class,
        patch("src.alfred.register_builtin_tools"),
        patch("src.alfred.get_registry") as mock_registry,
        patch("src.alfred.Agent") as mock_agent_class,
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
        patch("src.alfred.LLMFactory") as mock_factory,
        patch("src.alfred.ContextLoader") as mock_loader_class,
        patch("src.alfred.EmbeddingClient") as mock_embedder_class,
        patch("src.alfred.MemoryStore") as mock_memory_class,
        patch("src.alfred.CronStore") as mock_cron_store_class,
        patch("src.alfred.CronScheduler") as mock_cron_scheduler_class,
        patch("src.alfred.register_builtin_tools"),
        patch("src.alfred.get_registry") as mock_registry,
        patch("src.alfred.Agent") as mock_agent_class,
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
        patch("src.alfred.LLMFactory"),
        patch("src.alfred.ContextLoader"),
        patch("src.alfred.EmbeddingClient"),
        patch("src.alfred.MemoryStore"),
        patch("src.alfred.CronStore"),
        patch("src.alfred.CronScheduler"),
        patch("src.alfred.register_builtin_tools"),
        patch("src.alfred.get_registry"),
        patch("src.alfred.Agent"),
    ):
        alfred = Alfred(mock_config)
        result = await alfred.compact()

        assert result == "Compaction not yet implemented"


def test_sync_token_tracker_from_session(mock_config):
    """Test that token tracker is synced from session messages.

    Only output (assistant) tokens are estimated. Input tokens remain 0
    because the LLM's prompt_tokens includes system prompt and formatting
    overhead that we cannot accurately estimate.
    """
    from datetime import UTC, datetime

    from src.session import Message, Role

    with (
        patch("src.alfred.LLMFactory"),
        patch("src.alfred.ContextLoader"),
        patch("src.alfred.EmbeddingClient"),
        patch("src.alfred.MemoryStore"),
        patch("src.alfred.CronStore"),
        patch("src.alfred.CronScheduler"),
        patch("src.alfred.register_builtin_tools"),
        patch("src.alfred.get_registry"),
        patch("src.alfred.Agent"),
    ):
        alfred = Alfred(mock_config)

        # Create mock messages
        # User message: 40 chars (not counted - input tokens start at 0)
        # Assistant message: 76 chars = ~19 tokens (at 4 chars/token)
        mock_messages = [
            Message(
                idx=0,
                role=Role.USER,
                content="Hello, this is a test message from user.",
                timestamp=datetime.now(UTC),
            ),
            Message(
                idx=1,
                role=Role.ASSISTANT,
                content="Hello! I am the assistant responding to your test message with more content.",
                timestamp=datetime.now(UTC),
            ),
        ]

        # Mock the session manager's get_session_messages
        alfred.session_manager.get_session_messages = MagicMock(return_value=mock_messages)

        # Verify tracker starts at 0
        assert alfred.token_tracker.usage.input_tokens == 0
        assert alfred.token_tracker.usage.output_tokens == 0

        # Sync token tracker
        alfred.sync_token_tracker_from_session()

        # Verify only output tokens were estimated
        # Input remains 0 (will reflect actual usage from first new message)
        # Output: len("Hello! I am the assistant responding to your test message with more content.") // 4 = 76 // 4 = 19
        assert alfred.token_tracker.usage.input_tokens == 0
        assert alfred.token_tracker.usage.output_tokens == 19


def test_sync_token_tracker_empty_session(mock_config):
    """Test that sync handles empty sessions gracefully."""
    with (
        patch("src.alfred.LLMFactory"),
        patch("src.alfred.ContextLoader"),
        patch("src.alfred.EmbeddingClient"),
        patch("src.alfred.MemoryStore"),
        patch("src.alfred.CronStore"),
        patch("src.alfred.CronScheduler"),
        patch("src.alfred.register_builtin_tools"),
        patch("src.alfred.get_registry"),
        patch("src.alfred.Agent"),
    ):
        alfred = Alfred(mock_config)

        # Mock empty session
        alfred.session_manager.get_session_messages = MagicMock(return_value=[])

        # Should not raise
        alfred.sync_token_tracker_from_session()

        # Tokens should remain at 0
        assert alfred.token_tracker.usage.input_tokens == 0
        assert alfred.token_tracker.usage.output_tokens == 0
