"""Tests for CLI interface."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from io import StringIO

from src.interfaces.cli import CLIInterface
from src.alfred import Alfred
from src.config import Config
from src.llm import ChatResponse


@pytest.fixture
def mock_config():
    """Create a mock config."""
    return MagicMock(spec=Config)


@pytest.fixture
def mock_alfred():
    """Create a mock Alfred engine."""
    alfred = MagicMock(spec=Alfred)
    alfred.chat = AsyncMock(
        return_value=ChatResponse(content="CLI response", model="kimi")
    )
    alfred.compact = AsyncMock(return_value="Compacted")
    return alfred


@pytest.mark.asyncio
async def test_chat_delegates_to_alfred(mock_config, mock_alfred):
    """Test that CLI delegates chat to Alfred."""
    interface = CLIInterface(mock_config, mock_alfred)

    with patch("sys.stdin", StringIO("Hello\nexit\n")):
        with patch("sys.stdout", StringIO()):
            await interface.run()

    mock_alfred.chat.assert_called_once_with("Hello")


@pytest.mark.asyncio
async def test_compact_delegates_to_alfred(mock_config, mock_alfred):
    """Test that CLI delegates compact to Alfred."""
    interface = CLIInterface(mock_config, mock_alfred)

    with patch("sys.stdin", StringIO("compact\nexit\n")):
        with patch("sys.stdout", StringIO()):
            await interface.run()

    mock_alfred.compact.assert_called_once()


@pytest.mark.asyncio
async def test_exit_terminates_loop(mock_config, mock_alfred):
    """Test that 'exit' command terminates the loop."""
    interface = CLIInterface(mock_config, mock_alfred)

    with patch("sys.stdin", StringIO("exit\n")):
        with patch("sys.stdout", StringIO()):
            await interface.run()

    # Should not call chat
    mock_alfred.chat.assert_not_called()


@pytest.mark.asyncio
async def test_empty_input_ignored(mock_config, mock_alfred):
    """Test that empty input is ignored."""
    interface = CLIInterface(mock_config, mock_alfred)

    with patch("sys.stdin", StringIO("\n\nHello\nexit\n")):
        with patch("sys.stdout", StringIO()):
            await interface.run()

    # Only one chat call for "Hello"
    mock_alfred.chat.assert_called_once_with("Hello")


@pytest.mark.asyncio
async def test_eoferror_terminates_loop(mock_config, mock_alfred):
    """Test that EOFError terminates the loop gracefully."""
    interface = CLIInterface(mock_config, mock_alfred)

    # Simulate EOFError on first input
    with patch("builtins.input", side_effect=EOFError):
        await interface.run()

    # Should not call chat
    mock_alfred.chat.assert_not_called()


@pytest.mark.asyncio
async def test_case_insensitive_commands(mock_config, mock_alfred):
    """Test that commands are case-insensitive."""
    interface = CLIInterface(mock_config, mock_alfred)

    with patch("sys.stdin", StringIO("COMPACT\nEXIT\n")):
        with patch("sys.stdout", StringIO()):
            await interface.run()

    mock_alfred.compact.assert_called_once()
