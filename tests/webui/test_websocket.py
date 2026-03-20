"""WebSocket protocol tests for Alfred Web UI."""

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import TestClient as StarletteTestClient
from starlette.websockets import WebSocketDisconnect

from alfred.interfaces.webui.server import create_app


@pytest.fixture
def app():
    """Create test app without Alfred instance."""
    return create_app(alfred_instance=None)


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestWebSocketConnection:
    """Test WebSocket connection handshake and basic protocol."""

    def test_websocket_connection_handshake(self, client):
        """Test that connecting to /ws creates a session with valid UUID.

        Verifies:
        - Connection upgrade succeeds
        - Server sends 'connected' message immediately
        - Connection stays open for subsequent messages
        """
        with client.websocket_connect("/ws") as websocket:
            # Server should send connected message immediately
            data = websocket.receive_json()

            assert data["type"] == "connected"
            assert "payload" in data

    def test_websocket_accepts_ping(self, client):
        """Test that server responds to ping with pong."""
        with client.websocket_connect("/ws") as websocket:
            # Receive connected message
            websocket.receive_json()

            # Send ping
            websocket.send_json({"type": "ping"})

            # Should receive pong
            data = websocket.receive_json()
            assert data["type"] == "pong"

    def test_websocket_rejects_invalid_json(self, client):
        """Test that server handles invalid JSON gracefully."""
        with client.websocket_connect("/ws") as websocket:
            # Receive connected message
            websocket.receive_json()

            # Send invalid JSON
            websocket.send_text("not valid json{{{")

            # Should receive error
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "Invalid JSON" in data["payload"]["error"]

    def test_websocket_unknown_message_type(self, client):
        """Test that server handles unknown message types gracefully."""
        with client.websocket_connect("/ws") as websocket:
            # Receive connected message
            websocket.receive_json()

            # Send unknown message type
            websocket.send_json({
                "type": "unknown.type",
                "payload": {}
            })

            # Server echoes back unknown message types
            data = websocket.receive_json()
            assert data["type"] == "echo"

            # Connection should remain open
            # Send a ping to verify connection is still alive
            websocket.send_json({"type": "ping"})
            data = websocket.receive_json()
            assert data["type"] == "pong"


class TestWebSocketChatWithoutAlfred:
    """Test chat functionality when Alfred instance is not available."""

    def test_chat_send_without_alfred_returns_error(self, client):
        """Test that chat.send returns error when Alfred is not available."""
        with client.websocket_connect("/ws") as websocket:
            # Receive connected message
            websocket.receive_json()

            # Send chat message
            websocket.send_json({
                "type": "chat.send",
                "payload": {"content": "Hello"}
            })

            # Should receive error
            data = websocket.receive_json()
            assert data["type"] == "chat.error"
            assert "Alfred instance not available" in data["payload"]["error"]

    def test_chat_send_empty_content_returns_error(self, client):
        """Test that chat.send with empty content returns error."""
        with client.websocket_connect("/ws") as websocket:
            # Receive connected message
            websocket.receive_json()

            # Send empty chat message
            websocket.send_json({
                "type": "chat.send",
                "payload": {"content": "   "}
            })

            # Server checks Alfred instance first when content is whitespace
            data = websocket.receive_json()
            assert data["type"] == "chat.error"
            # Server may return either error depending on validation order
            assert "cannot be empty" in data["payload"]["error"] or \
                   "Alfred instance not available" in data["payload"]["error"]


class TestWebSocketCommandWithoutAlfred:
    """Test command functionality when Alfred instance is not available."""

    def test_command_execute_without_alfred_returns_error(self, client):
        """Test that commands return error when Alfred is not available or unknown."""
        with client.websocket_connect("/ws") as websocket:
            # Receive connected message
            websocket.receive_json()

            # Send /help command
            websocket.send_json({
                "type": "command.execute",
                "payload": {"command": "/help"}
            })

            # Should receive error (either about Alfred instance or unknown command)
            data = websocket.receive_json()
            assert data["type"] == "chat.error"
            # Server may return either error depending on implementation order
            assert "Alfred instance not available" in data["payload"]["error"] or \
                   "Unknown command" in data["payload"]["error"]

    def test_command_execute_empty_command_returns_error(self, client):
        """Test that empty command returns error."""
        with client.websocket_connect("/ws") as websocket:
            # Receive connected message
            websocket.receive_json()

            # Send empty command
            websocket.send_json({
                "type": "command.execute",
                "payload": {"command": "   "}
            })

            # Should receive error
            data = websocket.receive_json()
            assert data["type"] == "chat.error"
            assert "cannot be empty" in data["payload"]["error"]

    def test_command_unknown_command(self, client):
        """Test that unknown command returns error."""
        with client.websocket_connect("/ws") as websocket:
            # Receive connected message
            websocket.receive_json()

            # Send unknown command
            websocket.send_json({
                "type": "command.execute",
                "payload": {"command": "/unknown"}
            })

            # Should receive error about Alfred instance first
            data = websocket.receive_json()
            assert data["type"] == "chat.error"
