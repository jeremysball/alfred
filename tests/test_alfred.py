"""Tests for Alfred core engine."""

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
    ):
        # Create a mock stream that yields chunks
        mock_stream = MockStream(["Hello! ", "How ", "can ", "I ", "help ", "you?"])

        mock_llm = MagicMock()
        mock_llm.stream_chat_with_tools = mock_stream
        mock_factory.create.return_value = mock_llm

        mock_loader = AsyncMock()
        mock_loader.assemble.return_value = mock_context
        mock_loader_class.return_value = mock_loader

        alfred = Alfred(mock_config)
        response = await alfred.chat("Hello Alfred")

        assert isinstance(response, str)
        assert response == "Hello! How can I help you?"
        assert mock_stream.call_args is not None


@pytest.mark.asyncio
async def test_chat_builds_correct_messages(mock_config, mock_context):
    """Test that chat builds messages with system prompt and user input."""
    mock_stream = MockStream(["Test response"])

    with (
        patch("src.alfred.LLMFactory") as mock_factory,
        patch("src.alfred.ContextLoader") as mock_loader_class,
    ):
        mock_llm = MagicMock()
        mock_llm.stream_chat_with_tools = mock_stream
        mock_factory.create.return_value = mock_llm

        mock_loader = AsyncMock()
        mock_loader.assemble.return_value = mock_context
        mock_loader_class.return_value = mock_loader

        alfred = Alfred(mock_config)
        await alfred.chat("Test message")

        # Verify stream_chat_with_tools was called with correct messages
        assert mock_stream.call_args is not None
        messages = mock_stream.call_args[0]  # First positional arg

        assert len(messages) == 2
        assert messages[0].role == "system"
        assert "You are Alfred" in messages[0].content
        assert messages[1].role == "user"
        assert messages[1].content == "Test message"


@pytest.mark.asyncio
async def test_compact_returns_placeholder(mock_config):
    """Test that compact returns placeholder message."""
    with (
        patch("src.alfred.LLMFactory"),
        patch("src.alfred.ContextLoader"),
    ):
        alfred = Alfred(mock_config)
        result = await alfred.compact()

        assert result == "Compaction not yet implemented"
