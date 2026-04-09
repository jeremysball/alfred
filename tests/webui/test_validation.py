"""Tests for WebSocket message validation using Pydantic models."""

import pytest
from pydantic import ValidationError

from alfred.interfaces.webui.validation import (
    AckMessage,
    AckPayload,
    ChatCancelMessage,
    ChatCancelledMessage,
    ChatCancelledPayload,
    ChatChunkMessage,
    ChatChunkPayload,
    ChatCompleteMessage,
    ChatCompletePayload,
    ChatEditMessage,
    ChatEditPayload,
    ChatErrorMessage,
    ChatErrorPayload,
    ChatSendMessage,
    ChatSendPayload,
    CommandExecuteMessage,
    CommandExecutePayload,
    CompletionRequestMessage,
    CompletionRequestPayload,
    DaemonStatusInfo,
    DaemonStatusMessage,
    DaemonStatusPayload,
    SessionLoadedMessage,
    SessionLoadedPayload,
    SessionMessage,
    TextBlock,
    StatusUpdateMessage,
    StatusUpdatePayload,
    ToastMessage,
    ToastPayload,
    ToolEndMessage,
    ToolEndPayload,
    ToolStartMessage,
    ToolStartPayload,
    UsageInfo,
    create_validation_error_response,
    validate_client_message,
)

# =============================================================================
# Chat Send Tests
# =============================================================================


def test_chat_send_payload_valid():
    """Verify ChatSendPayload accepts valid data."""
    payload = ChatSendPayload(content="Hello Alfred")
    assert payload.content == "Hello Alfred"
    assert payload.queue is False


def test_chat_send_payload_with_queue():
    """Verify ChatSendPayload accepts queue parameter."""
    payload = ChatSendPayload(content="Hello", queue=True)
    assert payload.queue is True


def test_chat_send_payload_empty_content_raises():
    """Verify ChatSendPayload rejects empty content."""
    with pytest.raises(ValidationError):
        ChatSendPayload(content="")


def test_chat_send_message_valid():
    """Verify ChatSendMessage accepts valid data."""
    message = ChatSendMessage(type="chat.send", payload=ChatSendPayload(content="Hello"))
    assert message.type == "chat.send"
    assert message.payload.content == "Hello"


# =============================================================================
# Command Execute Tests
# =============================================================================


def test_command_execute_message_valid():
    """Verify CommandExecuteMessage accepts valid data."""
    message = CommandExecuteMessage(type="command.execute", payload=CommandExecutePayload(command="/new"))
    assert message.type == "command.execute"
    assert message.payload.command == "/new"


def test_command_execute_empty_command_raises():
    """Verify CommandExecutePayload rejects empty command."""
    with pytest.raises(ValidationError):
        CommandExecutePayload(command="")


# =============================================================================
# Completion Request Tests
# =============================================================================


def test_completion_request_valid():
    """Verify CompletionRequestMessage accepts valid data."""
    message = CompletionRequestMessage(type="completion.request", payload=CompletionRequestPayload(text="Hello", cursor=5))
    assert message.type == "completion.request"
    assert message.payload.text == "Hello"
    assert message.payload.cursor == 5


def test_completion_request_negative_cursor_raises():
    """Verify CompletionRequestPayload rejects negative cursor."""
    with pytest.raises(ValidationError):
        CompletionRequestPayload(text="Hello", cursor=-1)


# =============================================================================
# Ack Tests
# =============================================================================


def test_ack_message_valid():
    """Verify AckMessage accepts valid data."""
    message = AckMessage(type="ack", payload=AckPayload(message_id="msg-123"))
    assert message.type == "ack"
    assert message.payload.message_id == "msg-123"


def test_ack_message_from_dict():
    """Verify AckMessage can be created from dict with messageId alias."""
    data = {"type": "ack", "payload": {"messageId": "msg-123"}}
    message = AckMessage.model_validate(data)
    assert message.payload.message_id == "msg-123"


# =============================================================================
# Server Message Tests
# =============================================================================


def test_chat_started_message():
    """Verify ChatStartedMessage structure."""
    from alfred.interfaces.webui.validation import ChatStartedMessage, ChatStartedPayload

    message = ChatStartedMessage(type="chat.started", payload=ChatStartedPayload(message_id="msg-123", role="assistant"))
    assert message.type == "chat.started"
    assert message.payload.message_id == "msg-123"
    assert message.payload.role == "assistant"


def test_chat_chunk_message():
    """Verify ChatChunkMessage structure."""
    message = ChatChunkMessage(type="chat.chunk", payload=ChatChunkPayload(message_id="msg-123", content="Hello"))
    assert message.type == "chat.chunk"
    assert message.payload.content == "Hello"


def test_chat_complete_message():
    """Verify ChatCompleteMessage structure."""
    usage = UsageInfo(input_tokens=10, output_tokens=20, cache_read_tokens=0, reasoning_tokens=5)
    message = ChatCompleteMessage(
        type="chat.complete", payload=ChatCompletePayload(message_id="msg-123", final_content="Complete response", usage=usage)
    )
    assert message.type == "chat.complete"
    assert message.payload.final_content == "Complete response"
    assert message.payload.usage.input_tokens == 10


def test_chat_error_message():
    """Verify ChatErrorMessage structure."""
    message = ChatErrorMessage(type="chat.error", payload=ChatErrorPayload(message_id="msg-123", error="Something went wrong"))
    assert message.type == "chat.error"
    assert message.payload.error == "Something went wrong"


def test_tool_start_message():
    """Verify ToolStartMessage structure."""
    message = ToolStartMessage(
        type="tool.start",
        payload=ToolStartPayload(tool_call_id="tool-1", tool_name="read", arguments={"path": "/tmp/file.txt"}, message_id="msg-123"),
    )
    assert message.type == "tool.start"
    assert message.payload.tool_name == "read"
    assert message.payload.arguments == {"path": "/tmp/file.txt"}


def test_tool_end_message():
    """Verify ToolEndMessage structure."""
    message = ToolEndMessage(type="tool.end", payload=ToolEndPayload(tool_call_id="tool-1", success=True, output="File contents"))
    assert message.type == "tool.end"
    assert message.payload.success is True
    assert message.payload.output == "File contents"


def test_daemon_status_message():
    """Verify DaemonStatusMessage structure."""
    message = DaemonStatusMessage(
        type="daemon.status",
        payload=DaemonStatusPayload(
            daemon=DaemonStatusInfo(
                state="running",
                pid=12345,
                socket_path="/home/node/.cache/alfred/notify.sock",
                socket_healthy=True,
                started_at="2026-03-21T12:00:00Z",
                uptime_seconds=183,
                last_heartbeat_at="2026-03-21T12:03:00Z",
                last_reload_at="2026-03-21T12:02:41Z",
                last_error=None,
            ),
        ),
    )
    assert message.type == "daemon.status"
    assert message.payload.daemon.state == "running"
    assert message.payload.daemon.pid == 12345
    assert message.payload.daemon.socket_healthy is True
    assert message.model_dump(by_alias=True) == {
        "type": "daemon.status",
        "payload": {
            "daemon": {
                "state": "running",
                "pid": 12345,
                "socketPath": "/home/node/.cache/alfred/notify.sock",
                "socketHealthy": True,
                "startedAt": "2026-03-21T12:00:00Z",
                "uptimeSeconds": 183,
                "lastHeartbeatAt": "2026-03-21T12:03:00Z",
                "lastReloadAt": "2026-03-21T12:02:41Z",
                "lastError": None,
            }
        },
    }


def test_status_update_message():
    """Verify StatusUpdateMessage structure."""
    message = StatusUpdateMessage(
        type="status.update",
        payload=StatusUpdatePayload(
            model="claude-3-sonnet",
            context_tokens=1000,
            input_tokens=50,
            output_tokens=25,
            cache_read_tokens=100,
            reasoning_tokens=10,
            queue_length=0,
            is_streaming=True,
        ),
    )
    assert message.type == "status.update"
    assert message.payload.model == "claude-3-sonnet"
    assert message.payload.is_streaming is True
    assert message.model_dump(by_alias=True) == {
        "type": "status.update",
        "payload": {
            "model": "claude-3-sonnet",
            "contextTokens": 1000,
            "contextWindowTokens": None,
            "inputTokens": 50,
            "outputTokens": 25,
            "cacheReadTokens": 100,
            "reasoningTokens": 10,
            "queueLength": 0,
            "isStreaming": True,
            "contextStatus": None,
        },
    }


def test_status_update_message_accepts_context_status_snapshot():
    """Verify StatusUpdateMessage accepts persistent context-health warnings."""
    message = StatusUpdateMessage(
        type="status.update",
        payload=StatusUpdatePayload(
            model="claude-3-sonnet",
            context_tokens=1000,
            input_tokens=50,
            output_tokens=25,
            cache_read_tokens=100,
            reasoning_tokens=10,
            queue_length=0,
            is_streaming=True,
            context_status={
                "blockedContextFiles": ["SOUL.md"],
                "conflictedContextFiles": [
                    {
                        "id": "soul",
                        "name": "soul",
                        "label": "SOUL.md",
                        "reason": "Conflicted managed prompt fragment prompts/voice.md blocks SOUL.md",
                    }
                ],
                "warnings": ["Disabled sections: TOOLS"],
            },
        ),
    )

    assert message.payload.context_status is not None
    assert message.payload.context_status.blocked_context_files == ["SOUL.md"]
    assert message.payload.context_status.conflicted_context_files[0].label == "SOUL.md"


def test_status_update_message_rejects_daemon_fields():
    """Verify StatusUpdateMessage rejects legacy daemon fields."""
    with pytest.raises(ValidationError):
        StatusUpdateMessage.model_validate(
            {
                "type": "status.update",
                "payload": {
                    "model": "claude-3-sonnet",
                    "contextTokens": 1000,
                    "inputTokens": 50,
                    "outputTokens": 25,
                    "cacheReadTokens": 100,
                    "reasoningTokens": 10,
                    "queueLength": 0,
                    "isStreaming": True,
                    "daemonStatus": "running",
                    "daemonPid": 12345,
                },
            }
        )


def test_toast_message():
    """Verify ToastMessage structure."""
    message = ToastMessage(type="toast", payload=ToastPayload(message="Hello", level="info"))
    assert message.type == "toast"
    assert message.payload.message == "Hello"
    assert message.payload.level == "info"


def test_session_loaded_message():
    """Verify SessionLoadedMessage structure."""
    messages = [
        SessionMessage(id="msg-1", role="user", content="Hello"),
        SessionMessage(
            id="msg-2",
            role="assistant",
            content="Hi there",
            text_blocks=[TextBlock(content="Hi there", sequence=0)],
        ),
    ]
    message = SessionLoadedMessage(type="session.loaded", payload=SessionLoadedPayload(session_id="session-123", messages=messages))
    assert message.type == "session.loaded"
    assert message.payload.session_id == "session-123"
    assert len(message.payload.messages) == 2
    assert message.payload.messages[0].role == "user"
    assert message.payload.messages[1].text_blocks[0].content == "Hi there"


# =============================================================================
# Validation Function Tests
# =============================================================================


def test_validate_client_message_chat_send():
    """Verify validate_client_message accepts valid chat.send."""
    data = {"type": "chat.send", "payload": {"content": "Hello"}}
    is_valid, message, error = validate_client_message(data)

    assert is_valid is True
    assert error == ""
    assert isinstance(message, ChatSendMessage)
    assert message.payload.content == "Hello"


def test_validate_client_message_command_execute():
    """Verify validate_client_message accepts valid command.execute."""
    data = {"type": "command.execute", "payload": {"command": "/new"}}
    is_valid, message, error = validate_client_message(data)

    assert is_valid is True
    assert isinstance(message, CommandExecuteMessage)


def test_validate_client_message_completion_request():
    """Verify validate_client_message accepts valid completion.request."""
    data = {"type": "completion.request", "payload": {"text": "Hello", "cursor": 5}}
    is_valid, message, error = validate_client_message(data)

    assert is_valid is True
    assert isinstance(message, CompletionRequestMessage)


def test_validate_client_message_ack():
    """Verify validate_client_message accepts valid ack."""
    data = {"type": "ack", "payload": {"messageId": "msg-123"}}
    is_valid, message, error = validate_client_message(data)

    assert is_valid is True
    assert isinstance(message, AckMessage)
    assert message.payload.message_id == "msg-123"


def test_validate_client_message_rejects_non_dict():
    """Verify validate_client_message rejects non-dict input."""
    is_valid, message, error = validate_client_message("not a dict")

    assert is_valid is False
    assert message is None
    assert "must be a JSON object" in error


def test_validate_client_message_rejects_missing_type():
    """Verify validate_client_message rejects missing type field."""
    data = {"payload": {"content": "Hello"}}
    is_valid, message, error = validate_client_message(data)

    assert is_valid is False
    assert "must have a 'type' field" in error


def test_validate_client_message_rejects_unknown_type():
    """Verify validate_client_message rejects unknown message type."""
    data = {"type": "unknown.type", "payload": {}}
    is_valid, message, error = validate_client_message(data)

    assert is_valid is False
    assert "Unknown message type" in error


def test_validate_client_message_rejects_invalid_payload():
    """Verify validate_client_message rejects invalid payload."""
    data = {"type": "chat.send", "payload": {"content": ""}}  # Empty content
    is_valid, message, error = validate_client_message(data)

    assert is_valid is False
    assert "Validation error" in error


def test_validate_client_message_rejects_negative_cursor():
    """Verify validate_client_message rejects negative cursor."""
    data = {"type": "completion.request", "payload": {"text": "Hello", "cursor": -1}}
    is_valid, message, error = validate_client_message(data)

    assert is_valid is False
    assert "Validation error" in error


# =============================================================================
# Error Response Tests
# =============================================================================


def test_create_validation_error_response():
    """Verify create_validation_error_response creates proper error message."""
    response = create_validation_error_response("msg-123", "Invalid message format")

    assert response["type"] == "chat.error"
    assert response["payload"]["messageId"] == "msg-123"
    assert response["payload"]["error"] == "Invalid message format"


# =============================================================================
# Streaming Control Tests
# =============================================================================


def test_validate_client_message_chat_cancel():
    """Verify validate_client_message accepts chat.cancel."""
    data = {"type": "chat.cancel"}
    is_valid, message, error = validate_client_message(data)

    assert is_valid is True
    assert error == ""
    assert isinstance(message, ChatCancelMessage)
    assert message.model_dump() == {"type": "chat.cancel"}


def test_validate_client_message_chat_cancel_rejects_payload():
    """Verify chat.cancel rejects unexpected payload data."""
    data = {"type": "chat.cancel", "payload": {}}
    is_valid, message, error = validate_client_message(data)

    assert is_valid is False
    assert message is None
    assert "Validation error" in error


def test_validate_client_message_chat_edit():
    """Verify validate_client_message accepts chat.edit."""
    payload = ChatEditPayload(messageId="msg-123", content="Updated prompt")
    data = {"type": "chat.edit", "payload": payload.model_dump(by_alias=True)}
    is_valid, message, error = validate_client_message(data)

    assert is_valid is True
    assert error == ""
    assert isinstance(message, ChatEditMessage)
    assert message.payload.message_id == "msg-123"
    assert message.payload.content == "Updated prompt"


def test_validate_client_message_chat_edit_rejects_missing_message_id():
    """Verify chat.edit rejects missing messageId."""
    data = {"type": "chat.edit", "payload": {"content": "Updated prompt"}}
    is_valid, message, error = validate_client_message(data)

    assert is_valid is False
    assert message is None
    assert "Validation error" in error
    assert "messageId" in error or "message_id" in error


def test_validate_client_message_chat_edit_rejects_empty_content():
    """Verify chat.edit rejects empty content."""
    data = {"type": "chat.edit", "payload": {"messageId": "msg-123", "content": ""}}
    is_valid, message, error = validate_client_message(data)

    assert is_valid is False
    assert message is None
    assert "Validation error" in error
    assert "content" in error


def test_chat_cancelled_message():
    """Verify chat.cancelled server message structure."""
    payload = ChatCancelledPayload(message_id="msg-123")
    message = ChatCancelledMessage(type="chat.cancelled", payload=payload)

    assert message.type == "chat.cancelled"
    assert message.payload.message_id == "msg-123"
    assert message.model_dump(by_alias=True) == {
        "type": "chat.cancelled",
        "payload": {"messageId": "msg-123"},
    }
