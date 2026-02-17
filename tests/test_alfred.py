"""Tests for Alfred core engine."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.alfred import Alfred
from src.llm import ChatResponse


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


@pytest.mark.asyncio
async def test_chat_returns_response(mock_config, mock_context):
    """Test that chat returns a ChatResponse."""
    with (
        patch("src.alfred.LLMFactory") as mock_factory,
        patch("src.alfred.ContextLoader") as mock_loader_class,
    ):
        # Mock the LLM provider
        mock_llm = AsyncMock()
        mock_llm.chat.return_value = ChatResponse(
            content="Hello! How can I help you?",
            model="kimi",
            usage={"prompt_tokens": 10, "completion_tokens": 8},
        )
        mock_factory.create.return_value = mock_llm

        # Mock the context loader
        mock_loader = AsyncMock()
        mock_loader.assemble.return_value = mock_context
        mock_loader_class.return_value = mock_loader

        alfred = Alfred(mock_config)
        response = await alfred.chat("Hello Alfred")

        assert isinstance(response, ChatResponse)
        assert response.content == "Hello! How can I help you?"
        mock_llm.chat.assert_called_once()


@pytest.mark.asyncio
async def test_chat_builds_correct_messages(mock_config, mock_context):
    """Test that chat builds messages with system prompt and user input."""
    with (
        patch("src.alfred.LLMFactory") as mock_factory,
        patch("src.alfred.ContextLoader") as mock_loader_class,
    ):
        mock_llm = AsyncMock()
        mock_llm.chat.return_value = ChatResponse(content="Response", model="kimi")
        mock_factory.create.return_value = mock_llm

        mock_loader = AsyncMock()
        mock_loader.assemble.return_value = mock_context
        mock_loader_class.return_value = mock_loader

        alfred = Alfred(mock_config)
        await alfred.chat("Test message")

        # Verify messages were built correctly
        call_args = mock_llm.chat.call_args
        messages = call_args[0][0]

        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[0].content == "You are Alfred, a helpful assistant."
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
