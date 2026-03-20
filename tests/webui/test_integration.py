"""Integration tests for Alfred Web UI using Playwright.

These tests run the full stack (FastAPI server + real browser) to catch
bugs that unit tests miss, like:
- Empty message handling
- WebSocket connection issues
- Frontend state management bugs
- Race conditions in UI updates
"""

from __future__ import annotations

import asyncio
import subprocess
import time
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from playwright.async_api import Page


pytestmark = pytest.mark.playwright


@pytest.fixture(scope="module")
def server_port() -> int:
    """Get a free port for the test server."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server_url(server_port: int) -> str:
    """Get the server URL."""
    return f"http://127.0.0.1:{server_port}"


@pytest.fixture(scope="module")
def server_process(server_port: int):
    """Start the Alfred Web UI server as a subprocess.

    Yields the process handle and kills it after tests complete.
    """
    import os
    import tempfile

    # Create a temporary directory for test data
    temp_dir = tempfile.mkdtemp(prefix="alfred_test_")

    # Set environment variables for test isolation
    env = os.environ.copy()
    env["XDG_DATA_HOME"] = os.path.join(temp_dir, "data")
    env["XDG_CONFIG_HOME"] = os.path.join(temp_dir, "config")
    env["XDG_STATE_HOME"] = os.path.join(temp_dir, "state")

    # Start server with test config - use a simpler approach
    server_code = f'''
import asyncio
import sys
sys.path.insert(0, "/workspace/alfred-prd/src")

async def main():
    from alfred.alfred import Alfred
    from alfred.config import load_config
    from alfred.data_manager import init_xdg_directories
    from alfred.interfaces.webui.server import create_app
    import uvicorn

    # Initialize Alfred
    init_xdg_directories()
    config = load_config()
    alfred = Alfred(config, telegram_mode=False)
    await alfred.start()

    # Create app and run server
    app = create_app(alfred_instance=alfred)
    config = uvicorn.Config(app, host="127.0.0.1", port={server_port}, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
'''

    process = subprocess.Popen(
        ["python", "-c", server_code],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    # Wait for server to start
    max_retries = 60
    for i in range(max_retries):
        try:
            import socket

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                s.connect(("127.0.0.1", server_port))
                break
        except (ConnectionRefusedError, socket.timeout, OSError):
            if i == max_retries - 1:
                process.terminate()
                stdout, stderr = process.communicate(timeout=5)
                raise RuntimeError(
                    f"Server failed to start.\nstdout: {stdout.decode()}\nstderr: {stderr.decode()}"
                )
            time.sleep(0.5)

    yield process

    # Cleanup
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()

    # Clean up temp directory
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
async def page(page: Page, server_process, server_url: str) -> Page:
    """Navigate to the webui page before each test."""
    await page.goto(server_url)
    # Wait for WebSocket connection
    await page.wait_for_selector("[data-testid='connection-status']", state="visible")
    return page


@pytest.mark.asyncio
async def test_page_loads_and_shows_chat_interface(page: Page) -> None:
    """Test that the page loads and shows the chat interface."""
    # Check title
    title = await page.title()
    assert "Alfred" in title

    # Check chat container exists
    chat_container = await page.query_selector("#chat-container")
    assert chat_container is not None

    # Check input field exists
    input_field = await page.query_selector("#message-input")
    assert input_field is not None


@pytest.mark.asyncio
async def test_empty_message_shows_error(page: Page) -> None:
    """Test that sending an empty message shows an error."""
    # Clear input and try to send empty message
    input_field = page.locator("#message-input")
    await input_field.fill("")

    # Click send button
    send_button = page.locator("#send-button")
    await send_button.click()

    # Wait for error message
    error_message = page.locator(".error-message")
    await error_message.wait_for(state="visible", timeout=2000)

    error_text = await error_message.text_content()
    assert "empty" in error_text.lower() or "cannot" in error_text.lower()


@pytest.mark.asyncio
async def test_whitespace_only_message_shows_error(page: Page) -> None:
    """Test that sending only whitespace shows an error."""
    input_field = page.locator("#message-input")
    await input_field.fill("   \n\t  ")

    send_button = page.locator("#send-button")
    await send_button.click()

    # Wait for error message
    error_message = page.locator(".error-message")
    await error_message.wait_for(state="visible", timeout=2000)


@pytest.mark.asyncio
async def test_chat_message_flow(page: Page) -> None:
    """Test sending a message and receiving a response.

    This is a basic smoke test - it will fail without a real LLM API key,
    but we can mock the chat_stream method if needed.
    """
    # Skip if no API key is available
    import os

    if not os.getenv("KIMI_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        pytest.skip("No LLM API key available")

    input_field = page.locator("#message-input")
    await input_field.fill("Hello, this is a test message")

    send_button = page.locator("#send-button")
    await send_button.click()

    # Wait for user message to appear
    user_message = page.locator(".chat-message.user")
    await user_message.wait_for(state="visible", timeout=5000)

    # Wait for assistant response to start
    assistant_message = page.locator(".chat-message.assistant")
    await assistant_message.wait_for(state="visible", timeout=30000)


@pytest.mark.asyncio
async def test_websocket_reconnection(page: Page, server_url: str) -> None:
    """Test that WebSocket reconnects after connection drop."""
    # Get initial connection status
    status_indicator = page.locator("[data-testid='connection-status']")
    initial_status = await status_indicator.get_attribute("data-status")
    assert initial_status == "connected"

    # Simulate connection drop by executing JavaScript
    await page.evaluate("""
        if (window.wsClient && window.wsClient.ws) {
            window.wsClient.ws.close();
        }
    """)

    # Wait for disconnected state
    await page.wait_for_selector(
        "[data-testid='connection-status'][data-status='disconnected']",
        timeout=5000,
    )

    # Wait for reconnection
    await page.wait_for_selector(
        "[data-testid='connection-status'][data-status='connected']",
        timeout=10000,
    )


@pytest.mark.asyncio
async def test_command_completion_shows_on_slash(page: Page) -> None:
    """Test that typing '/' shows command completion menu."""
    input_field = page.locator("#message-input")
    await input_field.fill("/")

    # Wait for completion menu
    completion_menu = page.locator("#completion-menu")
    await completion_menu.wait_for(state="visible", timeout=2000)

    # Check that commands are shown
    items = await page.query_selector_all(".completion-item")
    assert len(items) > 0

    # Check for expected commands
    texts = [await item.text_content() for item in items]
    assert any("/new" in t for t in texts if t)
    assert any("/help" in t for t in texts if t)


@pytest.mark.asyncio
async def test_command_completion_navigation(page: Page) -> None:
    """Test keyboard navigation in command completion menu."""
    input_field = page.locator("#message-input")
    await input_field.fill("/")

    # Wait for completion menu
    completion_menu = page.locator("#completion-menu")
    await completion_menu.wait_for(state="visible", timeout=2000)

    # Press down arrow
    await page.keyboard.press("ArrowDown")

    # Check first item is highlighted
    first_item = page.locator(".completion-item.selected")
    await first_item.wait_for(state="visible", timeout=1000)

    # Press Enter to select
    await page.keyboard.press("Enter")

    # Check input field has the command
    value = await input_field.input_value()
    assert value.startswith("/")


@pytest.mark.asyncio
async def test_escape_closes_completion_menu(page: Page) -> None:
    """Test that Escape key closes the completion menu."""
    input_field = page.locator("#message-input")
    await input_field.fill("/")

    # Wait for completion menu
    completion_menu = page.locator("#completion-menu")
    await completion_menu.wait_for(state="visible", timeout=2000)

    # Press Escape
    await page.keyboard.press("Escape")

    # Check menu is hidden
    await completion_menu.wait_for(state="hidden", timeout=2000)


@pytest.mark.asyncio
async def test_shift_enter_queues_message(page: Page) -> None:
    """Test that Shift+Enter queues a message instead of sending."""
    input_field = page.locator("#message-input")
    await input_field.fill("First queued message")

    # Press Shift+Enter
    await page.keyboard.press("Shift+Enter")

    # Check message is still in input (queued, not sent)
    value = await input_field.input_value()
    # Input should be cleared after queueing

    # Check queue indicator shows 1
    queue_badge = page.locator("#queue-count")
    await queue_badge.wait_for(state="visible", timeout=2000)
    count = await queue_badge.text_content()
    assert count == "1"


@pytest.mark.asyncio
async def test_ctrl_t_toggles_tool_calls(page: Page) -> None:
    """Test that Ctrl+T toggles tool call visibility."""
    # First, we'd need a tool call to be rendered
    # For now, just test the keyboard shortcut works

    # Press Ctrl+T
    await page.keyboard.press("Control+t")

    # This would check tool call state if we had any
    # Just ensure no errors occur
    await asyncio.sleep(0.5)


@pytest.mark.asyncio
async def test_new_session_command_creates_new_session(page: Page) -> None:
    """Test that /new command creates a new session."""
    input_field = page.locator("#message-input")
    await input_field.fill("/new")

    send_button = page.locator("#send-button")
    await send_button.click()

    # Wait for system message
    system_message = page.locator(".chat-message.system")
    await system_message.wait_for(state="visible", timeout=5000)

    # Check for session-related text
    text = await system_message.text_content()
    assert "session" in text.lower() or "new" in text.lower()


@pytest.mark.asyncio
async def test_message_history_navigation(page: Page) -> None:
    """Test UP/DOWN arrow navigation through message history."""
    # Send a message first
    input_field = page.locator("#message-input")
    await input_field.fill("Test message for history")

    send_button = page.locator("#send-button")
    await send_button.click()

    # Wait for message to be sent
    await page.wait_for_timeout(500)

    # Press UP to recall message
    await input_field.focus()
    await page.keyboard.press("ArrowUp")

    # Check input has the previous message
    value = await input_field.input_value()
    assert "Test message" in value


@pytest.mark.asyncio
async def test_chat_container_auto_scrolls(page: Page) -> None:
    """Test that chat container auto-scrolls to new messages."""
    # Send multiple messages to create scroll
    for i in range(5):
        input_field = page.locator("#message-input")
        await input_field.fill(f"Test message {i}")

        send_button = page.locator("#send-button")
        await send_button.click()

        await page.wait_for_timeout(300)

    # Check scroll position is at bottom
    scroll_position = await page.evaluate("""
        const container = document.getElementById('chat-container');
        return container.scrollHeight - container.scrollTop - container.clientHeight;
    """)

    # Should be close to 0 (at bottom)
    assert scroll_position < 50


@pytest.mark.asyncio
async def test_connection_status_indicator(page: Page) -> None:
    """Test that connection status indicator is visible and updates."""
    status_indicator = page.locator("[data-testid='connection-status']")

    # Should be visible
    assert await status_indicator.is_visible()

    # Should show connected status
    status = await status_indicator.get_attribute("data-status")
    assert status == "connected"


@pytest.mark.asyncio
async def test_server_health_endpoint(server_url: str) -> None:
    """Test that health endpoint returns OK."""
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{server_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


@pytest.mark.asyncio
async def test_static_files_served(server_url: str) -> None:
    """Test that static files are served correctly."""
    import httpx

    async with httpx.AsyncClient() as client:
        # Test CSS
        response = await client.get(f"{server_url}/static/css/base.css")
        assert response.status_code == 200
        assert "text/css" in response.headers.get("content-type", "")

        # Test JS
        response = await client.get(f"{server_url}/static/js/main.js")
        assert response.status_code == 200
        assert "javascript" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_websocket_echo(server_url: str) -> None:
    """Test WebSocket connection and basic message handling."""
    import websockets
    import json

    ws_url = server_url.replace("http://", "ws://") + "/ws"

    async with websockets.connect(ws_url) as websocket:
        # Wait for connected message
        response = await websocket.recv()
        data = json.loads(response)
        assert data["type"] == "connected"

        # Send a test message
        await websocket.send(json.dumps({
            "type": "chat.send",
            "payload": {"content": "Test message"}
        }))

        # Should receive either started or error (not crash)
        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
        data = json.loads(response)
        assert data["type"] in ["chat.started", "chat.error"]


@pytest.mark.asyncio
async def test_empty_message_via_websocket(server_url: str) -> None:
    """Test that empty messages are rejected via WebSocket."""
    import websockets
    import json

    ws_url = server_url.replace("http://", "ws://") + "/ws"

    async with websockets.connect(ws_url) as websocket:
        # Wait for connected message
        await websocket.recv()

        # Send empty message
        await websocket.send(json.dumps({
            "type": "chat.send",
            "payload": {"content": "   "}
        }))

        # Should receive error
        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
        data = json.loads(response)
        assert data["type"] == "chat.error"
        assert "empty" in data["payload"]["error"].lower()
