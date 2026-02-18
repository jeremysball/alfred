"""Tests for CLI interface."""

from collections.abc import AsyncIterator
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.alfred import Alfred
from src.interfaces.cli import CLIInterface


@pytest.fixture
def mock_alfred() -> MagicMock:
    """Create a mock Alfred engine."""
    alfred = MagicMock(spec=Alfred)

    # Create an async generator mock for chat_stream
    async def async_gen(*args: object, **kwargs: object) -> AsyncIterator[str]:
        yield "CLI response"

    alfred.chat_stream = AsyncMock(side_effect=async_gen)
    alfred.compact = AsyncMock(return_value="Compacted")
    return alfred


@pytest.mark.asyncio
async def test_chat_delegates_to_alfred(mock_alfred: MagicMock) -> None:
    """Test that CLI delegates chat to Alfred via chat_stream."""
    interface = CLIInterface(mock_alfred)

    with patch("sys.stdin", StringIO("Hello\nexit\n")), patch("sys.stdout", StringIO()):
        await interface.run()

    mock_alfred.chat_stream.assert_called_once_with("Hello")


@pytest.mark.asyncio
async def test_compact_delegates_to_alfred(mock_alfred: MagicMock) -> None:
    """Test that CLI delegates compact to Alfred."""
    interface = CLIInterface(mock_alfred)

    with patch("sys.stdin", StringIO("compact\nexit\n")), patch("sys.stdout", StringIO()):
        await interface.run()

    mock_alfred.compact.assert_called_once()


@pytest.mark.asyncio
async def test_exit_terminates_loop(mock_alfred: MagicMock) -> None:
    """Test that 'exit' command terminates the loop."""
    interface = CLIInterface(mock_alfred)

    with patch("sys.stdin", StringIO("exit\n")), patch("sys.stdout", StringIO()):
        await interface.run()

    # Should not call chat_stream
    mock_alfred.chat_stream.assert_not_called()


@pytest.mark.asyncio
async def test_empty_input_ignored(mock_alfred: MagicMock) -> None:
    """Test that empty input is ignored."""
    interface = CLIInterface(mock_alfred)

    with patch("sys.stdin", StringIO("\n\nHello\nexit\n")), patch("sys.stdout", StringIO()):
        await interface.run()

    # Only one chat_stream call for "Hello"
    mock_alfred.chat_stream.assert_called_once_with("Hello")


@pytest.mark.asyncio
async def test_eoferror_terminates_loop(mock_alfred: MagicMock) -> None:
    """Test that EOFError terminates the loop gracefully."""
    interface = CLIInterface(mock_alfred)

    # Simulate EOFError on first input
    with patch("builtins.input", side_effect=EOFError):
        await interface.run()

    # Should not call chat_stream
    mock_alfred.chat_stream.assert_not_called()


@pytest.mark.asyncio
async def test_case_insensitive_commands(mock_alfred: MagicMock) -> None:
    """Test that commands are case-insensitive."""
    interface = CLIInterface(mock_alfred)

    with patch("sys.stdin", StringIO("COMPACT\nEXIT\n")), patch("sys.stdout", StringIO()):
        await interface.run()

    mock_alfred.compact.assert_called_once()
