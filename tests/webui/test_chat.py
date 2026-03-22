"""Tests for chat integration with Alfred."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from alfred.interfaces.webui import create_app
from alfred.interfaces.webui.server import _handle_chat_message
from tests.webui.fakes import FakeAlfred


@pytest.fixture
def mock_alfred() -> FakeAlfred:
    """Create a realistic Alfred fake for chat tests."""

    return FakeAlfred()


@pytest.fixture
def client_with_alfred(mock_alfred: FakeAlfred) -> TestClient:
    """Create a TestClient with a realistic Alfred fake."""

    app = create_app(alfred_instance=mock_alfred)
    return TestClient(app)


def _consume_startup_messages(websocket) -> tuple[dict, dict, dict]:
    """Read the standard Web UI startup messages."""

    connected = websocket.receive_json()
    session_loaded = websocket.receive_json()
    daemon_status = websocket.receive_json()
    status_update = websocket.receive_json()
    assert daemon_status["type"] == "daemon.status"
    return connected, session_loaded, status_update


def test_chat_send_message_structure() -> None:
    """Verify chat.send message format."""

    message = {
        "type": "chat.send",
        "payload": {
            "content": "Hello, Alfred!",
        },
    }
    assert message["type"] == "chat.send"
    assert message["payload"]["content"] == "Hello, Alfred!"


def test_websocket_accepts_chat_send_message(client_with_alfred: TestClient) -> None:
    """Verify WebSocket accepts chat.send message."""

    with client_with_alfred.websocket_connect("/ws") as websocket:
        connected, session_loaded, status_update = _consume_startup_messages(websocket)
        assert connected["type"] == "connected"
        assert session_loaded["type"] == "session.loaded"
        assert status_update["type"] == "status.update"

        websocket.send_json({"type": "chat.send", "payload": {"content": "Hello"}})

        response = websocket.receive_json()
        assert response["type"] == "chat.started"
        assert "messageId" in response["payload"]
        assert response["payload"]["role"] == "assistant"


def test_websocket_streams_chat_chunks(client_with_alfred: TestClient) -> None:
    """Verify WebSocket streams chat chunks."""

    with client_with_alfred.websocket_connect("/ws") as websocket:
        _consume_startup_messages(websocket)

        websocket.send_json({"type": "chat.send", "payload": {"content": "Hello"}})

        started = websocket.receive_json()
        message_id = started["payload"]["messageId"]

        chunks = []
        while True:
            response = websocket.receive_json()
            if response["type"] == "chat.chunk":
                assert response["payload"]["messageId"] == message_id
                chunks.append(response["payload"]["content"])
            elif response["type"] == "chat.complete":
                break

        assert "".join(chunks) == "Hello! How can I help?"


def test_websocket_sends_chat_complete(client_with_alfred: TestClient) -> None:
    """Verify WebSocket sends chat.complete message."""

    with client_with_alfred.websocket_connect("/ws") as websocket:
        _consume_startup_messages(websocket)

        websocket.send_json({"type": "chat.send", "payload": {"content": "Hello"}})

        while True:
            response = websocket.receive_json()
            if response["type"] == "chat.complete":
                break

        assert response["type"] == "chat.complete"
        assert "messageId" in response["payload"]
        assert "finalContent" in response["payload"]
        assert response["payload"]["finalContent"] == "Hello! How can I help?"
        assert "usage" in response["payload"]
        assert "inputTokens" in response["payload"]["usage"]


def test_websocket_handles_invalid_json(client_with_alfred: TestClient) -> None:
    """Verify WebSocket handles invalid JSON gracefully."""

    with client_with_alfred.websocket_connect("/ws") as websocket:
        _consume_startup_messages(websocket)

        websocket.send_text("not valid json")

        response = websocket.receive_json()
        assert response["type"] == "error"
        assert "Invalid JSON" in response["payload"]["error"]


def test_websocket_echoes_unknown_messages(client_with_alfred: TestClient) -> None:
    """Verify WebSocket echoes unknown message types."""

    with client_with_alfred.websocket_connect("/ws") as websocket:
        _consume_startup_messages(websocket)

        websocket.send_json({"type": "unknown.type", "payload": {"data": "test"}})

        response = websocket.receive_json()
        assert response["type"] == "echo"


def test_websocket_without_alfred_instance() -> None:
    """Verify WebSocket handles missing Alfred instance."""

    app = create_app(alfred_instance=None)
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        response = websocket.receive_json()
        assert response["type"] == "connected"
        assert websocket.receive_json()["type"] == "daemon.status"

        websocket.send_json({"type": "chat.send", "payload": {"content": "Hello"}})

        response = websocket.receive_json()
        assert response["type"] == "chat.error"
        assert "Alfred instance not available" in response["payload"]["error"]


@pytest.mark.asyncio
async def test_chat_stream_integration() -> None:
    """Verify integration with Alfred's chat_stream method."""

    mock_websocket = AsyncMock()
    mock_alfred = FakeAlfred(stream_parts=["Test", " response"])

    await _handle_chat_message(mock_websocket, mock_alfred, "Hello")

    calls = mock_websocket.send_json.call_args_list
    assert calls[0][0][0]["type"] == "chat.started"

    chunk_calls = [c for c in calls if c[0][0]["type"] == "chat.chunk"]
    assert "".join(call[0][0]["payload"]["content"] for call in chunk_calls) == "Test response"
    assert len(chunk_calls) >= 1

    complete_call = next(call for call in calls if call[0][0]["type"] == "chat.complete")
    assert complete_call[0][0]["payload"]["finalContent"] == "Test response"


@pytest.mark.asyncio
async def test_chat_stream_error_handling() -> None:
    """Verify error handling in chat stream."""

    mock_websocket = AsyncMock()
    mock_alfred = FakeAlfred(stream_parts=["Test"])

    async def mock_stream_error(message: str, tool_callback=None):
        yield "Test"
        raise ValueError("Test error")

    mock_alfred.chat_stream = mock_stream_error  # type: ignore[method-assign]

    await _handle_chat_message(mock_websocket, mock_alfred, "Hello")

    calls = mock_websocket.send_json.call_args_list
    assert calls[0][0][0]["type"] == "chat.started"

    error_calls = [c for c in calls if c[0][0]["type"] == "chat.error"]
    assert len(error_calls) == 1
    assert "Test error" in error_calls[0][0][0]["payload"]["error"]


def test_websocket_handles_command_execute(client_with_alfred: TestClient) -> None:
    """Verify WebSocket handles command.execute message type."""

    with client_with_alfred.websocket_connect("/ws") as websocket:
        _consume_startup_messages(websocket)

        websocket.send_json({"type": "command.execute", "payload": {"command": "/new"}})

        response = websocket.receive_json()
        assert response["type"] == "session.new"
        assert "sessionId" in response["payload"]
        assert response["payload"]["sessionId"] == "session-3"


def test_websocket_command_unknown_command(client_with_alfred: TestClient) -> None:
    """Verify WebSocket returns error for unknown commands."""

    with client_with_alfred.websocket_connect("/ws") as websocket:
        _consume_startup_messages(websocket)

        websocket.send_json({"type": "command.execute", "payload": {"command": "/unknown"}})

        response = websocket.receive_json()
        assert response["type"] == "chat.error"
        assert "Unknown command" in response["payload"]["error"]
