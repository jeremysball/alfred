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
    """Tests for CLI markdown rendering integration."""

    def test_cli_creates_markdown_renderer(self, mock_alfred: MagicMock) -> None:
        """CLIInterface creates a MarkdownRenderer on init."""
        from src.utils.markdown import MarkdownRenderer

        interface = CLIInterface(mock_alfred)

        assert hasattr(interface, "markdown_renderer")
        assert isinstance(interface.markdown_renderer, MarkdownRenderer)

    @pytest.mark.asyncio
    async def test_chat_renders_markdown_after_stream(
        self, mock_alfred: MagicMock
    ) -> None:
        """After streaming, response is rendered as markdown."""
        from collections.abc import AsyncGenerator

        interface = CLIInterface(mock_alfred)

        # Mock the markdown renderer
        interface.markdown_renderer.render = MagicMock(return_value="rendered output")

        # Create a proper async generator for chat_stream
        async def mock_stream(*args: object, **kwargs: object) -> AsyncGenerator[str, None]:
            yield "CLI response"

        mock_alfred.chat_stream = mock_stream

        inputs = iter(["Hello", "exit"])
        with (
            patch.object(interface.session, "prompt_async", side_effect=lambda: next(inputs)),
            patch("sys.stdout", StringIO()),
        ):
            await interface.run()

        # The streamed response "CLI response" should be passed to render
        interface.markdown_renderer.render.assert_called_once_with("CLI response")

    @pytest.mark.asyncio
    async def test_chat_does_not_render_empty_response(
        self, mock_alfred: MagicMock
    ) -> None:
        """Empty responses are not rendered."""
        from collections.abc import AsyncGenerator

        # Create mock that yields nothing
        async def empty_stream(*args: object, **kwargs: object) -> AsyncGenerator[str, None]:
            return
            yield  # pragma: no cover

        mock_alfred.chat_stream = empty_stream

        interface = CLIInterface(mock_alfred)
        interface.markdown_renderer.render = MagicMock(return_value="")

        inputs = iter(["Hello", "exit"])
        with (
            patch.object(interface.session, "prompt_async", side_effect=lambda: next(inputs)),
            patch("sys.stdout", StringIO()),
        ):
            await interface.run()

        # Empty response should not trigger render
        interface.markdown_renderer.render.assert_not_called()
