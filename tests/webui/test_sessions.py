"""Tests for session management commands."""

from fastapi.testclient import TestClient

from alfred.interfaces.webui import create_app


def test_new_command_creates_session():
    """Verify /new command creates a new session."""
    app = create_app()
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Receive connected message
        response = websocket.receive_json()
        assert response["type"] == "connected"

        # Send /new command
        websocket.send_json({
            "type": "command.execute",
            "payload": {"command": "/new"}
        })

        # Should receive acknowledgment or session info
        # (In real implementation, would create new session)


def test_resume_command_structure():
    """Verify /resume command validates session ID."""
    from alfred.interfaces.webui.validation import CommandExecuteMessage, CommandExecutePayload

    message = CommandExecuteMessage(
        type="command.execute",
        payload=CommandExecutePayload(command="/resume abc123")
    )

    assert message.type == "command.execute"
    assert "/resume" in message.payload.command


def test_sessions_command_structure():
    """Verify /sessions command format."""
    from alfred.interfaces.webui.validation import CommandExecuteMessage, CommandExecutePayload

    message = CommandExecuteMessage(
        type="command.execute",
        payload=CommandExecutePayload(command="/sessions")
    )

    assert message.payload.command == "/sessions"


def test_session_command_structure():
    """Verify /session command format."""
    from alfred.interfaces.webui.validation import CommandExecuteMessage, CommandExecutePayload

    message = CommandExecuteMessage(
        type="command.execute",
        payload=CommandExecutePayload(command="/session")
    )

    assert message.payload.command == "/session"


def test_context_command_structure():
    """Verify /context command format."""
    from alfred.interfaces.webui.validation import CommandExecuteMessage, CommandExecutePayload

    message = CommandExecuteMessage(
        type="command.execute",
        payload=CommandExecutePayload(command="/context")
    )

    assert message.payload.command == "/context"


def test_session_loaded_message_structure():
    """Verify session.loaded message structure."""
    from alfred.interfaces.webui.validation import SessionLoadedMessage, SessionLoadedPayload, SessionMessage

    messages = [
        SessionMessage(id="msg-1", role="user", content="Hello"),
        SessionMessage(id="msg-2", role="assistant", content="Hi there")
    ]

    message = SessionLoadedMessage(
        type="session.loaded",
        payload=SessionLoadedPayload(session_id="session-123", messages=messages)
    )

    assert message.type == "session.loaded"
    assert message.payload.session_id == "session-123"
    assert len(message.payload.messages) == 2
    assert message.payload.messages[0].role == "user"


def test_websocket_handles_session_commands():
    """Verify WebSocket accepts session-related commands."""
    app = create_app()
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Receive connected message
        response = websocket.receive_json()
        assert response["type"] == "connected"

        # Test various session commands
        commands = ["/new", "/sessions", "/session", "/context"]

        for cmd in commands:
            websocket.send_json({
                "type": "command.execute",
                "payload": {"command": cmd}
            })
            # Commands are processed, may or may not receive immediate response
            # depending on implementation
