"""Tests for verbose logging functionality."""
import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, patch

from alfred.verbose_logger import TelegramVerboseHandler, VerboseLoggerManager


@pytest.mark.asyncio
async def test_verbose_handler_emit_when_enabled():
    """Test that handler sends logs when enabled."""
    mock_app = MagicMock()
    mock_app.bot = MagicMock()
    mock_app.bot.send_message = AsyncMock()
    
    handler = TelegramVerboseHandler(mock_app, chat_id=123)
    handler.enable()
    
    # Create a log record
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    handler.emit(record)
    
    # Wait a bit for async send
    await asyncio.sleep(0.1)
    
    mock_app.bot.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_verbose_handler_no_emit_when_disabled():
    """Test that handler doesn't send logs when disabled."""
    mock_app = MagicMock()
    mock_app.bot = MagicMock()
    mock_app.bot.send_message = AsyncMock()
    
    handler = TelegramVerboseHandler(mock_app, chat_id=123)
    # Disabled by default
    
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    handler.emit(record)
    
    # Wait a bit
    await asyncio.sleep(0.1)
    
    mock_app.bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_verbose_handler_toggle():
    """Test toggle functionality."""
    mock_app = MagicMock()
    
    handler = TelegramVerboseHandler(mock_app, chat_id=123)
    
    assert handler.enabled is False
    
    enabled = handler.toggle()
    assert enabled is True
    assert handler.enabled is True
    
    enabled = handler.toggle()
    assert enabled is False
    assert handler.enabled is False


@pytest.mark.asyncio
async def test_verbose_manager_create_handler():
    """Test creating handler through manager."""
    manager = VerboseLoggerManager()
    mock_app = MagicMock()
    
    handler = manager.create_handler(123, mock_app)
    
    assert handler is not None
    assert manager.get_handler(123) is handler


@pytest.mark.asyncio
async def test_verbose_manager_toggle():
    """Test toggling through manager."""
    manager = VerboseLoggerManager()
    mock_app = MagicMock()
    
    # First toggle creates and enables
    enabled = manager.toggle_for_chat(456, mock_app)
    assert enabled is True
    assert manager.is_enabled(456) is True
    
    # Second toggle disables
    enabled = manager.toggle_for_chat(456, mock_app)
    assert enabled is False
    assert manager.is_enabled(456) is False


def test_verbose_manager_is_enabled_nonexistent():
    """Test is_enabled returns False for non-existent handler."""
    manager = VerboseLoggerManager()
    assert manager.is_enabled(999) is False


@pytest.mark.asyncio
async def test_verbose_handler_truncate_long_messages():
    """Test that long messages are truncated."""
    mock_app = MagicMock()
    mock_app.bot = AsyncMock()
    
    handler = TelegramVerboseHandler(mock_app, chat_id=123)
    handler.enable()
    
    # Create a very long message
    long_msg = "x" * 5000
    
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg=long_msg,
        args=(),
        exc_info=None
    )
    
    handler.emit(record)
    await asyncio.sleep(0.1)
    
    # Check that send_message was called
    mock_app.bot.send_message.assert_called_once()
    call_args = mock_app.bot.send_message.call_args
    
    # Message should be truncated
    assert len(call_args[1]["text"]) < 4100


import asyncio
