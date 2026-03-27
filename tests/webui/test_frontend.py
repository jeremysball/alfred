"""Tests for frontend Web Components and WebSocket client."""

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
    assert "websocket-client.js" in content


def test_chat_styles_exist():
    """Verify chat-specific CSS is present."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/css/base.css")
    content = response.text

    # Verify chat-related styles
    assert ".message" in content or "chat" in content.lower()
    assert ".user" in content.lower() or ".assistant" in content.lower()
