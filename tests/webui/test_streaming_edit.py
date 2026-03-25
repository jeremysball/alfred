"""Browser tests for message editing functionality."""

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.slow]


async def test_pencil_button_visible_on_last_user_message(
    websocket_server, page_helper
):
    """Verify pencil button appears on the last user message."""
    from playwright.async_api import expect

    page = await page_helper(websocket_server)

    # Wait for WebSocket connection
    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    # Mock adding a user message
    await page.evaluate("""
        () => {
            const messageList = document.getElementById('message-list');
            const userMsg = document.createElement('chat-message');
            userMsg.setAttribute('role', 'user');
            userMsg.setAttribute('content', 'Test message');
            userMsg.setAttribute('message-id', 'test-msg-1');
            userMsg.setAttribute('editable', 'true');
            messageList.appendChild(userMsg);
        }
    """)

    # Verify pencil button is visible
    pencil_button = page.locator("chat-message[role='user'] [data-action='edit']")
    await expect(pencil_button).to_be_visible()
    await expect(pencil_button).to_have_attribute("aria-label", "Edit message")


async def test_pencil_button_hidden_when_not_editable(
    websocket_server, page_helper
):
    """Verify pencil button is hidden when message is not editable."""
    from playwright.async_api import expect

    page = await page_helper(websocket_server)

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    # Add a user message without editable attribute
    await page.evaluate("""
        () => {
            const messageList = document.getElementById('message-list');
            const userMsg = document.createElement('chat-message');
            userMsg.setAttribute('role', 'user');
            userMsg.setAttribute('content', 'Test message');
            userMsg.setAttribute('message-id', 'test-msg-2');
            // No editable attribute
            messageList.appendChild(userMsg);
        }
    """)

    # Verify pencil button is not visible
    pencil_button = page.locator("chat-message[message-id='test-msg-2'] [data-action='edit']")
    await expect(pencil_button).to_have_count(0)


async def test_pencil_button_hidden_on_assistant_messages(
    websocket_server, page_helper
):
    """Verify pencil button does not appear on assistant messages."""
    from playwright.async_api import expect

    page = await page_helper(websocket_server)

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    # Add an assistant message
    await page.evaluate("""
        () => {
            const messageList = document.getElementById('message-list');
            const assistantMsg = document.createElement('chat-message');
            assistantMsg.setAttribute('role', 'assistant');
            assistantMsg.setAttribute('content', 'Assistant response');
            assistantMsg.setAttribute('message-id', 'test-msg-3');
            messageList.appendChild(assistantMsg);
        }
    """)

    # Verify pencil button is not present
    pencil_button = page.locator("chat-message[role='assistant'] [data-action='edit']")
    await expect(pencil_button).to_have_count(0)


async def test_click_pencil_prefills_composer(
    websocket_server, page_helper
):
    """Verify clicking pencil prefills the composer with message content."""
    from playwright.async_api import expect

    page = await page_helper(websocket_server)

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    # Add a user message
    await page.evaluate("""
        () => {
            const messageList = document.getElementById('message-list');
            const userMsg = document.createElement('chat-message');
            userMsg.setAttribute('role', 'user');
            userMsg.setAttribute('content', 'Message to edit');
            userMsg.setAttribute('message-id', 'test-msg-4');
            userMsg.setAttribute('editable', 'true');
            messageList.appendChild(userMsg);
        }
    """)

    # Click the pencil button
    await page.click("chat-message[message-id='test-msg-4'] [data-action='edit']")

    # Verify composer is prefilled
    message_input = page.locator("#message-input")
    await expect(message_input).to_have_value("Message to edit")


async def test_edit_mode_sets_composer_state(
    websocket_server, page_helper
):
    """Verify edit mode sets data-composer-state to editing."""
    from playwright.async_api import expect

    page = await page_helper(websocket_server)

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    # Add a user message
    await page.evaluate("""
        () => {
            const messageList = document.getElementById('message-list');
            const userMsg = document.createElement('chat-message');
            userMsg.setAttribute('role', 'user');
            userMsg.setAttribute('content', 'Test content');
            userMsg.setAttribute('message-id', 'test-msg-5');
            userMsg.setAttribute('editable', 'true');
            messageList.appendChild(userMsg);
        }
    """)

    # Click the pencil button
    await page.click("chat-message[message-id='test-msg-5'] [data-action='edit']")

    # Verify composer state
    input_area = page.locator("#input-area")
    await expect(input_area).to_have_attribute("data-composer-state", "editing")


async def test_edit_mode_highlights_message(
    websocket_server, page_helper
):
    """Verify the message being edited gets a visual highlight."""
    from playwright.async_api import expect

    page = await page_helper(websocket_server)

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    # Add a user message
    await page.evaluate("""
        () => {
            const messageList = document.getElementById('message-list');
            const userMsg = document.createElement('chat-message');
            userMsg.setAttribute('role', 'user');
            userMsg.setAttribute('content', 'Test content');
            userMsg.setAttribute('message-id', 'test-msg-6');
            userMsg.setAttribute('editable', 'true');
            messageList.appendChild(userMsg);
        }
    """)

    # Click the pencil button
    await page.click("chat-message[message-id='test-msg-6'] [data-action='edit']")

    # Verify message has editing state
    message = page.locator("chat-message[message-id='test-msg-6']")
    await expect(message).to_have_attribute("data-message-state", "editing")


async def test_edit_placeholder_shows_cancel_hint(
    websocket_server, page_helper
):
    """Verify placeholder shows 'Esc to cancel' hint when editing."""
    from playwright.async_api import expect

    page = await page_helper(websocket_server)

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    # Add a user message
    await page.evaluate("""
        () => {
            const messageList = document.getElementById('message-list');
            const userMsg = document.createElement('chat-message');
            userMsg.setAttribute('role', 'user');
            userMsg.setAttribute('content', 'Test');
            userMsg.setAttribute('message-id', 'test-msg-7');
            userMsg.setAttribute('editable', 'true');
            messageList.appendChild(userMsg);
        }
    """)

    # Click the pencil button
    await page.click("chat-message[message-id='test-msg-7'] [data-action='edit']")

    # Verify placeholder
    message_input = page.locator("#message-input")
    await expect(message_input).to_have_attribute(
        "placeholder",
        "Editing message... (Esc to cancel)"
    )


async def test_esc_cancels_edit_mode(
    websocket_server, page_helper
):
    """Verify pressing Esc cancels edit mode."""
    from playwright.async_api import expect

    page = await page_helper(websocket_server)

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    # Add a user message and enter edit mode
    await page.evaluate("""
        () => {
            const messageList = document.getElementById('message-list');
            const userMsg = document.createElement('chat-message');
            userMsg.setAttribute('role', 'user');
            userMsg.setAttribute('content', 'Test content');
            userMsg.setAttribute('message-id', 'test-msg-8');
            userMsg.setAttribute('editable', 'true');
            messageList.appendChild(userMsg);
        }
    """)

    # Enter edit mode
    await page.click("chat-message[message-id='test-msg-8'] [data-action='edit']")

    # Verify we're in edit mode
    input_area = page.locator("#input-area")
    await expect(input_area).to_have_attribute("data-composer-state", "editing")

    # Press Escape
    await page.keyboard.press("Escape")

    # Verify we're back to idle
    await expect(input_area).to_have_attribute("data-composer-state", "idle")


async def test_edit_event_dispatched_with_correct_detail(
    websocket_server, page_helper
):
    """Verify edit-message event is dispatched with messageId and content."""
    page = await page_helper(websocket_server)

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    # Track edit events
    await page.evaluate("""
        () => {
            window.__editEvents = [];
            document.addEventListener('edit-message', (e) => {
                window.__editEvents.push({
                    messageId: e.detail.messageId,
                    content: e.detail.content
                });
            });
        }
    """)

    # Add a user message
    await page.evaluate("""
        () => {
            const messageList = document.getElementById('message-list');
            const userMsg = document.createElement('chat-message');
            userMsg.setAttribute('role', 'user');
            userMsg.setAttribute('content', 'Event test content');
            userMsg.setAttribute('message-id', 'event-test-msg');
            userMsg.setAttribute('editable', 'true');
            messageList.appendChild(userMsg);
        }
    """)

    # Click the pencil button
    await page.click("chat-message[message-id='event-test-msg'] [data-action='edit']")

    # Check edit event was dispatched
    edit_events = await page.evaluate("() => window.__editEvents")
    assert len(edit_events) == 1
    assert edit_events[0]["messageId"] == "event-test-msg"
    assert edit_events[0]["content"] == "Event test content"
