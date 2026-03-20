"""Tests for chat integration with Alfred."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from starlette.testclient import TestClient as WSClient

from alfred.interfaces.webui import create_app


@pytest.fixture
def mock_alfred():
    """Create a mock Alfred instance."""
    alfred = MagicMock()
    
    async def mock_chat_stream(message):
        """Mock chat stream that yields chunks."""
        chunks = ["Hello", "!", " How", " can", " I", " help", "?"]
        for chunk in chunks:
            yield chunk
    
    alfred.chat_stream = mock_chat_stream
    return alfred


@pytest.fixture
def client_with_alfred(mock_alfred):
    """Create a TestClient with mocked Alfred."""
    app = create_app(alfred_instance=mock_alfred)
    return TestClient(app)


def test_chat_send_message_structure():
    """Verify chat.send message format."""
    message = {
        "type": "chat.send",
        "payload": {
            "content": "Hello, Alfred!",
        },
    }
    assert message["type"] == "chat.send"
    assert message["payload"]["content"] == "Hello, Alfred!"


def test_websocket_accepts_chat_send_message(client_with_alfred):
    """Verify WebSocket accepts chat.send message."""
    with client_with_alfred.websocket_connect("/ws") as websocket:
        # Receive connected message
        response = websocket.receive_json()
        assert response["type"] == "connected"
        
        # Send chat message
        websocket.send_json({
            "type": "chat.send",
            "payload": {"content": "Hello"},
        })
        
        # Receive chat.started
        response = websocket.receive_json()
        assert response["type"] == "chat.started"
        assert "messageId" in response["payload"]
        assert response["payload"]["role"] == "assistant"


def test_websocket_streams_chat_chunks(client_with_alfred):
    """Verify WebSocket streams chat chunks."""
    with client_with_alfred.websocket_connect("/ws") as websocket:
        # Receive connected message
        websocket.receive_json()
        
        # Send chat message
        websocket.send_json({
            "type": "chat.send",
            "payload": {"content": "Hello"},
        })
        
        # Receive chat.started
        started = websocket.receive_json()
        message_id = started["payload"]["messageId"]
        
        # Receive chunks
        chunks = []
        while True:
            response = websocket.receive_json()
            if response["type"] == "chat.chunk":
                assert response["payload"]["messageId"] == message_id
                chunks.append(response["payload"]["content"])
            elif response["type"] == "chat.complete":
                break
        
        # Verify we received all expected chunks
        assert chunks == ["Hello", "!", " How", " can", " I", " help", "?"]


def test_websocket_sends_chat_complete(client_with_alfred):
    """Verify WebSocket sends chat.complete message."""
    with client_with_alfred.websocket_connect("/ws") as websocket:
        # Receive connected message
        websocket.receive_json()
        
        # Send chat message
        websocket.send_json({
            "type": "chat.send",
            "payload": {"content": "Hello"},
        })
        
        # Skip to chat.complete
        while True:
            response = websocket.receive_json()
            if response["type"] == "chat.complete":
                break
        
        # Verify chat.complete structure
        assert response["type"] == "chat.complete"
        assert "messageId" in response["payload"]
        assert "finalContent" in response["payload"]
        assert response["payload"]["finalContent"] == "Hello! How can I help?"
        assert "usage" in response["payload"]
        assert "inputTokens" in response["payload"]["usage"]


def test_websocket_handles_invalid_json(client_with_alfred):
    """Verify WebSocket handles invalid JSON gracefully."""
    with client_with_alfred.websocket_connect("/ws") as websocket:
        # Receive connected message
        websocket.receive_json()
        
        # Send invalid JSON
        websocket.send_text("not valid json")
        
        # Receive error
        response = websocket.receive_json()
        assert response["type"] == "error"
        assert "Invalid JSON" in response["payload"]["error"]


def test_websocket_echoes_unknown_messages(client_with_alfred):
    """Verify WebSocket echoes unknown message types."""
    with client_with_alfred.websocket_connect("/ws") as websocket:
        # Receive connected message
        websocket.receive_json()
        
        # Send unknown message type
        websocket.send_json({
            "type": "unknown.type",
            "payload": {"data": "test"},
        })
        
        # Receive echo
        response = websocket.receive_json()
        assert response["type"] == "echo"


def test_websocket_without_alfred_instance():
    """Verify WebSocket handles missing Alfred instance."""
    app = create_app(alfred_instance=None)
    client = TestClient(app)
    
    with client.websocket_connect("/ws") as websocket:
        # Receive connected message (should still work)
        response = websocket.receive_json()
        assert response["type"] == "connected"
        
        # Send chat message
        websocket.send_json({
            "type": "chat.send",
            "payload": {"content": "Hello"},
        })
        
        # Receive error
        response = websocket.receive_json()
        assert response["type"] == "chat.error"
        assert "Alfred instance not available" in response["payload"]["error"]


@pytest.mark.asyncio
async def test_chat_stream_integration():
    """Verify integration with Alfred's chat_stream method."""
    from alfred.interfaces.webui.server import _handle_chat_message
    
    # Create mock objects
    mock_websocket = AsyncMock()
    mock_alfred = MagicMock()
    
    async def mock_stream(message):
        yield "Test"
        yield " response"
    
    mock_alfred.chat_stream = mock_stream
    
    # Call the handler
    await _handle_chat_message(mock_websocket, mock_alfred, "Hello")
    
    # Verify chat.started was sent
    calls = mock_websocket.send_json.call_args_list
    assert calls[0][0][0]["type"] == "chat.started"
    
    # Verify chat.chunk messages were sent
    chunk_calls = [c for c in calls if c[0][0]["type"] == "chat.chunk"]
    assert len(chunk_calls) == 2
    assert chunk_calls[0][0][0]["payload"]["content"] == "Test"
    assert chunk_calls[1][0][0]["payload"]["content"] == " response"
    
    # Verify chat.complete was sent
    assert calls[-1][0][0]["type"] == "chat.complete"
    assert calls[-1][0][0]["payload"]["finalContent"] == "Test response"


@pytest.mark.asyncio
async def test_chat_stream_error_handling():
    """Verify error handling in chat stream."""
    from alfred.interfaces.webui.server import _handle_chat_message
    
    # Create mock objects
    mock_websocket = AsyncMock()
    mock_alfred = MagicMock()
    
    async def mock_stream_error(message):
        yield "Test"
        raise ValueError("Test error")
    
    mock_alfred.chat_stream = mock_stream_error
    
    # Call the handler
    await _handle_chat_message(mock_websocket, mock_alfred, "Hello")
    
    # Verify chat.started was sent
    calls = mock_websocket.send_json.call_args_list
    assert calls[0][0][0]["type"] == "chat.started"
    
    # Verify chat.error was sent
    error_calls = [c for c in calls if c[0][0]["type"] == "chat.error"]
    assert len(error_calls) == 1
    assert "Test error" in error_calls[0][0][0]["payload"]["error"]


def test_websocket_handles_command_execute(client_with_alfred):
    """Verify WebSocket handles command.execute message type."""
    # Mock the new_session method
    client_with_alfred.app.state.alfred.new_session = AsyncMock(return_value=MagicMock(
        session_id="test-session-123"
    ))
    
    with client_with_alfred.websocket_connect("/ws") as websocket:
        # Receive connected message
        websocket.receive_json()
        
        # Send command message
        websocket.send_json({
            "type": "command.execute",
            "payload": {"command": "/new"},
        })
        
        # Receive session.new response
        response = websocket.receive_json()
        assert response["type"] == "session.new"
        assert "sessionId" in response["payload"]


def test_websocket_command_unknown_command(client_with_alfred):
    """Verify WebSocket returns error for unknown commands."""
    with client_with_alfred.websocket_connect("/ws") as websocket:
        # Receive connected message
        websocket.receive_json()
        
        # Send unknown command
        websocket.send_json({
            "type": "command.execute",
            "payload": {"command": "/unknown"},
        })
        
        # Receive error response
        response = websocket.receive_json()
        assert response["type"] == "chat.error"
        assert "Unknown command" in response["payload"]["error"]
