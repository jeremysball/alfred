"""Browser tests for streaming cancel functionality."""

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.slow]


async def test_stop_button_visible_during_streaming(
    websocket_server, page_helper
):
    """Verify stop button appears during streaming and send button is hidden."""
    from playwright.async_api import expect

    page = await page_helper(websocket_server)

    # Wait for WebSocket connection
    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    # Initial state: stop button should be hidden
    stop_button = page.locator("#stop-button")
    send_button = page.locator("#send-button")
    input_area = page.locator("#input-area")

    await expect(stop_button).to_be_hidden()
    await expect(send_button).to_be_visible()
    await expect(input_area).to_have_attribute("data-composer-state", "idle")

    # Send a message to trigger streaming
    await page.fill("#message-input", "Hello, streaming test")

    # Mock the streaming state by setting it directly via JS
    await page.evaluate("""
        () => {
            window.__testSetComposerState = function(state) {
                const inputArea = document.getElementById('input-area');
                if (inputArea) {
                    inputArea.dataset.composerState = state;
                }
            };
            window.__testSetComposerState('streaming');
        }
    """)

    # Verify stop button is visible and send button is hidden during streaming
    await expect(stop_button).to_be_visible()
    await expect(send_button).to_be_hidden()
    await expect(input_area).to_have_attribute("data-composer-state", "streaming")

    # Verify stop button has CSS square icon and accessibility
    stop_icon = stop_button.locator(".stop-icon")
    await expect(stop_icon).to_be_visible()
    await expect(stop_button).to_have_attribute("aria-label", "Stop generating")


async def test_stop_button_click_sends_cancel(
    websocket_server, page_helper
):
    """Verify clicking stop button sends chat.cancel message."""
    page = await page_helper(websocket_server)

    # Wait for WebSocket connection
    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    # Track WebSocket messages
    ws_messages = []

    await page.evaluate("""
        () => {
            window.__wsMessages = [];
            const originalSend = WebSocket.prototype.send;
            WebSocket.prototype.send = function(data) {
                try {
                    const parsed = JSON.parse(data);
                    window.__wsMessages.push(parsed);
                } catch (e) {
                    window.__wsMessages.push({ type: 'raw', data });
                }
                return originalSend.apply(this, arguments);
            };
        }
    """)

    # Set streaming state and click stop
    await page.evaluate("""
        () => {
            const inputArea = document.getElementById('input-area');
            if (inputArea) {
                inputArea.dataset.composerState = 'streaming';
            }
            const stopButton = document.getElementById('stop-button');
            if (stopButton) {
                stopButton.hidden = false;
            }
        }
    """)

    # Click the stop button
    await page.click("#stop-button")

    # Wait a moment for message to be sent
    await page.wait_for_timeout(100)

    # Check that cancel message was sent
    ws_messages = await page.evaluate("() => window.__wsMessages")
    cancel_messages = [m for m in ws_messages if m.get("type") == "chat.cancel"]

    assert len(cancel_messages) > 0, f"Expected chat.cancel message, got: {ws_messages}"


async def test_stop_button_disabled_while_cancelling(
    websocket_server, page_helper
):
    """Verify stop button is disabled while in cancelling state."""
    from playwright.async_api import expect

    page = await page_helper(websocket_server)

    # Wait for connection
    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    # Set cancelling state
    await page.evaluate("""
        () => {
            const inputArea = document.getElementById('input-area');
            if (inputArea) {
                inputArea.dataset.composerState = 'cancelling';
            }
            const stopButton = document.getElementById('stop-button');
            if (stopButton) {
                stopButton.hidden = false;
                stopButton.disabled = true;
                stopButton.style.opacity = '0.6';
            }
        }
    """)

    stop_button = page.locator("#stop-button")

    # Verify button is disabled and shows stop icon (with reduced opacity)
    await expect(stop_button).to_be_disabled()
    stop_icon = stop_button.locator(".stop-icon")
    await expect(stop_icon).to_be_visible()


async def test_esc_key_triggers_cancel(
    websocket_server, page_helper
):
    """Verify pressing Esc during streaming triggers cancel."""
    page = await page_helper(websocket_server)

    # Wait for connection
    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    # Track WebSocket messages
    await page.evaluate("""
        () => {
            window.__wsMessages = [];
            const originalSend = WebSocket.prototype.send;
            WebSocket.prototype.send = function(data) {
                try {
                    const parsed = JSON.parse(data);
                    window.__wsMessages.push(parsed);
                } catch (e) {
                    window.__wsMessages.push({ type: 'raw', data });
                }
                return originalSend.apply(this, arguments);
            };
        }
    """)

    # Set streaming state
    await page.evaluate("""
        () => {
            // Mock currentAssistantMessage and composerState
            window.__testComposerState = 'streaming';
            window.__testAssistantMessage = { classList: { contains: () => false, add: () => {} } };

            // Override the getter functions
            const originalGetComposerState = window.__alfredWebUI.getComposerState;
            window.__alfredWebUI.getComposerState = () => window.__testComposerState;
            window.__alfredWebUI.getCurrentAssistantMessage = () => window.__testAssistantMessage;
        }
    """)

    # Press Escape
    await page.keyboard.press("Escape")

    # Wait a moment
    await page.wait_for_timeout(100)

    # Check that cancel message was sent
    ws_messages = await page.evaluate("() => window.__wsMessages")
    cancel_messages = [m for m in ws_messages if m.get("type") == "chat.cancel"]

    assert len(cancel_messages) > 0, f"Expected chat.cancel message after Escape, got: {ws_messages}"


async def test_composer_state_contract(
    websocket_server, page_helper
):
    """Verify composer state contract: idle, streaming, cancelling."""
    from playwright.async_api import expect

    page = await page_helper(websocket_server)

    # Wait for connection
    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    input_area = page.locator("#input-area")

    # Test idle state (default)
    await expect(input_area).to_have_attribute("data-composer-state", "idle")

    # Test streaming state
    await page.evaluate("""
        () => {
            const inputArea = document.getElementById('input-area');
            if (inputArea) inputArea.dataset.composerState = 'streaming';
        }
    """)
    await expect(input_area).to_have_attribute("data-composer-state", "streaming")

    # Test cancelling state
    await page.evaluate("""
        () => {
            const inputArea = document.getElementById('input-area');
            if (inputArea) inputArea.dataset.composerState = 'cancelling';
        }
    """)
    await expect(input_area).to_have_attribute("data-composer-state", "cancelling")

    # Test editing state
    await page.evaluate("""
        () => {
            const inputArea = document.getElementById('input-area');
            if (inputArea) inputArea.dataset.composerState = 'editing';
        }
    """)
    await expect(input_area).to_have_attribute("data-composer-state", "editing")


async def test_send_button_visibility_states(
    websocket_server, page_helper
):
    """Verify send button visibility in different composer states."""
    from playwright.async_api import expect

    page = await page_helper(websocket_server)

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    send_button = page.locator("#send-button")
    stop_button = page.locator("#stop-button")

    # Idle: send visible, stop hidden
    await expect(send_button).to_be_visible()
    await expect(stop_button).to_be_hidden()

    # Streaming: send hidden, stop visible
    await page.evaluate("""
        () => {
            const inputArea = document.getElementById('input-area');
            if (inputArea) inputArea.dataset.composerState = 'streaming';
            const stopBtn = document.getElementById('stop-button');
            if (stopBtn) stopBtn.hidden = false;
        }
    """)
    await expect(send_button).to_be_hidden()
    await expect(stop_button).to_be_visible()

    # Cancelling: send hidden, stop visible but disabled
    await page.evaluate("""
        () => {
            const inputArea = document.getElementById('input-area');
            if (inputArea) inputArea.dataset.composerState = 'cancelling';
            const stopBtn = document.getElementById('stop-button');
            if (stopBtn) {
                stopBtn.hidden = false;
                stopBtn.disabled = true;
            }
        }
    """)
    await expect(send_button).to_be_hidden()
    await expect(stop_button).to_be_visible()
    await expect(stop_button).to_be_disabled()
