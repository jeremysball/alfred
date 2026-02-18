"""Tests for Telegram interface."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.interfaces.telegram import TelegramInterface
from src.alfred import Alfred
from src.config import Config
from src.llm import ChatResponse


@pytest.fixture
def mock_config():
    """Create a mock config with telegram token."""
    config = MagicMock(spec=Config)
    config.telegram_bot_token = "test_token"
    return config


async def mock_chat_stream(message):
    """Mock async generator for chat_stream."""
    yield "Test response"


@pytest.fixture
def mock_alfred():
    """Create a mock Alfred engine."""
    alfred = MagicMock(spec=Alfred)
    alfred.chat_stream.side_effect = mock_chat_stream
    alfred.compact = AsyncMock(return_value="Compacted successfully")
    return alfred


@pytest.fixture
def mock_update():
    """Create a mock Telegram update with message."""
    update = MagicMock()
    update.message = MagicMock()
    update.message.text = "Hello Alfred"
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create a mock Telegram context."""
    return MagicMock()


@pytest.mark.asyncio
async def test_message_delegates_to_alfred(mock_config, mock_alfred, mock_update, mock_context):
    """Test that message handler delegates to Alfred.chat_stream()."""
    interface = TelegramInterface(mock_config, mock_alfred)

    await interface.message(mock_update, mock_context)

    assert mock_alfred.chat_stream.called
    # Verify it was called with the right message
    call_args = mock_alfred.chat_stream.call_args[0][0]
    assert call_args == "Hello Alfred"


@pytest.mark.asyncio
async def test_compact_delegates_to_alfred(mock_config, mock_alfred, mock_update, mock_context):
    """Test that compact handler delegates to Alfred.compact()."""
    interface = TelegramInterface(mock_config, mock_alfred)

    await interface.compact(mock_update, mock_context)

    mock_alfred.compact.assert_called_once()
    mock_update.message.reply_text.assert_called_once_with("Compacted successfully")


@pytest.mark.asyncio
async def test_start_sends_greeting(mock_config, mock_alfred, mock_update, mock_context):
    """Test that start handler sends greeting."""
    interface = TelegramInterface(mock_config, mock_alfred)

    await interface.start(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_once()
    call_args = mock_update.message.reply_text.call_args[0][0]
    assert "Alfred" in call_args


@pytest.mark.asyncio
async def test_message_handles_none_text(mock_config, mock_alfred, mock_context):
    """Test that message handler handles None text gracefully."""
    interface = TelegramInterface(mock_config, mock_alfred)

    update = MagicMock()
    update.message = MagicMock()
    update.message.text = None
    update.message.reply_text = AsyncMock()

    await interface.message(update, mock_context)

    assert not mock_alfred.chat_stream.called


@pytest.mark.asyncio
async def test_message_handles_missing_message(mock_config, mock_alfred, mock_context):
    """Test that message handler handles missing message gracefully."""
    interface = TelegramInterface(mock_config, mock_alfred)

    update = MagicMock()
    update.message = None

    await interface.message(update, mock_context)

    assert not mock_alfred.chat_stream.called


async def error_stream(message):
    """Mock async generator that raises an error."""
    raise Exception("API error")
    yield ""


@pytest.mark.asyncio
async def test_message_surfaces_errors(mock_config, mock_alfred, mock_update, mock_context):
    """Test that message handler surfaces errors to user."""
    interface = TelegramInterface(mock_config, mock_alfred)
    mock_alfred.chat_stream = error_stream

    # Should not raise - error is caught and displayed
    await interface.message(mock_update, mock_context)

    # Error should be displayed via edit_text
    mock_update.message.reply_text.assert_called_once()
    # edit_text should be called with error message
    assert mock_update.message.reply_text.return_value.edit_text.called


@pytest.mark.asyncio
async def test_setup_creates_handlers(mock_config, mock_alfred):
    """Test that setup creates all required handlers."""
    interface = TelegramInterface(mock_config, mock_alfred)

    # Mock Application.builder to avoid real API calls
    mock_app = MagicMock()
    mock_app.add_handler = MagicMock()

    mock_builder = MagicMock()
    mock_builder.token.return_value.build.return_value = mock_app

    with pytest.MonkeyPatch.context() as m:
        m.setattr("src.interfaces.telegram.Application.builder", lambda: mock_builder)

        result = interface.setup()

        assert result is mock_app
        # Should have 3 handlers: start, compact, message
        assert mock_app.add_handler.call_count == 3
