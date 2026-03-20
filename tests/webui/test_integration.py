"""Integration tests for Alfred Web UI.

These tests verify end-to-end functionality through the WebSocket connection,
testing the complete flow from connection establishment through message handling.
"""

import pytest
from fastapi.testclient import TestClient

from alfred.interfaces.webui.server import create_app


class MockSession:
    """Mock session for integration testing."""

    class Message:
        """Mock message."""

        def __init__(self, role, content):
            from datetime import datetime
            self.role = MockSession.Role(role)
            self.content = content
            self.id = f"msg-{datetime.now().timestamp()}"
            self.created_at = datetime.now()

    class Role:
        """Mock role."""

        def __init__(self, value):
            self.value = value

    def __init__(self, session_id="test-session-123", messages=None):
        from datetime import datetime
        self.session_id = session_id
        self.messages = messages or []
        self.created_at = datetime.now()
        self.summary = "Test session summary"
        self.meta = MockSession.Meta(session_id)

    class Meta:
        """Mock session meta."""

        def __init__(self, session_id):
            self.session_id = session_id


class MockAlfred:
    """Mock Alfred instance for integration testing."""

    def __init__(self, chunks=None, sessions=None, config=None):
        self.chunks = chunks or ["Hello", ", ", "this", " is", " a", " test", " response", "."]
        self.chat_called = False
        self.last_message = None
        self._sessions = sessions or [
            MockSession("session-1"),
            MockSession("session-2"),
        ]
        self._current_session = self._sessions[0] if self._sessions else None
        self.new_session_called = False
        self.resume_session_called = False
        self.list_sessions_called = False
        self.config = config or {"model": "claude-3-sonnet-20240229"}

    async def chat_stream(self, message, tool_callback=None):
        """Mock chat stream that yields chunks."""
        self.chat_called = True
        self.last_message = message
        for chunk in self.chunks:
            yield chunk

    async def new_session(self):
        """Mock creating a new session."""
        self.new_session_called = True
        new_session = MockSession(f"new-session-{len(self._sessions) + 1}")
        self._sessions.insert(0, new_session)
        self._current_session = new_session
        return new_session

    async def resume_session(self, session_id):
        """Mock resuming a session."""
        self.resume_session_called = True
        for session in self._sessions:
            if session.session_id == session_id:
                self._current_session = session
                # Add a mock message to the session
                session.messages = [MockSession.Message("user", "Hello")]
                return session
        raise ValueError(f"Session {session_id} not found")

    async def list_sessions(self, limit=10):
        """Mock listing sessions."""
        self.list_sessions_called = True
        return self._sessions[:limit]

    @property
    def current_session(self):
        """Get current session."""
        return self._current_session

    def get_context(self):
        """Mock getting context."""
        return {
            "cwd": "/workspace/alfred-prd",
            "files": ["README.md", "pyproject.toml"],
            "system_info": {"platform": "linux"},
        }


@pytest.fixture
def mock_alfred():
    """Create a mock Alfred instance."""
    return MockAlfred()


@pytest.fixture
def client(mock_alfred):
    """Create test client with mocked Alfred."""
    app = create_app(alfred_instance=mock_alfred)
    return TestClient(app), mock_alfred


class TestFullChatFlow:
    """End-to-end tests for complete chat flows."""

    def test_full_chat_flow_single_message(self, client):
        """Test complete flow: connect, send message, receive streaming response.

        Verifies:
        - WebSocket connection established
        - Chat message sent successfully
        - Streaming response received in correct order
        - Status updates received during streaming
        - Final completion message received
        - All message IDs are consistent
        """
        test_client, mock_alfred = client

        with test_client.websocket_connect("/ws") as websocket:
            # Step 1: Receive connection confirmation
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert "payload" in data

            # Step 2: Send a chat message
            test_message = "What is the weather today?"
            websocket.send_json({
                "type": "chat.send",
                "payload": {"content": test_message}
            })

            # Step 3: Receive chat.started
            data = websocket.receive_json()
            assert data["type"] == "chat.started"
            assert "messageId" in data["payload"]
            message_id = data["payload"]["messageId"]
            assert data["payload"]["role"] == "assistant"

            # Step 4: Collect streaming response
            received_chunks = []
            status_updates = []
            received_complete = False

            while not received_complete:
                data = websocket.receive_json()

                if data["type"] == "chat.chunk":
                    received_chunks.append(data["payload"]["content"])
                    assert data["payload"]["messageId"] == message_id
                elif data["type"] == "status.update":
                    status_updates.append(data["payload"])
                    # Verify status format
                    assert "model" in data["payload"]
                    assert "inputTokens" in data["payload"]
                    assert "outputTokens" in data["payload"]
                    assert "isStreaming" in data["payload"]
                elif data["type"] == "chat.complete":
                    assert data["payload"]["messageId"] == message_id
                    assert "finalContent" in data["payload"]
                    assert "usage" in data["payload"]
                    received_complete = True
                else:
                    pytest.fail(f"Unexpected message type: {data['type']}")

            # Step 5: Verify results
            assert received_chunks == mock_alfred.chunks
            assert mock_alfred.chat_called
            assert mock_alfred.last_message == test_message
            assert len(status_updates) >= 1  # At least one status update

    def test_full_chat_flow_multiple_messages(self, client):
        """Test sending multiple messages in sequence.

        Verifies:
        - Multiple chat messages can be sent in one session
        - Each message gets its own message ID
        - Message IDs are unique per message
        """
        test_client, mock_alfred = client

        with test_client.websocket_connect("/ws") as websocket:
            # Receive connection confirmation
            websocket.receive_json()

            message_ids = []

            for i in range(3):
                # Send message
                websocket.send_json({
                    "type": "chat.send",
                    "payload": {"content": f"Message {i + 1}"}
                })

                # Receive chat.started (may be preceded by status updates)
                while True:
                    data = websocket.receive_json()
                    if data["type"] == "chat.started":
                        message_id = data["payload"]["messageId"]
                        message_ids.append(message_id)
                        break
                    elif data["type"] == "status.update":
                        continue

                # Collect response
                while True:
                    data = websocket.receive_json()
                    if data["type"] == "chat.complete":
                        break
                    elif data["type"] == "status.update":
                        continue
                    # Ignore other message types

            # Verify all message IDs are unique
            assert len(message_ids) == 3
            assert len(set(message_ids)) == 3  # All unique

    def test_full_chat_flow_with_reasoning(self, client):
        """Test chat flow with reasoning blocks.

        Verifies:
        - Reasoning chunks are properly identified and sent
        - Reasoning and content chunks are separated
        - Final content includes both reasoning and response
        """
        test_client, mock_alfred = client

        # Setup reasoning chunks
        mock_alfred.chunks = [
            "[REASONING]",
            "Let me think about this question",
            ". I need to consider the context",
            "[/REASONING]",
            "Based on my analysis, the answer is 42."
        ]

        with test_client.websocket_connect("/ws") as websocket:
            # Receive connection confirmation
            websocket.receive_json()

            # Send message
            websocket.send_json({
                "type": "chat.send",
                "payload": {"content": "What is the meaning of life?"}
            })

            # Collect response
            reasoning_chunks = []
            content_chunks = []

            while True:
                data = websocket.receive_json()

                if data["type"] == "reasoning.chunk":
                    reasoning_chunks.append(data["payload"]["content"])
                elif data["type"] == "chat.chunk":
                    content_chunks.append(data["payload"]["content"])
                elif data["type"] == "chat.complete":
                    break
                elif data["type"] == "status.update":
                    continue

            # Verify reasoning was extracted
            assert len(reasoning_chunks) > 0
            assert "Let me think" in "".join(reasoning_chunks)
            assert "answer is 42" in "".join(content_chunks)


class TestSessionManagementFlow:
    """End-to-end tests for session management commands."""

    def test_session_create_new_session(self, client):
        """Test creating a new session via /new command.

        Verifies:
        - /new command creates a new session
        - New session ID is returned
        - Confirmation message is sent
        """
        test_client, mock_alfred = client
        original_session_count = len(mock_alfred._sessions)

        with test_client.websocket_connect("/ws") as websocket:
            # Receive connection confirmation
            websocket.receive_json()

            # Send /new command
            websocket.send_json({
                "type": "command.execute",
                "payload": {"command": "/new"}
            })

            # Receive session.new response
            data = websocket.receive_json()
            assert data["type"] == "session.new"
            assert "sessionId" in data["payload"]
            assert "New session created" in data["payload"]["message"]

            # Verify session was created
            assert mock_alfred.new_session_called
            assert len(mock_alfred._sessions) == original_session_count + 1

    def test_session_list_sessions(self, client):
        """Test listing sessions via /sessions command.

        Verifies:
        - /sessions command returns list of sessions
        - Each session has required fields (id, summary, created)
        """
        test_client, mock_alfred = client

        with test_client.websocket_connect("/ws") as websocket:
            # Receive connection confirmation
            websocket.receive_json()

            # Send /sessions command
            websocket.send_json({
                "type": "command.execute",
                "payload": {"command": "/sessions"}
            })

            # Receive session.list response
            data = websocket.receive_json()
            assert data["type"] == "session.list"
            assert "sessions" in data["payload"]
            assert len(data["payload"]["sessions"]) == 2

            # Verify session structure
            for session in data["payload"]["sessions"]:
                assert "id" in session
                assert "summary" in session
                assert "created" in session

            assert mock_alfred.list_sessions_called

    def test_session_resume_session(self, client):
        """Test resuming a session via /resume command.

        Verifies:
        - /resume <session_id> switches to specified session
        - Session messages are loaded
        - Confirmation message includes session ID
        """
        test_client, mock_alfred = client
        target_session_id = "session-2"

        with test_client.websocket_connect("/ws") as websocket:
            # Receive connection confirmation
            websocket.receive_json()

            # Send /resume command
            websocket.send_json({
                "type": "command.execute",
                "payload": {"command": f"/resume {target_session_id}"}
            })

            # Receive session.loaded response
            data = websocket.receive_json()
            assert data["type"] == "session.loaded"
            assert data["payload"]["sessionId"] == target_session_id
            assert "messages" in data["payload"]

            assert mock_alfred.resume_session_called

    def test_session_resume_without_id(self, client):
        """Test /resume command without session ID.

        Verifies:
        - Error is returned when session ID is missing
        - Error message is descriptive
        """
        test_client, mock_alfred = client

        with test_client.websocket_connect("/ws") as websocket:
            # Receive connection confirmation
            websocket.receive_json()

            # Send /resume without ID
            websocket.send_json({
                "type": "command.execute",
                "payload": {"command": "/resume"}
            })

            # Receive error response
            data = websocket.receive_json()
            assert data["type"] == "chat.error"
            assert "Session ID required" in data["payload"]["error"]

    def test_session_full_workflow(self, client):
        """Test complete session management workflow.

        Verifies:
        - Create new session
        - List sessions shows new session
        - Resume original session
        - List sessions again
        """
        test_client, mock_alfred = client

        with test_client.websocket_connect("/ws") as websocket:
            # Receive connection confirmation
            websocket.receive_json()

            # Step 1: Create new session
            websocket.send_json({
                "type": "command.execute",
                "payload": {"command": "/new"}
            })
            data = websocket.receive_json()
            assert data["type"] == "session.new"
            new_session_id = data["payload"]["sessionId"]

            # Step 2: List sessions
            websocket.send_json({
                "type": "command.execute",
                "payload": {"command": "/sessions"}
            })
            data = websocket.receive_json()
            assert data["type"] == "session.list"
            assert len(data["payload"]["sessions"]) == 3  # Original 2 + new 1

            # Step 3: Resume original session
            websocket.send_json({
                "type": "command.execute",
                "payload": {"command": "/resume session-1"}
            })
            data = websocket.receive_json()
            assert data["type"] == "session.loaded"
            assert data["payload"]["sessionId"] == "session-1"

            # Step 4: Get current session info
            websocket.send_json({
                "type": "command.execute",
                "payload": {"command": "/session"}
            })
            data = websocket.receive_json()
            assert data["type"] == "session.info"
            assert data["payload"]["sessionId"] == "session-1"


class TestErrorHandling:
    """Tests for error scenarios and edge cases."""

    def test_error_chat_without_alfred(self):
        """Test error when Alfred instance is not available.

        Verifies:
        - Appropriate error is returned
        - Connection remains open
        """
        app = create_app(alfred_instance=None)
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            # Receive connection confirmation
            websocket.receive_json()

            # Send chat message
            websocket.send_json({
                "type": "chat.send",
                "payload": {"content": "Hello"}
            })

            # Receive error
            data = websocket.receive_json()
            assert data["type"] == "chat.error"
            assert "Alfred instance not available" in data["payload"]["error"]

            # Verify connection is still open
            websocket.send_json({"type": "ping"})
            data = websocket.receive_json()
            assert data["type"] == "pong"

    def test_error_invalid_json(self, client):
        """Test handling of invalid JSON messages.

        Verifies:
        - Error is returned for invalid JSON
        - Connection remains open
        """
        test_client, _ = client

        with test_client.websocket_connect("/ws") as websocket:
            # Receive connection confirmation
            websocket.receive_json()

            # Send invalid JSON
            websocket.send_text("not valid json {{{")

            # Receive error
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "Invalid JSON" in data["payload"]["error"]

            # Verify connection is still open
            websocket.send_json({"type": "ping"})
            data = websocket.receive_json()
            assert data["type"] == "pong"

    def test_error_unknown_command(self, client):
        """Test handling of unknown commands.

        Verifies:
        - Error is returned for unknown commands
        - Connection remains open
        """
        test_client, _ = client

        with test_client.websocket_connect("/ws") as websocket:
            # Receive connection confirmation
            websocket.receive_json()

            # Send unknown command
            websocket.send_json({
                "type": "command.execute",
                "payload": {"command": "/unknowncommand"}
            })

            # Receive error
            data = websocket.receive_json()
            assert data["type"] == "chat.error"

            # Verify connection is still open
            websocket.send_json({"type": "ping"})
            data = websocket.receive_json()
            assert data["type"] == "pong"

    def test_error_empty_message(self, client):
        """Test handling of empty chat messages.

        Verifies:
        - Error is returned for empty content
        - Connection remains open
        """
        test_client, _ = client

        with test_client.websocket_connect("/ws") as websocket:
            # Receive connection confirmation
            websocket.receive_json()

            # Send empty message
            websocket.send_json({
                "type": "chat.send",
                "payload": {"content": "   "}
            })

            # Receive error
            data = websocket.receive_json()
            assert data["type"] == "chat.error"
            assert "cannot be empty" in data["payload"]["error"]

    def test_error_resume_nonexistent_session(self, client):
        """Test resuming a session that doesn't exist.

        Verifies:
        - Error is returned for non-existent session
        - Connection remains open
        """
        test_client, _ = client

        with test_client.websocket_connect("/ws") as websocket:
            # Receive connection confirmation
            websocket.receive_json()

            # Try to resume non-existent session
            websocket.send_json({
                "type": "command.execute",
                "payload": {"command": "/resume nonexistent-session"}
            })

            # Receive error
            data = websocket.receive_json()
            assert data["type"] == "chat.error"
            assert "not found" in data["payload"]["error"].lower()

    def test_recovery_after_error(self, client):
        """Test that normal operation resumes after an error.

        Verifies:
        - Error occurs
        - Subsequent valid requests work correctly
        """
        test_client, mock_alfred = client

        with test_client.websocket_connect("/ws") as websocket:
            # Receive connection confirmation
            websocket.receive_json()

            # Step 1: Cause an error (empty message)
            websocket.send_json({
                "type": "chat.send",
                "payload": {"content": ""}
            })
            data = websocket.receive_json()
            assert data["type"] == "chat.error"

            # Step 2: Send valid message
            websocket.send_json({
                "type": "chat.send",
                "payload": {"content": "Valid message after error"}
            })

            # Should receive chat.started
            data = websocket.receive_json()
            assert data["type"] == "chat.started"

            # Complete the chat
            while True:
                data = websocket.receive_json()
                if data["type"] == "chat.complete":
                    break

            assert mock_alfred.chat_called


class TestConcurrentOperations:
    """Tests for concurrent and rapid operations."""

    def test_rapid_ping_pong(self, client):
        """Test rapid ping/pong exchanges.

        Verifies:
        - Server handles rapid messages
        - All pongs are received
        - No message loss
        """
        test_client, _ = client

        with test_client.websocket_connect("/ws") as websocket:
            # Receive connection confirmation
            websocket.receive_json()

            # Send 10 rapid pings
            for _ in range(10):
                websocket.send_json({"type": "ping"})

            # Receive all pongs
            pong_count = 0
            for _ in range(10):
                data = websocket.receive_json()
                if data["type"] == "pong":
                    pong_count += 1

            assert pong_count == 10

    def test_multiple_commands_in_sequence(self, client):
        """Test multiple commands sent in rapid succession.

        Verifies:
        - All commands are processed
        - Responses are received in order
        """
        test_client, mock_alfred = client

        with test_client.websocket_connect("/ws") as websocket:
            # Receive connection confirmation
            websocket.receive_json()

            # Send multiple commands rapidly
            commands = ["/session", "/context", "/sessions"]
            for cmd in commands:
                websocket.send_json({
                    "type": "command.execute",
                    "payload": {"command": cmd}
                })

            # Collect responses
            responses = []
            for _ in range(len(commands)):
                data = websocket.receive_json()
                responses.append(data["type"])

            # Verify all commands were processed
            assert "session.info" in responses
            assert "context.info" in responses
            assert "session.list" in responses
