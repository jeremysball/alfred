"""Tests for CLI interface using prompt_toolkit."""

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

    # Create an async generator factory for chat_stream
    def make_stream(*args: object, **kwargs: object) -> AsyncIterator[str]:
        async def async_gen() -> AsyncIterator[str]:
            yield "CLI response"
        return async_gen()

    alfred.chat_stream = AsyncMock(side_effect=make_stream)
    alfred.compact = AsyncMock(return_value="Compacted")
    return alfred


@pytest.mark.asyncio
async def test_chat_delegates_to_alfred(mock_alfred: MagicMock) -> None:
    """Test that CLI delegates chat to Alfred via chat_stream."""
    interface = CLIInterface(mock_alfred)

    # Mock prompt_async to return inputs sequentially
    inputs = iter(["Hello", "exit"])
    with (
        patch.object(interface.session, "prompt_async", side_effect=lambda: next(inputs)),
        patch("sys.stdout", StringIO()),
    ):
        await interface.run()

    mock_alfred.chat_stream.assert_called_once_with("Hello")


@pytest.mark.asyncio
async def test_compact_delegates_to_alfred(mock_alfred: MagicMock) -> None:
    """Test that CLI delegates compact to Alfred."""
    interface = CLIInterface(mock_alfred)

    inputs = iter(["compact", "exit"])
    with (
        patch.object(interface.session, "prompt_async", side_effect=lambda: next(inputs)),
        patch("sys.stdout", StringIO()),
    ):
        await interface.run()

    mock_alfred.compact.assert_called_once()


@pytest.mark.asyncio
async def test_exit_terminates_loop(mock_alfred: MagicMock) -> None:
    """Test that 'exit' command terminates the loop."""
    interface = CLIInterface(mock_alfred)

    with (
        patch.object(interface.session, "prompt_async", return_value="exit"),
        patch("sys.stdout", StringIO()),
    ):
        await interface.run()

    # Should not call chat_stream
    mock_alfred.chat_stream.assert_not_called()


@pytest.mark.asyncio
async def test_empty_input_ignored(mock_alfred: MagicMock) -> None:
    """Test that empty input is ignored."""
    interface = CLIInterface(mock_alfred)

    inputs = iter(["", "", "Hello", "exit"])
    with (
        patch.object(interface.session, "prompt_async", side_effect=lambda: next(inputs)),
        patch("sys.stdout", StringIO()),
    ):
        await interface.run()

    # Only one chat_stream call for "Hello"
    mock_alfred.chat_stream.assert_called_once_with("Hello")


@pytest.mark.asyncio
async def test_eof_terminates_loop(mock_alfred: MagicMock) -> None:
    """Test that EOF terminates the loop gracefully."""
    interface = CLIInterface(mock_alfred)

    with patch.object(interface.session, "prompt_async", side_effect=EOFError):
        await interface.run()

    # Should not call chat_stream
    mock_alfred.chat_stream.assert_not_called()


@pytest.mark.asyncio
async def test_keyboard_interrupt_terminates_loop(mock_alfred: MagicMock) -> None:
    """Test that KeyboardInterrupt terminates the loop gracefully."""
    interface = CLIInterface(mock_alfred)

    with (
        patch.object(interface.session, "prompt_async", side_effect=KeyboardInterrupt),
        patch("sys.stdout", StringIO()),
    ):
        await interface.run()

    # Should not call chat_stream
    mock_alfred.chat_stream.assert_not_called()


@pytest.mark.asyncio
async def test_case_insensitive_commands(mock_alfred: MagicMock) -> None:
    """Test that commands are case-insensitive."""
    interface = CLIInterface(mock_alfred)

    inputs = iter(["COMPACT", "EXIT"])
    with (
        patch.object(interface.session, "prompt_async", side_effect=lambda: next(inputs)),
        patch("sys.stdout", StringIO()),
    ):
        await interface.run()

    mock_alfred.compact.assert_called_once()


class TestCLIMarkdownRendering:
    """Tests for CLI markdown rendering integration using Rich Live."""

    def test_cli_creates_console(self, mock_alfred: MagicMock) -> None:
        """CLIInterface creates a Rich Console on init."""
        from rich.console import Console

        interface = CLIInterface(mock_alfred)

        assert hasattr(interface, "console")
        assert isinstance(interface.console, Console)

    @pytest.mark.asyncio
    async def test_chat_uses_live_for_markdown(
        self, mock_alfred: MagicMock
    ) -> None:
        """Streaming uses Rich Live to render markdown incrementally."""
        from collections.abc import AsyncGenerator

        interface = CLIInterface(mock_alfred)

        # Create a proper async generator for chat_stream
        async def mock_stream(*args: object, **kwargs: object) -> AsyncGenerator[str, None]:
            yield "CLI response"

        mock_alfred.chat_stream = mock_stream

        inputs = iter(["Hello", "exit"])

        # Patch Live to verify it's called
        with (
            patch.object(interface.session, "prompt_async", side_effect=lambda: next(inputs)),
            patch("src.interfaces.cli.Live") as mock_live,
        ):
            await interface.run()

        # Live should have been instantiated
        mock_live.assert_called()

    @pytest.mark.asyncio
    async def test_chat_handles_empty_stream(
        self, mock_alfred: MagicMock
    ) -> None:
        """Empty streams are handled gracefully."""
        from collections.abc import AsyncGenerator

        # Create mock that yields nothing
        async def empty_stream(*args: object, **kwargs: object) -> AsyncGenerator[str, None]:
            return
            yield  # pragma: no cover

        mock_alfred.chat_stream = empty_stream

        interface = CLIInterface(mock_alfred)

        inputs = iter(["Hello", "exit"])

        with (
            patch.object(interface.session, "prompt_async", side_effect=lambda: next(inputs)),
            patch("src.interfaces.cli.Live") as mock_live,
        ):
            await interface.run()

        # Live should still be called even with empty stream
        mock_live.assert_called()
