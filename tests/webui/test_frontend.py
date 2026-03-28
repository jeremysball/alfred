"""Tests for frontend Web Components and WebSocket client."""

import pytest
from fastapi.testclient import TestClient

from alfred.interfaces.webui import create_app


def test_chat_message_component_exists():
    """Verify chat-message Web Component is served."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/js/components/chat-message.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert b"customElements" in response.content


def test_chat_message_component_renders():
    """Verify chat-message component renders HTML structure."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/js/components/chat-message.js")
    content = response.text

    # Verify it defines a custom element
    assert "class ChatMessage" in content or "chat-message" in content
    assert "customElements.define" in content

    # Verify it handles content/role attributes
    assert "role" in content.lower() or "content" in content.lower()


def test_websocket_client_exists():
    """Verify WebSocket client is served."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/js/websocket-client.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


def test_websocket_client_has_connection_logic():
    """Verify WebSocket client has connection management."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/js/websocket-client.js")
    content = response.text

    # Verify WebSocket connection logic
    assert "WebSocket" in content
    assert "protocol === 'https:' ? 'wss' : 'ws'" in content


def test_chat_message_component_exposes_edit_state_and_websocket_client_helpers():
    """Verify the browser contract hooks are present in the static client assets."""
    app = create_app()
    client = TestClient(app)

    chat_message = client.get("/static/js/components/chat-message.js").text
    websocket_client = client.get("/static/js/websocket-client.js").text
    main_js = client.get("/static/js/main.js").text
    index_html = client.get("/static/index.html").text

    assert "editable" in chat_message
    assert "data-message-state" in chat_message
    assert "message-edited" in chat_message
    assert "setMessageState" in chat_message

    assert "sendCancel" in websocket_client
    assert "sendChatEdit" in websocket_client

    assert "getComposerState" in main_js
    assert "edit-message" in main_js
    assert "dataset.composerState" in main_js

    assert 'data-composer-state="idle"' in index_html
    assert 'chat-message.js?v=' in index_html
    assert 'main.js?v=' in index_html


def test_index_html_has_chat_ui():
    """Verify index.html includes chat panel structure."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/index.html")
    content = response.text

    # Verify chat container exists
    assert 'id="chat-container"' in content or 'class="chat-container"' in content
    # Verify message list exists
    assert 'id="message-list"' in content or 'class="message-list"' in content
    # Verify input area exists
    assert "input" in content.lower()


def test_index_html_includes_components():
    """Verify index.html includes all component scripts."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/index.html")
    content = response.text

    # Verify component scripts are included
    assert "chat-message.js" in content
    assert "session-viewer.js" in content
    # Note: websocket-client.js is imported as an ES module in main.js, not via script tag


def test_command_palette_includes_session_commands():
    """Verify command palette registers session and sessions commands."""
    app = create_app()
    client = TestClient(app)

    main_js = client.get("/static/js/main.js").text

    assert 'id: "view-sessions"' in main_js
    assert 'id: "current-session"' in main_js
    assert 'wsClient.sendCommand("/sessions")' in main_js
    assert 'wsClient.sendCommand("/session")' in main_js


def test_chat_styles_exist():
    """Verify chat-specific CSS is present."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/css/base.css")
    content = response.text

    # Verify chat-related styles
    assert ".message" in content or "chat" in content.lower()
    assert ".user" in content.lower() or ".assistant" in content.lower()


@pytest.mark.asyncio
async def test_leader_popup_shows_legend_and_nested_submenu(websocket_server, page_helper):
    """Verify leader mode shows the full keybind tree (leader-only mode)."""
    from playwright.async_api import expect

    page = page_helper

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    await page.focus("#message-input")
    await page.keyboard.press("Control+s")

    which_key = page.locator(".which-key")
    await expect(which_key).to_be_visible()

    # Verify root-level categories (leader-only mode: all keybinds)
    await expect(which_key).to_contain_text("S")
    await expect(which_key).to_contain_text("Search")
    await expect(which_key).to_contain_text("C")
    await expect(which_key).to_contain_text("Chat")
    await expect(which_key).to_contain_text("M")
    await expect(which_key).to_contain_text("Messages")
    await expect(which_key).to_contain_text("P")
    await expect(which_key).to_contain_text("Palette")
    await expect(which_key).to_contain_text("T")
    await expect(which_key).to_contain_text("Theme")
    await expect(which_key).to_contain_text("H")
    await expect(which_key).to_contain_text("Help")
    await expect(which_key).to_contain_text("X")
    await expect(which_key).to_contain_text("Cancel")
    await expect(which_key).to_contain_text("Esc")

    # Verify popup is within viewport bounds
    box = await which_key.bounding_box()
    assert box is not None
    assert box["y"] >= 0
    assert box["y"] + box["height"] <= await page.evaluate("window.innerHeight")

    # Navigate to Search > Messages
    await page.keyboard.press("S")
    await expect(which_key).to_contain_text("Leader + S")
    await expect(which_key).to_contain_text("M")
    await expect(which_key).to_contain_text("Messages")
    await expect(which_key).to_contain_text("Q")
    await expect(which_key).to_contain_text("Quick Switcher")

    await page.keyboard.press("M")
    await expect(page.locator(".search-overlay")).to_be_visible()

    # Close search and test Help > Keyboard help
    await page.keyboard.press("Escape")
    await page.keyboard.press("Control+s")
    await page.keyboard.press("H")  # Enter Help submenu

    await expect(which_key).to_contain_text("Leader + H")
    await expect(which_key).to_contain_text("Keyboard help")

    await page.keyboard.press("H")  # Open keyboard help
    await page.wait_for_function(
        "() => window.alfredHelpSheet?.sheet?.isOpen === true",
        timeout=5000,
    )
