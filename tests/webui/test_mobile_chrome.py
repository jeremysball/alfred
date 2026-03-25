"""Browser tests for mobile chrome collapse behavior."""

import pytest
import re

pytestmark = [pytest.mark.asyncio, pytest.mark.slow]


async def test_header_collapses_on_scroll_down(
    websocket_server, page_helper
):
    """Verify header collapses when scrolling down on mobile."""
    from playwright.async_api import expect

    page = page_helper

    # Set mobile viewport
    await page.set_viewport_size({"width": 375, "height": 667})

    # Wait for WebSocket connection
    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    # Add some messages to make the chat scrollable
    await page.evaluate("""
        () => {
            const messageList = document.getElementById('message-list');
            for (let i = 0; i < 20; i++) {
                const msg = document.createElement('chat-message');
                msg.setAttribute('role', i % 2 === 0 ? 'user' : 'assistant');
                msg.setAttribute('content', 'Test message ' + i);
                msg.setAttribute('message-id', 'msg-' + i);
                messageList.appendChild(msg);
            }
        }
    """)

    # Wait a moment for messages to render
    await page.wait_for_timeout(100)

    # Get initial header state
    header = page.locator(".app-header")
    await expect(header).not_to_have_class(re.compile(r"\bcompact\b"))

    # Scroll down
    await page.evaluate("""
        () => {
            window.scrollTo(0, 100);
        }
    """)

    # Wait for scroll handler
    await page.wait_for_timeout(150)

    # Verify header has hidden class
    await expect(header).to_have_class(re.compile(r"\bcompact\b"))


async def test_header_restores_on_scroll_up(
    websocket_server, page_helper
):
    """Verify header restores when scrolling up on mobile."""
    from playwright.async_api import expect

    page = page_helper

    # Set mobile viewport
    await page.set_viewport_size({"width": 375, "height": 667})

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    # Add scrollable content
    await page.evaluate("""
        () => {
            const messageList = document.getElementById('message-list');
            for (let i = 0; i < 20; i++) {
                const msg = document.createElement('chat-message');
                msg.setAttribute('role', i % 2 === 0 ? 'user' : 'assistant');
                msg.setAttribute('content', 'Test message ' + i);
                msg.setAttribute('message-id', 'msg-' + i);
                messageList.appendChild(msg);
            }
        }
    """)

    await page.wait_for_timeout(100)

    # Scroll down first
    await page.evaluate("""
        () => {
            const chatContainer = document.getElementById('chat-container');
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    """)
    await page.wait_for_timeout(150)

    # Verify hidden
    header = page.locator(".app-header")
    await expect(header).to_have_class(re.compile(r"\bcompact\b"))

    # Scroll up
    await page.evaluate("""
        () => {
            window.scrollTo(0, 0);
        }
    """)
    await page.wait_for_timeout(150)

    # Verify restored (not hidden)
    await expect(header).not_to_have_class(re.compile(r"\bcompact\b"))


async def test_header_restores_on_composer_focus(
    websocket_server, page_helper
):
    """Verify header restores when focusing the composer on mobile."""
    from playwright.async_api import expect

    page = page_helper

    # Set mobile viewport
    await page.set_viewport_size({"width": 375, "height": 667})

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    # Add scrollable content
    await page.evaluate("""
        () => {
            const messageList = document.getElementById('message-list');
            for (let i = 0; i < 20; i++) {
                const msg = document.createElement('chat-message');
                msg.setAttribute('role', i % 2 === 0 ? 'user' : 'assistant');
                msg.setAttribute('content', 'Test message ' + i);
                msg.setAttribute('message-id', 'msg-' + i);
                messageList.appendChild(msg);
            }
        }
    """)

    await page.wait_for_timeout(100)

    # Scroll down to collapse
    await page.evaluate("""
        () => {
            const chatContainer = document.getElementById('chat-container');
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    """)
    await page.wait_for_timeout(150)

    # Verify hidden
    header = page.locator(".app-header")
    await expect(header).to_have_class(re.compile(r"\bcompact\b"))

    # Focus the composer by clicking
    await page.click("#message-input")
    await page.wait_for_timeout(300)

    # Verify restored (not hidden)
    await expect(header).not_to_have_class(re.compile(r"\bcompact\b"))


async def test_compact_mode_hides_non_essential_header_elements(
    websocket_server, page_helper
):
    """Verify compact mode hides non-essential header elements."""
    from playwright.async_api import expect

    page = page_helper

    # Set mobile viewport
    await page.set_viewport_size({"width": 375, "height": 667})

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    # Add scrollable content
    await page.evaluate("""
        () => {
            const messageList = document.getElementById('message-list');
            for (let i = 0; i < 20; i++) {
                const msg = document.createElement('chat-message');
                msg.setAttribute('role', i % 2 === 0 ? 'user' : 'assistant');
                msg.setAttribute('content', 'Test message ' + i);
                msg.setAttribute('message-id', 'msg-' + i);
                messageList.appendChild(msg);
            }
        }
    """)

    await page.wait_for_timeout(100)

    # Scroll down
    await page.evaluate("""
        () => {
            window.scrollTo(0, 100);
        }
    """)
    await page.wait_for_timeout(150)

    # Verify header is hidden
    header = page.locator(".app-header")
    await expect(header).to_have_class(re.compile(r"\bcompact\b"))

    # Verify header status is hidden in compact mode
    header_status = header.locator(".header-status")
    await expect(header_status).not_to_be_visible()


async def test_compact_input_area_hides_buttons(
    websocket_server, page_helper
):
    """Verify hidden input area hides buttons."""
    from playwright.async_api import expect

    page = page_helper

    # Set mobile viewport
    await page.set_viewport_size({"width": 375, "height": 667})

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    # Add scrollable content
    await page.evaluate("""
        () => {
            const messageList = document.getElementById('message-list');
            for (let i = 0; i < 20; i++) {
                const msg = document.createElement('chat-message');
                msg.setAttribute('role', i % 2 === 0 ? 'user' : 'assistant');
                msg.setAttribute('content', 'Test message ' + i);
                msg.setAttribute('message-id', 'msg-' + i);
                messageList.appendChild(msg);
            }
        }
    """)

    await page.wait_for_timeout(100)

    # Scroll down
    await page.evaluate("""
        () => {
            window.scrollTo(0, 100);
        }
    """)
    await page.wait_for_timeout(150)

    # Verify input area is hidden (mobile scroll behavior)
    input_area = page.locator("#input-area")
    await expect(input_area).to_have_class(re.compile(r"\bcompact\b"))


async def test_stop_button_visible_during_streaming_in_compact_mode(
    websocket_server, page_helper
):
    """Verify stop button remains visible during streaming even in compact mode."""
    from playwright.async_api import expect

    page = page_helper

    # Set mobile viewport
    await page.set_viewport_size({"width": 375, "height": 667})

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    # Add scrollable content and set streaming state
    await page.evaluate("""
        () => {
            const messageList = document.getElementById('message-list');
            for (let i = 0; i < 20; i++) {
                const msg = document.createElement('chat-message');
                msg.setAttribute('role', i % 2 === 0 ? 'user' : 'assistant');
                msg.setAttribute('content', 'Test message ' + i);
                msg.setAttribute('message-id', 'msg-' + i);
                messageList.appendChild(msg);
            }

            // Set streaming state
            const inputArea = document.getElementById('input-area');
            inputArea.dataset.composerState = 'streaming';

            // Show stop button
            const stopButton = document.getElementById('stop-button');
            if (stopButton) {
                stopButton.hidden = false;
            }
        }
    """)

    await page.wait_for_timeout(100)

    # Scroll down to hide chrome
    await page.evaluate("""
        () => {
            const chatContainer = document.getElementById('chat-container');
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    """)
    await page.wait_for_timeout(150)

    # Verify input area is hidden on scroll (mobile behavior)
    input_area = page.locator("#input-area")
    await expect(input_area).to_have_class(re.compile(r"\bcompact\b"))
    await expect(input_area).to_have_attribute("data-composer-state", "streaming")


async def test_history_buttons_hidden_during_streaming_on_mobile(
    websocket_server, page_helper
):
    """Verify history buttons are hidden during streaming on mobile."""
    from playwright.async_api import expect

    page = page_helper

    # Set mobile viewport
    await page.set_viewport_size({"width": 375, "height": 667})

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    # Set streaming state
    await page.evaluate("""
        () => {
            const inputArea = document.getElementById('input-area');
            inputArea.dataset.composerState = 'streaming';
        }
    """)

    # Verify history buttons are hidden during streaming
    input_area = page.locator("#input-area")
    history_up = input_area.locator("#history-up")
    history_down = input_area.locator("#history-down")
    await expect(history_up).not_to_be_visible()
    await expect(history_down).not_to_be_visible()


async def test_compact_mode_not_applied_on_desktop(
    websocket_server, page_helper
):
    """Verify compact mode is not applied on desktop viewport."""
    from playwright.async_api import expect

    page = page_helper

    # Set desktop viewport
    await page.set_viewport_size({"width": 1024, "height": 768})

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000
    )

    # Add scrollable content
    await page.evaluate("""
        () => {
            const messageList = document.getElementById('message-list');
            for (let i = 0; i < 20; i++) {
                const msg = document.createElement('chat-message');
                msg.setAttribute('role', i % 2 === 0 ? 'user' : 'assistant');
                msg.setAttribute('content', 'Test message ' + i);
                msg.setAttribute('message-id', 'msg-' + i);
                messageList.appendChild(msg);
            }
        }
    """)

    await page.wait_for_timeout(100)

    # Scroll down
    await page.evaluate("""
        () => {
            window.scrollTo(0, 100);
        }
    """)
    await page.wait_for_timeout(150)

    # Verify header is NOT hidden on desktop
    header = page.locator(".app-header")
    await expect(header).not_to_have_class(re.compile(r"\bcompact\b"))

    # Verify input area is NOT hidden
    input_area = page.locator("#input-area")
    await expect(input_area).not_to_have_class(re.compile(r"\bcompact\b"))
