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
