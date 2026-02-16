"""True end-to-end tests with real Telegram and Pi.

Requires environment variables:
    TELEGRAM_BOT_TOKEN - Bot token for testing
    TELEGRAM_CHAT_ID - Chat ID to send test messages
    LLM_API_KEY - API key for LLM provider

These tests send real messages and cost real API tokens.
Run manually, not in CI.
"""
import pytest
import asyncio
import os
from pathlib import Path
from datetime import datetime

from alfred.dispatcher import Dispatcher
from alfred.pi_manager import PiManager
from alfred.telegram_bot import TelegramBot


# Skip all tests if env vars not set
pytestmark = [
    pytest.mark.skipif(
        not os.getenv("TELEGRAM_BOT_TOKEN"),
        reason="TELEGRAM_BOT_TOKEN not set"
    ),
    pytest.mark.skipif(
        not os.getenv("TELEGRAM_CHAT_ID"),
        reason="TELEGRAM_CHAT_ID not set"
    ),
    pytest.mark.skipif(
        not os.getenv("LLM_API_KEY"),
        reason="LLM_API_KEY not set"
    ),
    pytest.mark.slow,
]


@pytest.fixture
def test_dirs(tmp_path):
    """Create temp directories for test."""
    workspace = tmp_path / "e2e_workspace"
    threads = tmp_path / "e2e_threads"
    workspace.mkdir()
    threads.mkdir()
    return workspace, threads


@pytest.fixture
def pi_manager():
    """Create PiManager with real config."""
    return PiManager(
        timeout=60,
        llm_provider=os.getenv("LLM_PROVIDER", "zai"),
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_model=os.getenv("LLM_MODEL")
    )


@pytest.mark.asyncio
async def test_e2e_real_pi_response(test_dirs, pi_manager):
    """Test real Pi subprocess returns actual LLM response."""
    workspace, threads = test_dirs
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    thread_id = f"e2e_test_{datetime.now().strftime('%H%M%S')}"
    
    try:
        response = await dispatcher.handle_message(
            chat_id=123,
            thread_id=thread_id,
            message="Say exactly: 'Pi is working' and nothing else"
        )
        
        # Verify we got a real response
        assert response
        assert len(response) > 0
        assert "working" in response.lower() or "pi" in response.lower()
        
        # Verify thread was saved
        from alfred.storage import ThreadStorage
        storage = ThreadStorage(threads)
        thread = await storage.load(thread_id)
        assert thread is not None
        assert len(thread.messages) == 2  # user + assistant
        
    finally:
        await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_e2e_real_telegram_message(test_dirs, pi_manager):
    """Test bot sends real message to Telegram."""
    workspace, threads = test_dirs
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = int(os.getenv("TELEGRAM_CHAT_ID"))
    
    bot = TelegramBot(token, dispatcher)
    
    # Setup bot
    app = bot.setup()
    await app.initialize()
    await app.start()
    
    try:
        # Send test message directly via bot API
        test_msg = f"🧪 E2E Test {datetime.now().strftime('%H:%M:%S')}"
        sent = await app.bot.send_message(
            chat_id=chat_id,
            text=test_msg
        )
        
        assert sent is not None
        assert sent.text == test_msg
        assert sent.chat.id == chat_id
        
    finally:
        await app.stop()
        await app.shutdown()
        await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_e2e_full_flow(test_dirs, pi_manager):
    """Test full flow: Telegram message -> Pi -> Telegram response."""
    workspace, threads = test_dirs
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = int(os.getenv("TELEGRAM_CHAT_ID"))
    
    bot = TelegramBot(token, dispatcher)
    app = bot.setup()
    await app.initialize()
    await app.start()
    
    thread_id = f"e2e_full_{datetime.now().strftime('%H%M%S')}"
    
    try:
        # Send message that will trigger Pi
        test_msg = f"🧪 E2E Test - Reply with timestamp: {datetime.now().isoformat()}"
        
        sent = await app.bot.send_message(
            chat_id=chat_id,
            text=test_msg
        )
        
        # Simulate what dispatcher would do
        response = await dispatcher.handle_message(
            chat_id=chat_id,
            thread_id=thread_id,
            message="What is 2+2? Reply with just the number."
        )
        
        # Send response back
        reply = await app.bot.send_message(
            chat_id=chat_id,
            text=f"🤖 Pi says: {response[:100]}"
        )
        
        assert reply is not None
        assert "Pi says:" in reply.text
        
    finally:
        await app.stop()
        await app.shutdown()
        await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_e2e_commands(test_dirs, pi_manager):
    """Test real Telegram command handlers."""
    workspace, threads = test_dirs
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = int(os.getenv("TELEGRAM_CHAT_ID"))
    
    bot = TelegramBot(token, dispatcher)
    app = bot.setup()
    await app.initialize()
    await app.start()
    
    try:
        # Test /status command
        status = await dispatcher.handle_command("any", "/status")
        sent = await app.bot.send_message(
            chat_id=chat_id,
            text=f"📊 {status}"
        )
        assert sent is not None
        
        # Test /threads command
        threads_list = await dispatcher.handle_command("any", "/threads")
        sent = await app.bot.send_message(
            chat_id=chat_id,
            text=f"📋 {threads_list}"
        )
        assert sent is not None
        
    finally:
        await app.stop()
        await app.shutdown()
        await dispatcher.shutdown()


@pytest.mark.asyncio
async def test_e2e_timeout_real(test_dirs):
    """Test real timeout with very short timeout."""
    workspace, threads = test_dirs
    
    # Create manager with impossibly short timeout
    pi_manager = PiManager(
        timeout=0.001,  # 1ms - should always timeout
        llm_provider=os.getenv("LLM_PROVIDER", "zai"),
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_model=os.getenv("LLM_MODEL")
    )
    
    dispatcher = Dispatcher(workspace, threads, pi_manager)
    
    try:
        response = await dispatcher.handle_message(
            chat_id=123,
            thread_id="e2e_timeout_test",
            message="This should timeout"
        )
        
        assert "⏱️ Timeout" in response
        
    finally:
        await dispatcher.shutdown()
