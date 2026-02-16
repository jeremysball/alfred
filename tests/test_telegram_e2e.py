"""End-to-end tests simulating Telegram messages."""
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Chat, Message, Update
from telegram.ext import ContextTypes

from alfred.dispatcher import Dispatcher
from alfred.pi_manager import PiManager
from alfred.telegram_bot import TelegramBot


def create_mock_update(text: str, chat_id: int = 123, thread_id: int = None) -> Update:
    """Create a mock Telegram update."""
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = chat_id

    update.message = MagicMock(spec=Message)
    update.message.text = text
    update.message.message_thread_id = thread_id

    return update


def create_mock_context() -> ContextTypes.DEFAULT_TYPE:
    """Create a mock Telegram context."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = AsyncMock()
    context.args = []
    return context


@pytest.mark.asyncio
async def test_e2e_message_flow(tmp_path: Path):
    """Test full message flow: Telegram -> Dispatcher -> Pi -> Response."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()

    pi_manager = PiManager(timeout=5)

    # Proper async mock for send_message
    async def mock_send(thread_id, workspace, message, system_prompt=None):
        await asyncio.sleep(0.01)
        return f"Echo: {message}"

    with patch.object(pi_manager, 'send_message', side_effect=mock_send):
        dispatcher = Dispatcher(workspace, threads, pi_manager)

        response = await dispatcher.handle_message(
            chat_id=123,
            thread_id="123",
            message="Hello Pi"
        )

        assert "Echo: Hello Pi" in response

        await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_e2e_command_status(tmp_path: Path):
    """Test /status command returns thread counts."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()

    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)

    update = create_mock_update("/status")
    update.message.reply_text = AsyncMock()
    context = create_mock_context()

    bot = TelegramBot("fake_token", dispatcher)
    await bot._handle_status(update, context)

    # Check that reply_text was called with status info
    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "Status" in call_args[0][0] or "Version" in call_args[0][0]

    await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_e2e_command_threads_empty(tmp_path: Path):
    """Test /threads command with no threads."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()

    pi_manager = PiManager(timeout=5)
    dispatcher = Dispatcher(workspace, threads, pi_manager)

    update = create_mock_update("/threads")
    update.message.reply_text = AsyncMock()
    context = create_mock_context()

    bot = TelegramBot("fake_token", dispatcher)
    await bot._handle_threads(update, context)

    update.message.reply_text.assert_called_once()
    call_args = update.message.reply_text.call_args
    assert "threads" in call_args[0][0].lower()

    await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_e2e_thread_persistence(tmp_path: Path):
    """Test that messages persist to thread storage."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()

    pi_manager = PiManager(timeout=5)

    # Track call count and return different responses
    call_count = 0
    async def mock_send(thread_id, workspace, message, system_prompt=None):
        nonlocal call_count
        call_count += 1
        return f"Response {call_count}"

    with patch.object(pi_manager, 'send_message', side_effect=mock_send):
        dispatcher = Dispatcher(workspace, threads, pi_manager)

        # Send first message
        await dispatcher.handle_message(123, "thread_1", "Message 1")

        # Send second message
        await dispatcher.handle_message(123, "thread_1", "Message 2")

        # Verify thread was saved with both messages
        from alfred.storage import ThreadStorage
        storage = ThreadStorage(threads)
        thread = await storage.load("thread_1")

        assert thread is not None
        assert len(thread.messages) == 4  # 2 user + 2 assistant
        assert thread.messages[0].content == "Message 1"
        assert thread.messages[2].content == "Message 2"

        await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_e2e_typing_indicator_sent(tmp_path: Path):
    """Test that typing indicator is sent while processing."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()

    pi_manager = PiManager(timeout=5)

    async def mock_send(thread_id, workspace, message, system_prompt=None):
        await asyncio.sleep(0.05)  # Small delay to allow typing indicator
        return "Response"

    with patch.object(pi_manager, 'send_message', side_effect=mock_send):
        dispatcher = Dispatcher(workspace, threads, pi_manager)
        bot = TelegramBot("fake_token", dispatcher)

        update = create_mock_update("Test message")
        context = create_mock_context()

        # Mock the typing indicator to track calls
        typing_calls = []
        async def mock_typing(*args, **kwargs):
            typing_calls.append("typing")

        context.bot.send_chat_action = AsyncMock(side_effect=mock_typing)

        await bot._handle_message(update, context)

        # Should have sent at least one typing action
        assert len(typing_calls) >= 1

        await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_e2e_timeout_handling(tmp_path: Path):
    """Test that timeout returns appropriate error message."""
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    workspace.mkdir()
    threads.mkdir()

    pi_manager = PiManager(timeout=1)  # 1 second timeout

    with patch.object(
        pi_manager, 'send_message',
        side_effect=asyncio.TimeoutError()
    ):
        dispatcher = Dispatcher(workspace, threads, pi_manager)

        response = await dispatcher.handle_message(
            chat_id=123,
            thread_id="123",
            message="Slow message"
        )

        assert "⏱️ Timeout" in response

        await dispatcher.shutdown()
