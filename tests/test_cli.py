"""Tests for CLI interface using prompt_toolkit."""

from collections.abc import AsyncGenerator
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.alfred import Alfred
from src.interfaces.cli import CLIInterface
from src.token_tracker import TokenUsage


@pytest.fixture
def mock_alfred() -> MagicMock:
    """Create a mock Alfred engine."""
    alfred = MagicMock(spec=Alfred)

    # Create an async generator factory for chat_stream
    def make_stream(*args: object, **kwargs: object) -> AsyncGenerator[str, None]:
        async def async_gen() -> AsyncGenerator[str, None]:
            yield "CLI response"
        return async_gen()

    alfred.chat_stream = AsyncMock(side_effect=make_stream)
    alfred.compact = AsyncMock(return_value="Compacted")

    # Add token tracker mock for status display
    alfred.model_name = "kimi/moonshot-v1-128k"
    mock_token_tracker = MagicMock()
    mock_token_tracker.usage = TokenUsage(
        input_tokens=100,
        output_tokens=50,
        cache_read_tokens=0,
        reasoning_tokens=0,
    )
    mock_token_tracker.context_tokens = 500
    alfred.token_tracker = mock_token_tracker

    return alfred


def make_mock_session(inputs: list[str]):
    """Create a mock PromptSession that returns inputs sequentially."""
    input_iter = iter(inputs)

    async def mock_prompt(*args, **kwargs):
        return next(input_iter)

    mock_session = MagicMock()
    mock_session.prompt_async = mock_prompt
    return mock_session


@pytest.mark.asyncio
async def test_chat_delegates_to_alfred(mock_alfred: MagicMock) -> None:
    """Test that CLI delegates chat to Alfred via chat_stream."""
    interface = CLIInterface(mock_alfred)

    with (
        patch("src.interfaces.cli.PromptSession") as mock_session_cls,
        patch("sys.stdout", StringIO()),
    ):
        mock_session_cls.return_value = make_mock_session(["Hello", "exit"])
        await interface.run()

    mock_alfred.chat_stream.assert_called_once()
    call_args = mock_alfred.chat_stream.call_args
    assert call_args[0][0] == "Hello"
    assert "tool_callback" in call_args[1]


@pytest.mark.asyncio
async def test_compact_delegates_to_alfred(mock_alfred: MagicMock) -> None:
    """Test that CLI delegates compact to Alfred."""
    interface = CLIInterface(mock_alfred)

    with (
        patch("src.interfaces.cli.PromptSession") as mock_session_cls,
        patch("sys.stdout", StringIO()),
    ):
        mock_session_cls.return_value = make_mock_session(["compact", "exit"])
        await interface.run()

    mock_alfred.compact.assert_called_once()


@pytest.mark.asyncio
async def test_exit_terminates_loop(mock_alfred: MagicMock) -> None:
    """Test that 'exit' command terminates the loop."""
    interface = CLIInterface(mock_alfred)

    with (
        patch("src.interfaces.cli.PromptSession") as mock_session_cls,
        patch("sys.stdout", StringIO()),
    ):
        mock_session_cls.return_value = make_mock_session(["exit"])
        await interface.run()

    # Should not call chat_stream
    mock_alfred.chat_stream.assert_not_called()


@pytest.mark.asyncio
async def test_empty_input_ignored(mock_alfred: MagicMock) -> None:
    """Test that empty input is ignored."""
    interface = CLIInterface(mock_alfred)

    with (
        patch("src.interfaces.cli.PromptSession") as mock_session_cls,
        patch("sys.stdout", StringIO()),
    ):
        mock_session_cls.return_value = make_mock_session(["", "", "Hello", "exit"])
        await interface.run()

    # Only one chat_stream call for "Hello"
    mock_alfred.chat_stream.assert_called_once()
    call_args = mock_alfred.chat_stream.call_args
    assert call_args[0][0] == "Hello"


@pytest.mark.asyncio
async def test_eof_terminates_loop(mock_alfred: MagicMock) -> None:
    """Test that EOF terminates the loop gracefully."""
    interface = CLIInterface(mock_alfred)

    with patch("src.interfaces.cli.PromptSession") as mock_session_cls:
        mock_session = MagicMock()
        mock_session.prompt_async = AsyncMock(side_effect=EOFError)
        mock_session_cls.return_value = mock_session
        await interface.run()

    # Should not call chat_stream
    mock_alfred.chat_stream.assert_not_called()


@pytest.mark.asyncio
async def test_keyboard_interrupt_terminates_loop(mock_alfred: MagicMock) -> None:
    """Test that KeyboardInterrupt terminates the loop gracefully."""
    interface = CLIInterface(mock_alfred)

    with (
        patch("src.interfaces.cli.PromptSession") as mock_session_cls,
        patch("sys.stdout", StringIO()),
    ):
        mock_session = MagicMock()
        mock_session.prompt_async = AsyncMock(side_effect=KeyboardInterrupt)
        mock_session_cls.return_value = mock_session
        await interface.run()

    # Should not call chat_stream
    mock_alfred.chat_stream.assert_not_called()


@pytest.mark.asyncio
async def test_case_insensitive_commands(mock_alfred: MagicMock) -> None:
    """Test that commands are case-insensitive."""
    interface = CLIInterface(mock_alfred)

    with (
        patch("src.interfaces.cli.PromptSession") as mock_session_cls,
        patch("sys.stdout", StringIO()),
    ):
        mock_session_cls.return_value = make_mock_session(["COMPACT", "EXIT"])
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

        interface = CLIInterface(mock_alfred)

        # Create a proper async generator for chat_stream
        async def mock_stream(message: str, **kwargs: object) -> AsyncGenerator[str, None]:
            yield "CLI response"

        mock_alfred.chat_stream = mock_stream

        with (
            patch("src.interfaces.cli.PromptSession") as mock_session_cls,
            patch("src.interfaces.cli.Live") as mock_live,
        ):
            mock_session_cls.return_value = make_mock_session(["Hello", "exit"])
            await interface.run()

        # Live should have been instantiated
        mock_live.assert_called()

    @pytest.mark.asyncio
    async def test_chat_handles_empty_stream(
        self, mock_alfred: MagicMock
    ) -> None:
        """Empty streams are handled gracefully."""

        # Create mock that yields nothing
        async def empty_stream(message: str, **kwargs: object) -> AsyncGenerator[str, None]:
            return
            yield  # pragma: no cover

        mock_alfred.chat_stream = empty_stream

        interface = CLIInterface(mock_alfred)

        with (
            patch("src.interfaces.cli.PromptSession") as mock_session_cls,
            patch("src.interfaces.cli.Live") as mock_live,
        ):
            mock_session_cls.return_value = make_mock_session(["Hello", "exit"])
            await interface.run()

        # Live should still be called even with empty stream
        mock_live.assert_called()
