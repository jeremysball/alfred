"""Integration tests for Alfred Web UI.

These tests verify end-to-end functionality through the WebSocket connection,
testing the complete flow from connection establishment through message handling.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from alfred.interfaces.webui import create_app
from tests.webui.fakes import FakeAlfred


@pytest.fixture
def mock_alfred() -> FakeAlfred:
    """Create a realistic Alfred fake."""

    return FakeAlfred()


@pytest.fixture
def client(mock_alfred: FakeAlfred) -> tuple[TestClient, FakeAlfred]:
    """Create test client with a realistic Alfred fake."""

    app = create_app(alfred_instance=mock_alfred)
    return TestClient(app), mock_alfred


def _consume_startup_messages(websocket) -> tuple[dict, dict, dict]:
    """Read the standard Web UI startup sequence."""

    connected = websocket.receive_json()
    session_loaded = websocket.receive_json()
    status_update = websocket.receive_json()
    return connected, session_loaded, status_update


def _collect_chat_response(websocket) -> tuple[list[str], list[str], list[dict], dict]:
    """Collect chat stream output until chat.complete arrives."""

    content_chunks: list[str] = []
    reasoning_chunks: list[str] = []
    status_updates: list[dict] = []
    complete: dict | None = None

    while complete is None:
        data = websocket.receive_json()
        if data["type"] == "chat.chunk":
            content_chunks.append(data["payload"]["content"])
        elif data["type"] == "reasoning.chunk":
            reasoning_chunks.append(data["payload"]["content"])
        elif data["type"] == "status.update":
            status_updates.append(data["payload"])
        elif data["type"] == "chat.complete":
            complete = data
        else:
            pytest.fail(f"Unexpected message type: {data['type']}")

    trailing = websocket.receive_json()
    if trailing["type"] == "status.update":
        status_updates.append(trailing["payload"])
    else:
        pytest.fail(f"Unexpected trailing message type: {trailing['type']}")

    return content_chunks, reasoning_chunks, status_updates, complete


class TestFullChatFlow:
    """End-to-end tests for complete chat flows."""

    def test_full_chat_flow_single_message(self, client: tuple[TestClient, FakeAlfred]) -> None:
        """Test complete flow: connect, send message, receive streaming response."""

        test_client, fake_alfred = client

        with test_client.websocket_connect("/ws") as websocket:
            connected, session_loaded, status_update = _consume_startup_messages(websocket)
            assert connected["type"] == "connected"
            assert session_loaded["type"] == "session.loaded"
            assert status_update["type"] == "status.update"

            test_message = "What is the weather today?"
            websocket.send_json({"type": "chat.send", "payload": {"content": test_message}})

            started = websocket.receive_json()
            assert started["type"] == "chat.started"
            message_id = started["payload"]["messageId"]
            assert started["payload"]["role"] == "assistant"

            received_chunks, _, status_updates, complete = _collect_chat_response(websocket)

        assert "".join(received_chunks) == "Hello! How can I help?"
        assert complete["payload"]["messageId"] == message_id
        assert complete["payload"]["finalContent"] == "Hello! How can I help?"
        assert len(status_updates) >= 1
        assert fake_alfred.chat_called is True
        assert fake_alfred.last_message == test_message

    def test_full_chat_flow_multiple_messages(self, client: tuple[TestClient, FakeAlfred]) -> None:
        """Test sending multiple messages in sequence."""

        test_client, fake_alfred = client

        with test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.receive_json()

            message_ids: list[str] = []

            for i in range(3):
                websocket.send_json({"type": "chat.send", "payload": {"content": f"Message {i + 1}"}})

                data = websocket.receive_json()
                assert data["type"] == "chat.started"
                message_id = data["payload"]["messageId"]
                message_ids.append(message_id)

                received_chunks: list[str] = []
                while True:
                    data = websocket.receive_json()
                    if data["type"] == "chat.chunk":
                        received_chunks.append(data["payload"]["content"])
                        assert data["payload"]["messageId"] == message_id
                    elif data["type"] == "status.update":
                        continue
                    elif data["type"] == "chat.complete":
                        assert data["payload"]["messageId"] == message_id
                        break
                    else:
                        pytest.fail(f"Unexpected message type: {data['type']}")

                trailing = websocket.receive_json()
                assert trailing["type"] == "status.update"
                assert "".join(received_chunks) == "Hello! How can I help?"

        assert len(message_ids) == 3
        assert len(set(message_ids)) == 3
        assert fake_alfred.chat_messages == ["Message 1", "Message 2", "Message 3"]

    def test_full_chat_flow_with_reasoning(self, client: tuple[TestClient, FakeAlfred]) -> None:
        """Test chat flow with reasoning chunks."""

        reasoning_parts = ["[REASONING]Let me think", " about this", "[/REASONING]", "The answer is 42"]
        fake_alfred = FakeAlfred(stream_parts=reasoning_parts)
        app = create_app(alfred_instance=fake_alfred)
        test_client = TestClient(app)

        with test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.receive_json()

            websocket.send_json({"type": "chat.send", "payload": {"content": "What is the answer?"}})

            started = websocket.receive_json()
            assert started["type"] == "chat.started"
            message_id = started["payload"]["messageId"]

            reasoning_chunks: list[str] = []
            content_chunks: list[str] = []

            while True:
                data = websocket.receive_json()
                if data["type"] == "reasoning.chunk":
                    reasoning_chunks.append(data["payload"]["content"])
                    assert data["payload"]["messageId"] == message_id
                elif data["type"] == "chat.chunk":
                    content_chunks.append(data["payload"]["content"])
                    assert data["payload"]["messageId"] == message_id
                elif data["type"] == "status.update":
                    continue
                elif data["type"] == "chat.complete":
                    assert data["payload"]["messageId"] == message_id
                    break
                else:
                    pytest.fail(f"Unexpected message type: {data['type']}")

            trailing = websocket.receive_json()
            assert trailing["type"] == "status.update"

        assert len(reasoning_chunks) > 0
        assert "Let me think" in "".join(reasoning_chunks)
        assert "answer is 42" in "".join(content_chunks)


class TestSessionManagementFlow:
    """End-to-end tests for session management commands."""

    def test_session_create_new_session(self, client: tuple[TestClient, FakeAlfred]) -> None:
        """Test creating a new session via /new command."""

        test_client, fake_alfred = client
        original_session_count = len(fake_alfred.core.session_manager._sessions)

        with test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.receive_json()

            websocket.send_json({"type": "command.execute", "payload": {"command": "/new"}})

            data = websocket.receive_json()
            assert data["type"] == "session.new"
            assert "sessionId" in data["payload"]
            assert data["payload"]["message"] == "New session created"
            assert fake_alfred.core.session_manager.new_session_called is True
            assert len(fake_alfred.core.session_manager._sessions) == original_session_count + 1

    def test_session_list_sessions(self, client: tuple[TestClient, FakeAlfred]) -> None:
        """Test listing sessions via /sessions command."""

        test_client, fake_alfred = client

        with test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.receive_json()

            websocket.send_json({"type": "command.execute", "payload": {"command": "/sessions"}})

            data = websocket.receive_json()
            assert data["type"] == "session.list"
            assert "sessions" in data["payload"]
            assert len(data["payload"]["sessions"]) == 2

            for session in data["payload"]["sessions"]:
                assert "id" in session
                assert "summary" in session
                assert "created" in session

            assert fake_alfred.core.session_manager.list_sessions_called is True

    def test_session_resume_session(self, client: tuple[TestClient, FakeAlfred]) -> None:
        """Test resuming a session via /resume command."""

        test_client, fake_alfred = client
        target_session_id = "session-2"

        with test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.receive_json()

            websocket.send_json({"type": "command.execute", "payload": {"command": f"/resume {target_session_id}"}})

            data = websocket.receive_json()
            assert data["type"] == "session.loaded"
            assert data["payload"]["sessionId"] == target_session_id
            assert "messages" in data["payload"]

            status_update = websocket.receive_json()
            assert status_update["type"] == "status.update"

            assert fake_alfred.core.session_manager.resume_session_called is True

    def test_session_resume_without_id(self, client: tuple[TestClient, FakeAlfred]) -> None:
        """Test /resume command without session ID."""

        test_client, _ = client

        with test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.receive_json()

            websocket.send_json({"type": "command.execute", "payload": {"command": "/resume"}})

            data = websocket.receive_json()
            assert data["type"] == "chat.error"
            assert "Session ID required" in data["payload"]["error"]

    def test_session_full_workflow(self, client: tuple[TestClient, FakeAlfred]) -> None:
        """Test complete session management workflow."""

        test_client, fake_alfred = client

        with test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.receive_json()

            websocket.send_json({"type": "command.execute", "payload": {"command": "/new"}})
            data = websocket.receive_json()
            assert data["type"] == "session.new"
            assert "sessionId" in data["payload"]
            websocket.receive_json()  # status.update

            websocket.send_json({"type": "command.execute", "payload": {"command": "/sessions"}})
            data = websocket.receive_json()
            assert data["type"] == "session.list"
            assert len(data["payload"]["sessions"]) == 3

            websocket.send_json({"type": "command.execute", "payload": {"command": "/resume session-1"}})
            data = websocket.receive_json()
            assert data["type"] == "session.loaded"
            assert data["payload"]["sessionId"] == "session-1"
            websocket.receive_json()  # status.update

            websocket.send_json({"type": "command.execute", "payload": {"command": "/session"}})
            data = websocket.receive_json()
            assert data["type"] == "session.info"
            assert data["payload"]["sessionId"] == "session-1"

        assert fake_alfred.core.session_manager.new_session_called is True
        assert fake_alfred.core.session_manager.list_sessions_called is True
        assert fake_alfred.core.session_manager.resume_session_called is True


class TestErrorHandling:
    """Tests for error scenarios and edge cases."""

    def test_error_chat_without_alfred(self) -> None:
        """Test error when Alfred instance is not available."""

        app = create_app(alfred_instance=None)
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()

            websocket.send_json({"type": "chat.send", "payload": {"content": "Hello"}})

            data = websocket.receive_json()
            assert data["type"] == "chat.error"
            assert "Alfred instance not available" in data["payload"]["error"]

            websocket.send_json({"type": "ping"})
            data = websocket.receive_json()
            assert data["type"] == "pong"

    def test_error_invalid_json(self, client: tuple[TestClient, FakeAlfred]) -> None:
        """Test handling of invalid JSON messages."""

        test_client, _ = client

        with test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.receive_json()

            websocket.send_text("not valid json {{{")

            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "Invalid JSON" in data["payload"]["error"]

            websocket.send_json({"type": "ping"})
            data = websocket.receive_json()
            assert data["type"] == "pong"

    def test_error_unknown_command(self, client: tuple[TestClient, FakeAlfred]) -> None:
        """Test handling of unknown commands."""

        test_client, _ = client

        with test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.receive_json()

            websocket.send_json({"type": "command.execute", "payload": {"command": "/unknowncommand"}})

            data = websocket.receive_json()
            assert data["type"] == "chat.error"
            assert "Unknown command" in data["payload"]["error"]

    def test_error_empty_message(self, client: tuple[TestClient, FakeAlfred]) -> None:
        """Test handling of empty chat messages."""

        test_client, _ = client

        with test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.receive_json()

            websocket.send_json({"type": "chat.send", "payload": {"content": "   "}})

            data = websocket.receive_json()
            assert data["type"] == "chat.error"
            assert "Message content cannot be empty" in data["payload"]["error"]

            websocket.send_json({"type": "ping"})
            data = websocket.receive_json()
            assert data["type"] == "pong"

    def test_error_resume_nonexistent_session(self, client: tuple[TestClient, FakeAlfred]) -> None:
        """Test resuming a session that doesn't exist."""

        test_client, fake_alfred = client

        with test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.receive_json()

            websocket.send_json({"type": "command.execute", "payload": {"command": "/resume nonexistent-session"}})

            data = websocket.receive_json()
            assert data["type"] == "chat.error"
            assert "Failed to resume session" in data["payload"]["error"]
            assert fake_alfred.core.session_manager.resume_session_called is True

    def test_recovery_after_error(self, client: tuple[TestClient, FakeAlfred]) -> None:
        """Test that normal operation resumes after an error."""

        test_client, fake_alfred = client

        with test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.receive_json()

            websocket.send_json({"type": "chat.send", "payload": {"content": ""}})
            data = websocket.receive_json()
            assert data["type"] == "chat.error"

            websocket.send_json({"type": "chat.send", "payload": {"content": "Hello"}})
            started = websocket.receive_json()
            assert started["type"] == "chat.started"
            message_id = started["payload"]["messageId"]

            received_chunks: list[str] = []
            while True:
                data = websocket.receive_json()
                if data["type"] == "chat.chunk":
                    received_chunks.append(data["payload"]["content"])
                    assert data["payload"]["messageId"] == message_id
                elif data["type"] == "status.update":
                    continue
                elif data["type"] == "chat.complete":
                    break
                else:
                    pytest.fail(f"Unexpected message type: {data['type']}")

        assert "".join(received_chunks) == "Hello! How can I help?"
        assert fake_alfred.chat_called is True
        assert fake_alfred.last_message == "Hello"


class TestConcurrentOperations:
    """Tests for concurrent and rapid operations."""

    def test_rapid_ping_pong(self, client: tuple[TestClient, FakeAlfred]) -> None:
        """Test rapid ping/pong exchanges."""

        test_client, _ = client

        with test_client.websocket_connect("/ws") as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.receive_json()

            for _ in range(10):
                websocket.send_json({"type": "ping"})

            pong_count = 0
            for _ in range(10):
                data = websocket.receive_json()
                if data["type"] == "pong":
                    pong_count += 1

            assert pong_count == 10

    def test_multiple_commands_in_sequence(self, client: tuple[TestClient, FakeAlfred]) -> None:
        """Test multiple commands sent in rapid succession."""

        test_client, fake_alfred = client
        context_data = {
            "system_prompt": {"sections": [{"name": "AGENTS.md", "tokens": 12}], "total_tokens": 12},
            "memories": {
                "displayed": 1,
                "total": 2,
                "items": [{"role": "user", "content": "Remember this", "timestamp": "2026-03-20"}],
                "tokens": 8,
            },
            "session_history": {"count": 1, "messages": [{"role": "user", "content": "hello"}], "tokens": 3},
            "tool_calls": {
                "count": 1,
                "items": [
                    {
                        "tool_name": "read",
                        "arguments": {"path": "README.md"},
                        "output": "file contents",
                        "status": "success",
                    }
                ],
                "tokens": 9,
            },
            "total_tokens": 32,
        }

        with (
            patch(
                "alfred.context_display.get_context_display",
                AsyncMock(return_value=context_data),
            ),
            test_client.websocket_connect("/ws") as websocket,
        ):
            websocket.receive_json()
            websocket.receive_json()
            websocket.receive_json()

            for cmd in ["/session", "/context", "/sessions"]:
                websocket.send_json({"type": "command.execute", "payload": {"command": cmd}})

            responses = [websocket.receive_json()["type"] for _ in range(3)]

        assert "session.info" in responses
        assert "context.info" in responses
        assert "session.list" in responses
        assert fake_alfred.core.session_manager.list_sessions_called is True
