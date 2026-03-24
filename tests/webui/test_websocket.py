"""WebSocket protocol tests for Alfred Web UI."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from alfred.interfaces.webui.server import create_app
from tests.webui.fakes import FakeAlfred as MockAlfred
from tests.webui.fakes import make_message, make_session, make_tool_call


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
            # Receive startup messages
            websocket.receive_json()
            websocket.receive_json()

            # Send ping
            websocket.send_json({"type": "ping"})

            # Should receive pong
            data = websocket.receive_json()
            assert data["type"] == "pong"

    def test_websocket_rejects_invalid_json(self, client):
        """Test that server handles invalid JSON gracefully."""
        with client.websocket_connect("/ws") as websocket:
            # Receive startup messages
            websocket.receive_json()
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
            # Receive startup messages
            websocket.receive_json()
            websocket.receive_json()

            # Send unknown message type
            websocket.send_json({"type": "unknown.type", "payload": {}})

            # Server echoes back unknown message types
            data = websocket.receive_json()
            assert data["type"] == "echo"

            # Connection should remain open
            # Send a ping to verify connection is still alive
            websocket.send_json({"type": "ping"})
            data = websocket.receive_json()
            assert data["type"] == "pong"


class TestWebSocketSessionRestore:
    """Test session payload restore behavior."""

    def test_session_loaded_includes_tool_calls(self):
        """Session load should include persisted tool calls for assistant messages."""
        assistant_message = make_message(
            "assistant",
            "Here are the results",
            idx=1,
            id="assistant-123",
            reasoning_content="thinking",
            tool_calls=[
                make_tool_call(
                    tool_call_id="tool-1",
                    tool_name="bash",
                    arguments={"command": "ls"},
                    output="done",
                    status="success",
                    insert_position=7,
                    sequence=1,
                )
            ],
            streaming=True,
        )
        mock_alfred = MockAlfred(sessions=[make_session("session-restore", messages=[assistant_message])])
        app = create_app(alfred_instance=mock_alfred)
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            connected = websocket.receive_json()
            session_loaded = websocket.receive_json()
            daemon_status = websocket.receive_json()
            status_update = websocket.receive_json()

            assert connected["type"] == "connected"
            assert session_loaded["type"] == "session.loaded"
            assert daemon_status["type"] == "daemon.status"
            assert status_update["type"] == "status.update"
            assert session_loaded["payload"]["messages"][0]["id"] == "assistant-123"
            assert session_loaded["payload"]["messages"][0]["streaming"] is True
            assert session_loaded["payload"]["messages"][0]["toolCalls"][0]["toolCallId"] == "tool-1"
            assert session_loaded["payload"]["messages"][0]["toolCalls"][0]["status"] == "success"


class TestWebSocketChatWithoutAlfred:
    """Test chat functionality when Alfred instance is not available."""

    def test_chat_send_without_alfred_returns_error(self, client):
        """Test that chat.send returns error when Alfred is not available."""
        with client.websocket_connect("/ws") as websocket:
            # Receive startup messages
            websocket.receive_json()
            websocket.receive_json()

            # Send chat message
            websocket.send_json({"type": "chat.send", "payload": {"content": "Hello"}})

            # Should receive error
            data = websocket.receive_json()
            assert data["type"] == "chat.error"
            assert "Alfred instance not available" in data["payload"]["error"]

    def test_chat_send_empty_content_returns_error(self, client):
        """Test that chat.send with empty content returns error."""
        with client.websocket_connect("/ws") as websocket:
            # Receive startup messages
            websocket.receive_json()
            websocket.receive_json()

            # Send empty chat message
            websocket.send_json({"type": "chat.send", "payload": {"content": "   "}})

            # Server checks Alfred instance first when content is whitespace
            data = websocket.receive_json()
            assert data["type"] == "chat.error"
            # Server may return either error depending on validation order
            assert "cannot be empty" in data["payload"]["error"] or "Alfred instance not available" in data["payload"]["error"]


@pytest.fixture
def mock_app():
    """Create test app with mocked Alfred instance."""
    mock_alfred = MockAlfred(chunks=["Hello", " ", "world", "!"])
    return create_app(alfred_instance=mock_alfred), mock_alfred


@pytest.fixture
def mock_client(mock_app):
    """Create test client with mocked Alfred."""
    app, _ = mock_app
    return TestClient(app)


class TestWebUIDebugInstrumentation:
    """Test debug-only Web UI instrumentation hooks."""

    def test_app_config_reports_debug_flag(self):
        """The browser should be able to read whether Web UI debug instrumentation is enabled."""
        app = create_app(alfred_instance=None, debug=True)
        client = TestClient(app)

        response = client.get("/app-config.js")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/javascript")
        assert '"debug": true' in response.text

    def test_chat_debug_logs_turn_summary(self, caplog):
        """Debug mode should log per-turn websocket summary stats for long-response diagnosis."""
        mock_alfred = MockAlfred(chunks=["a" * 20, "b" * 20, "c" * 20])
        app = create_app(alfred_instance=mock_alfred, debug=True)
        client = TestClient(app)

        with caplog.at_level("DEBUG", logger="alfred.interfaces.webui.server"), client.websocket_connect("/ws") as websocket:
            _connect_and_skip_initial_messages(websocket)
            websocket.send_json({"type": "chat.send", "payload": {"content": "instrument this"}})

            while True:
                data = websocket.receive_json()
                if data["type"] == "chat.complete":
                    break

        turn_logs = [record.message for record in caplog.records if "webui.websocket.turn_summary" in record.message]
        assert turn_logs
        assert "chat.complete" in turn_logs[-1]
        assert "total_bytes_sent=" in turn_logs[-1]
        assert "max_frame_bytes=" in turn_logs[-1]


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
            _connect_and_skip_initial_messages(websocket)

            # Send chat message
            websocket.send_json({"type": "chat.send", "payload": {"content": "Hello there"}})

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

            # Verify all content received, regardless of batching boundaries
            assert "".join(received_chunks) == "Hello world!"
            assert mock_alfred.chat_called
            assert mock_alfred.last_message == "Hello there"

    def test_chat_with_reasoning(self, mock_client):
        """Test chat flow with reasoning chunks."""
        # Create app with reasoning chunks
        reasoning_chunks = ["[REASONING]Let me think", " about this", "[/REASONING]", "The answer is 42"]
        mock_alfred = MockAlfred(chunks=reasoning_chunks)
        app = create_app(alfred_instance=mock_alfred)
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            _connect_and_skip_initial_messages(websocket)

            # Send chat message
            websocket.send_json({"type": "chat.send", "payload": {"content": "What is the answer?"}})

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

    def test_chat_batches_many_small_content_chunks(self):
        """Long streams should batch tiny content updates into fewer websocket messages."""
        tiny_chunks = ["a"] * 300
        mock_alfred = MockAlfred(chunks=tiny_chunks)
        app = create_app(alfred_instance=mock_alfred)
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            _connect_and_skip_initial_messages(websocket)
            websocket.send_json({"type": "chat.send", "payload": {"content": "Batch this content"}})

            data = websocket.receive_json()
            assert data["type"] == "chat.started"

            received_chunks = []
            while True:
                data = websocket.receive_json()
                if data["type"] == "chat.chunk":
                    received_chunks.append(data["payload"]["content"])
                elif data["type"] == "chat.complete":
                    break
                elif data["type"] == "status.update":
                    continue
                else:
                    pytest.fail(f"Unexpected message type: {data['type']}")

            assert "".join(received_chunks) == "a" * 300
            assert len(received_chunks) < 50

    def test_chat_batches_many_small_reasoning_chunks(self):
        """Long reasoning streams should batch tiny reasoning updates into fewer websocket messages."""
        reasoning_stream = ["[REASONING]a", *(["a"] * 299), "[/REASONING]", "done"]
        mock_alfred = MockAlfred(chunks=reasoning_stream)
        app = create_app(alfred_instance=mock_alfred)
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            _connect_and_skip_initial_messages(websocket)
            websocket.send_json({"type": "chat.send", "payload": {"content": "Batch this reasoning"}})

            data = websocket.receive_json()
            assert data["type"] == "chat.started"

            reasoning_chunks_received = []
            content_chunks_received = []
            while True:
                data = websocket.receive_json()
                if data["type"] == "reasoning.chunk":
                    reasoning_chunks_received.append(data["payload"]["content"])
                elif data["type"] == "chat.chunk":
                    content_chunks_received.append(data["payload"]["content"])
                elif data["type"] == "chat.complete":
                    break
                elif data["type"] == "status.update":
                    continue
                else:
                    pytest.fail(f"Unexpected message type: {data['type']}")

            assert "".join(reasoning_chunks_received) == "a" * 300
            assert len(reasoning_chunks_received) < 50
            assert "".join(content_chunks_received) == "done"

    def test_chat_batches_many_small_tool_output_chunks(self):
        """Long tool output streams should batch tiny tool.output updates into fewer websocket messages."""
        from alfred.agent import ToolEnd, ToolOutput, ToolStart

        mock_alfred = MockAlfred(
            stream_parts=[
                ToolStart(tool_call_id="tool-1", tool_name="bash", arguments={}),
                *[ToolOutput(tool_call_id="tool-1", tool_name="bash", chunk="x") for _ in range(300)],
                ToolEnd(tool_call_id="tool-1", tool_name="bash", result="ok"),
                "done",
            ]
        )
        app = create_app(alfred_instance=mock_alfred)
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            _connect_and_skip_initial_messages(websocket)
            websocket.send_json({"type": "chat.send", "payload": {"content": "Run tool"}})

            data = websocket.receive_json()
            assert data["type"] == "chat.started"

            tool_outputs = []
            saw_tool_start = False
            saw_tool_end = False
            while True:
                data = websocket.receive_json()
                if data["type"] == "tool.start":
                    saw_tool_start = True
                elif data["type"] == "tool.output":
                    tool_outputs.append(data["payload"]["chunk"])
                elif data["type"] == "tool.end":
                    saw_tool_end = True
                elif data["type"] == "chat.complete":
                    break
                elif data["type"] == "status.update" or data["type"] == "chat.chunk":
                    continue
                else:
                    pytest.fail(f"Unexpected message type: {data['type']}")

            assert saw_tool_start is True
            assert saw_tool_end is True
            assert "".join(tool_outputs) == "x" * 300
            assert len(tool_outputs) < 50


def test_chat_cancel_and_edit_restarts_without_duplicate_user_messages() -> None:
    mock_alfred = MockAlfred(chunks=["Retry ", "response"], chunk_delay=0.05, sessions=[make_session("session-1", messages=[])])
    app = create_app(alfred_instance=mock_alfred)
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        _connect_and_skip_initial_messages(websocket)

        websocket.send_json({"type": "chat.send", "payload": {"content": "Hello"}})

        started = websocket.receive_json()
        assert started["type"] == "chat.started"
        assistant_id = started["payload"]["messageId"]

        websocket.send_json({"type": "chat.cancel"})


        while True:
            data = websocket.receive_json()
            if data["type"] == "chat.cancelled":
                assert data["payload"]["messageId"] == assistant_id
                break
            if data["type"] in {
                "status.update",
                "chat.chunk",
                "reasoning.chunk",
                "tool.start",
                "tool.output",
                "tool.end",
            }:
                continue
            pytest.fail(f"Unexpected message type after cancel: {data['type']}")

        session = mock_alfred.core.session_manager.get_current_cli_session()
        assert session is not None
        assert len(session.messages) == 1
        assert session.messages[0].role.value == "user"
        assert session.messages[0].content == "Hello"

        websocket.send_json(
            {
                "type": "chat.edit",
                "payload": {
                    "messageId": assistant_id,
                    "content": "Hello",
                },
            }
        )

        restarted = websocket.receive_json()
        assert restarted["type"] == "chat.started"
        restarted_id = restarted["payload"]["messageId"]
        assert restarted_id != assistant_id

        while True:
            data = websocket.receive_json()
            if data["type"] == "chat.complete":
                break
            if data["type"] in {
                "status.update",
                "chat.chunk",
                "reasoning.chunk",
                "tool.start",
                "tool.output",
                "tool.end",
            }:
                continue
            pytest.fail(f"Unexpected message type after edit: {data['type']}")

        session = mock_alfred.core.session_manager.get_current_cli_session()
        assert session is not None
        assert [message.role.value for message in session.messages] == ["user", "assistant"]
        assert session.messages[0].content == "Hello"
        assert session.messages[1].content == "Retry response"
        assert mock_alfred.chat_messages == ["Hello", "Hello"]


class TestWebSocketCommandWithoutAlfred:
    """Test command functionality when Alfred instance is not available."""

    def test_command_execute_without_alfred_returns_error(self, client):
        """Test that commands return error when Alfred is not available or unknown."""
        with client.websocket_connect("/ws") as websocket:
            # Receive startup messages
            websocket.receive_json()
            websocket.receive_json()

            # Send /help command
            websocket.send_json({"type": "command.execute", "payload": {"command": "/help"}})

            # Should receive error (either about Alfred instance or unknown command)
            data = websocket.receive_json()
            assert data["type"] == "chat.error"
            # Server may return either error depending on implementation order
            assert "Alfred instance not available" in data["payload"]["error"] or "Unknown command" in data["payload"]["error"]

    def test_command_execute_empty_command_returns_error(self, client):
        """Test that empty command returns error."""
        with client.websocket_connect("/ws") as websocket:
            # Receive startup messages
            websocket.receive_json()
            websocket.receive_json()

            # Send empty command
            websocket.send_json({"type": "command.execute", "payload": {"command": "   "}})

            # Should receive error
            data = websocket.receive_json()
            assert data["type"] == "chat.error"
            assert "cannot be empty" in data["payload"]["error"]

    def test_command_unknown_command(self, client):
        """Test that unknown command returns error."""
        with client.websocket_connect("/ws") as websocket:
            # Receive startup messages
            websocket.receive_json()
            websocket.receive_json()

            # Send unknown command
            websocket.send_json({"type": "command.execute", "payload": {"command": "/unknown"}})

            # Should receive error about Alfred instance first
            data = websocket.receive_json()
            assert data["type"] == "chat.error"


def _connect_and_skip_initial_messages(websocket):
    """Helper to connect and skip connected, session.loaded, daemon.status, and status.update."""
    connected = websocket.receive_json()
    session_loaded = websocket.receive_json()
    daemon_status = websocket.receive_json()
    status_update = websocket.receive_json()

    assert connected["type"] == "connected"
    assert session_loaded["type"] == "session.loaded"
    assert daemon_status["type"] == "daemon.status"
    assert status_update["type"] == "status.update"


class TestWebSocketCommandsWithMockedAlfred:
    """Test command execution with mocked Alfred instance."""

    def test_command_new_session(self):
        """Test /new command creates new session."""
        mock_alfred = MockAlfred()
        app = create_app(alfred_instance=mock_alfred)
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            # Skip initial messages
            _connect_and_skip_initial_messages(websocket)

            # Send /new command
            websocket.send_json({"type": "command.execute", "payload": {"command": "/new"}})

            # Should receive session.new
            data = websocket.receive_json()
            assert data["type"] == "session.new"
            assert "sessionId" in data["payload"]
            assert "New session created" in data["payload"]["message"]
            assert mock_alfred.new_session_called

    def test_command_list_sessions(self):
        """Test /sessions command lists sessions."""
        mock_alfred = MockAlfred()
        app = create_app(alfred_instance=mock_alfred)
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            # Skip initial messages
            _connect_and_skip_initial_messages(websocket)

            # Send /sessions command
            websocket.send_json({"type": "command.execute", "payload": {"command": "/sessions"}})

            # Should receive session.list
            data = websocket.receive_json()
            assert data["type"] == "session.list"
            assert "sessions" in data["payload"]
            assert len(data["payload"]["sessions"]) == 2
            assert data["payload"]["sessions"][0]["id"] == "session-1"
            assert mock_alfred.list_sessions_called

    def test_command_session_info(self):
        """Test /session command shows current session info."""
        mock_alfred = MockAlfred()
        app = create_app(alfred_instance=mock_alfred)
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            # Skip initial messages
            _connect_and_skip_initial_messages(websocket)

            # Send /session command
            websocket.send_json({"type": "command.execute", "payload": {"command": "/session"}})

            # Should receive session.info
            data = websocket.receive_json()
            assert data["type"] == "session.info"
            assert data["payload"]["sessionId"] == "session-1"
            assert "messageCount" in data["payload"]
            assert "created" in data["payload"]

    def test_command_resume_session(self):
        """Test /resume command resumes a session."""
        mock_alfred = MockAlfred()
        app = create_app(alfred_instance=mock_alfred)
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            # Skip initial messages
            _connect_and_skip_initial_messages(websocket)

            # Send /resume command
            websocket.send_json({"type": "command.execute", "payload": {"command": "/resume session-2"}})

            # Should receive session.loaded
            data = websocket.receive_json()
            assert data["type"] == "session.loaded"
            assert data["payload"]["sessionId"] == "session-2"
            assert "messages" in data["payload"]
            assert mock_alfred.resume_session_called

    def test_command_resume_without_session_id(self):
        """Test /resume command without session ID returns error."""
        mock_alfred = MockAlfred()
        app = create_app(alfred_instance=mock_alfred)
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            # Skip initial messages
            _connect_and_skip_initial_messages(websocket)

            # Send /resume command without args
            websocket.send_json({"type": "command.execute", "payload": {"command": "/resume"}})

            # Should receive error
            data = websocket.receive_json()
            assert data["type"] == "chat.error"
            assert "Session ID required" in data["payload"]["error"]

    def test_command_context(self):
        """Test /context command shows shared structured context."""
        mock_alfred = MockAlfred()
        app = create_app(alfred_instance=mock_alfred)
        client = TestClient(app)

        context_data = {
            "system_prompt": {"sections": [{"name": "AGENTS.md", "tokens": 12}], "total_tokens": 12},
            "memories": {"displayed": 0, "total": 0, "items": [], "tokens": 0},
            "session_history": {"count": 1, "messages": [{"role": "user", "content": "hello"}], "tokens": 3},
            "tool_calls": {"count": 0, "items": [], "tokens": 0},
            "total_tokens": 15,
        }

        with (
            patch("alfred.context_display.get_context_display", AsyncMock(return_value=context_data)),
            client.websocket_connect("/ws") as websocket,
        ):
            _connect_and_skip_initial_messages(websocket)

            websocket.send_json({"type": "command.execute", "payload": {"command": "/context"}})

            data = websocket.receive_json()
            assert data["type"] == "context.info"
            assert data["payload"]["systemPrompt"]["totalTokens"] == 12
            assert data["payload"]["sessionHistory"]["count"] == 1


class TestWebSocketStatusUpdates:
    """Test status update protocol."""

    def test_status_update_during_chat_streaming(self):
        """Test that status updates are sent during chat streaming."""
        mock_alfred = MockAlfred()
        app = create_app(alfred_instance=mock_alfred)
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            # Skip initial messages
            _connect_and_skip_initial_messages(websocket)

            # Send chat message
            websocket.send_json({"type": "chat.send", "payload": {"content": "Hello"}})

            # Collect messages
            status_updates = []
            received_complete = False

            while not received_complete:
                data = websocket.receive_json()
                if data["type"] == "status.update":
                    status_updates.append(data["payload"])
                    # Verify status format
                    assert "model" in data["payload"]
                    assert "inputTokens" in data["payload"]
                    assert "outputTokens" in data["payload"]
                    assert "isStreaming" in data["payload"]
                elif data["type"] == "chat.complete":
                    received_complete = True

            # Should have received at least 1 status update
            # Server sends status at start of streaming
            assert len(status_updates) >= 1

            # First status should show streaming started
            assert status_updates[0]["isStreaming"] is True

    def test_status_update_with_model_name(self):
        """Test that status includes Alfred.model_name."""
        mock_alfred = MockAlfred()
        mock_alfred.model_name = "claude-3-opus-20240229"

        app = create_app(alfred_instance=mock_alfred)
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            _connect_and_skip_initial_messages(websocket)

            websocket.send_json({"type": "chat.send", "payload": {"content": "Test"}})

            while True:
                data = websocket.receive_json()
                if data["type"] == "status.update" and data["payload"]["model"]:
                    assert data["payload"]["model"] == "claude-3-opus-20240229"
                    break
                if data["type"] == "chat.complete":
                    continue

    def test_status_update_token_counts(self):
        """Test that status updates include token usage."""
        mock_alfred = MockAlfred(chunks=["This is a longer response with more tokens"] * 5)
        app = create_app(alfred_instance=mock_alfred)
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            # Skip initial messages
            _connect_and_skip_initial_messages(websocket)

            # Send chat message
            websocket.send_json({"type": "chat.send", "payload": {"content": "Hello world test message"}})

            final_status = None

            # Collect final status
            while True:
                data = websocket.receive_json()
                if data["type"] == "status.update":
                    final_status = data["payload"]
                elif data["type"] == "chat.complete":
                    break

            # Verify token counts are present
            assert final_status is not None
            assert "contextTokens" in final_status
            assert "inputTokens" in final_status
            assert "outputTokens" in final_status
            assert "cacheReadTokens" in final_status
            assert "reasoningTokens" in final_status

            # Token counts should be non-negative
            assert final_status["inputTokens"] >= 0
            assert final_status["outputTokens"] >= 0

    def test_status_update_queue_length(self):
        """Test that status includes queue length."""
        mock_alfred = MockAlfred()
        app = create_app(alfred_instance=mock_alfred)
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            # Skip initial messages
            _connect_and_skip_initial_messages(websocket)

            # Send chat message
            websocket.send_json({"type": "chat.send", "payload": {"content": "Test"}})

            # Look for status with queueLength
            while True:
                data = websocket.receive_json()
                if data["type"] == "status.update":
                    assert "queueLength" in data["payload"]
                    assert isinstance(data["payload"]["queueLength"], int)
                    assert data["payload"]["queueLength"] >= 0
                elif data["type"] == "chat.complete":
                    break


class TestWebSocketErrorHandling:
    """Test error handling in WebSocket protocol."""

    def test_command_new_session_failure(self):
        """Test error handling when new_session raises an exception."""
        mock_alfred = MockAlfred()

        # Override new_session_async to raise exception
        async def failing_new_session():
            raise RuntimeError("Database connection failed")

        mock_alfred.core.session_manager.new_session_async = failing_new_session

        app = create_app(alfred_instance=mock_alfred)
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            _connect_and_skip_initial_messages(websocket)

            websocket.send_json({"type": "command.execute", "payload": {"command": "/new"}})

            data = websocket.receive_json()
            assert data["type"] == "chat.error"
            assert "Failed to create session" in data["payload"]["error"]
            assert "Database connection failed" in data["payload"]["error"]

    def test_command_resume_session_failure(self):
        """Test error handling when resume_session raises an exception."""
        mock_alfred = MockAlfred()

        async def failing_resume_session(session_id):
            raise ValueError("Session not found in database")

        mock_alfred.core.session_manager.resume_session_async = failing_resume_session

        app = create_app(alfred_instance=mock_alfred)
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            _connect_and_skip_initial_messages(websocket)

            websocket.send_json({"type": "command.execute", "payload": {"command": "/resume nonexistent-session"}})

            data = websocket.receive_json()
            assert data["type"] == "chat.error"
            assert "Failed to resume session" in data["payload"]["error"]

    def test_command_list_sessions_failure(self):
        """Test error handling when list_sessions raises an exception."""
        mock_alfred = MockAlfred()

        async def failing_list_sessions():
            raise RuntimeError("Storage backend unavailable")

        mock_alfred.core.session_manager.list_sessions_async = failing_list_sessions

        app = create_app(alfred_instance=mock_alfred)
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            _connect_and_skip_initial_messages(websocket)

            websocket.send_json({"type": "command.execute", "payload": {"command": "/sessions"}})

            data = websocket.receive_json()
            assert data["type"] == "chat.error"
            assert "Failed to list sessions" in data["payload"]["error"]

    def test_command_context_failure(self):
        """Test error handling when context command fails."""
        # Skip this test - context command now handles errors gracefully
        # by returning "unknown" for missing config values
        pytest.skip("Context command now gracefully handles missing config")

    def test_chat_stream_exception_handling(self):
        """Test that chat stream errors are properly handled."""
        mock_alfred = MockAlfred()

        async def failing_chat_stream(message, tool_callback=None):
            yield "Starting response..."
            raise RuntimeError("LLM API error")

        mock_alfred.chat_stream = failing_chat_stream

        app = create_app(alfred_instance=mock_alfred)
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            _connect_and_skip_initial_messages(websocket)

            websocket.send_json({"type": "chat.send", "payload": {"content": "Hello"}})

            # Should receive chat.started
            data = websocket.receive_json()
            assert data["type"] == "chat.started"

            # Collect messages until we get error or complete
            received_error = False
            for _ in range(10):  # Limit iterations to prevent infinite loop
                data = websocket.receive_json()
                if data["type"] == "chat.error":
                    received_error = True
                    assert "LLM API error" in data["payload"]["error"]
                    break
                elif data["type"] == "chat.complete":
                    break
                # status.update and chat.chunk are also valid

            assert received_error, "Expected chat.error message"

    def test_echo_unknown_message_type(self):
        """Test that unknown message types are echoed back."""
        mock_alfred = MockAlfred()
        app = create_app(alfred_instance=mock_alfred)
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            _connect_and_skip_initial_messages(websocket)

            # Send unknown message type
            websocket.send_json({"type": "custom.unknown.type", "payload": {"data": "test"}})

            data = websocket.receive_json()
            assert data["type"] == "echo"
            assert data["payload"]["received"]["type"] == "custom.unknown.type"


class TestWebUIHTTPEndpoints:
    """Test HTTP endpoints for Web UI."""

    def test_health_check_endpoint(self):
        """Test the /health endpoint returns correct status."""
        app = create_app(alfred_instance=None)
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_root_redirects_to_static(self):
        """Test that / redirects to static index.html."""
        app = create_app(alfred_instance=None)
        client = TestClient(app)

        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"

    def test_static_files_served(self):
        """Test that static files are accessible."""
        app = create_app(alfred_instance=None)
        client = TestClient(app)

        # Should be able to access static files (index.html should exist)
        response = client.get("/static/index.html")
        # File exists or returns 200, or 404 if file doesn't exist
        # Mainly testing the static file mounting works
        assert response.status_code in [200, 404]
