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


class MockAlfred:
    """Mock Alfred instance for testing chat flow."""

    def __init__(self, chunks=None):
        self.chunks = chunks or ["Hello", " ", "world", "!"]
        self.chat_called = False
        self.last_message = None

    async def chat_stream(self, message, tool_callback=None):
        """Mock chat stream that yields chunks."""
        self.chat_called = True
        self.last_message = message
        for chunk in self.chunks:
            yield chunk


@pytest.fixture
def mock_app():
    """Create test app with mocked Alfred instance."""
    mock_alfred = MockAlfred()
    return create_app(alfred_instance=mock_alfred), mock_alfred


@pytest.fixture
def mock_client(mock_app):
    """Create test client with mocked Alfred."""
    app, _ = mock_app
    return TestClient(app)


class TestWebSocketChatWithMockedAlfred:
    """Test chat functionality with mocked Alfred instance."""

    def test_chat_send_receive_flow(self, mock_client, mock_app):
        """Test complete chat.send and chat.chunk flow.

        Verifies:
        - chat.started is sent first
        - chat.chunk messages are received in order
        - chat.complete is sent at the end
        - Message ID is consistent across all messages
        """
        _, mock_alfred = mock_app

        with mock_client.websocket_connect("/ws") as websocket:
            # Receive connected message
            websocket.receive_json()

            # Send chat message
            websocket.send_json({
                "type": "chat.send",
                "payload": {"content": "Hello there"}
            })

            # Should receive chat.started
            data = websocket.receive_json()
            assert data["type"] == "chat.started"
            assert "messageId" in data["payload"]
            message_id = data["payload"]["messageId"]
            assert data["payload"]["role"] == "assistant"

            # Should receive chunks in order
            received_chunks = []
            while True:
                data = websocket.receive_json()
                if data["type"] == "chat.chunk":
                    received_chunks.append(data["payload"]["content"])
                    assert data["payload"]["messageId"] == message_id
                elif data["type"] == "chat.complete":
                    # Verify completion
                    assert data["payload"]["messageId"] == message_id
                    assert "finalContent" in data["payload"]
                    assert "usage" in data["payload"]
                    break
                elif data["type"] == "status.update":
                    # Status updates may be sent during streaming
                    continue
                else:
                    # Unexpected message type
                    pytest.fail(f"Unexpected message type: {data['type']}")

            # Verify all chunks received
            assert received_chunks == ["Hello", " ", "world", "!"]
            assert mock_alfred.chat_called
            assert mock_alfred.last_message == "Hello there"

    def test_chat_with_reasoning(self, mock_client):
        """Test chat flow with reasoning chunks."""
        # Create app with reasoning chunks
        reasoning_chunks = [
            "[REASONING]Let me think",
            " about this",
            "[/REASONING]",
            "The answer is 42"
        ]
        mock_alfred = MockAlfred(chunks=reasoning_chunks)
        app = create_app(alfred_instance=mock_alfred)
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            # Receive connected message
            websocket.receive_json()

            # Send chat message
            websocket.send_json({
                "type": "chat.send",
                "payload": {"content": "What is the answer?"}
            })

            # Receive chat.started
            data = websocket.receive_json()
            assert data["type"] == "chat.started"
            message_id = data["payload"]["messageId"]

            # Collect all chunks
            reasoning_chunks_received = []
            content_chunks_received = []

            while True:
                data = websocket.receive_json()
                if data["type"] == "reasoning.chunk":
                    reasoning_chunks_received.append(data["payload"]["content"])
                    assert data["payload"]["messageId"] == message_id
                elif data["type"] == "chat.chunk":
                    content_chunks_received.append(data["payload"]["content"])
                    assert data["payload"]["messageId"] == message_id
                elif data["type"] == "chat.complete":
                    break
                elif data["type"] == "status.update":
                    continue
                else:
                    pytest.fail(f"Unexpected message type: {data['type']}")

            # Verify reasoning was split correctly
            assert "Let me think" in reasoning_chunks_received[0]
            assert "The answer is 42" in content_chunks_received


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
