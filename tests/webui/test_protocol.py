"""Tests for WebSocket protocol definitions."""

from alfred.interfaces.webui.protocol import (
    ChatChunkMessage,
    ChatCompleteMessage,
    ChatErrorMessage,
    ChatSendMessage,
    ChatStartedMessage,
    DaemonStatusMessage,
    StatusUpdateMessage,
    ToastMessage,
    ToolEndMessage,
    ToolStartMessage,
)


def test_chat_send_message_structure():
    """Verify chat.send message has correct structure."""
    message: ChatSendMessage = {
        "type": "chat.send",
        "payload": {
            "content": "Hello, Alfred!",
            "queue": False,
        },
    }
    assert message["type"] == "chat.send"
    assert message["payload"]["content"] == "Hello, Alfred!"
    assert message["payload"]["queue"] is False


def test_chat_send_message_without_queue():
    """Verify chat.send message works without optional queue field."""
    message: ChatSendMessage = {
        "type": "chat.send",
        "payload": {
            "content": "Hello",
        },
    }
    assert message["type"] == "chat.send"
    assert message["payload"]["content"] == "Hello"
    assert "queue" not in message["payload"]


def test_chat_started_message_structure():
    """Verify chat.started message has correct structure."""
    message: ChatStartedMessage = {
        "type": "chat.started",
        "payload": {
            "messageId": "msg_123",
            "role": "assistant",
        },
    }
    assert message["type"] == "chat.started"
    assert message["payload"]["messageId"] == "msg_123"
    assert message["payload"]["role"] == "assistant"


def test_chat_chunk_message_structure():
    """Verify chat.chunk message has correct structure."""
    message: ChatChunkMessage = {
        "type": "chat.chunk",
        "payload": {
            "messageId": "msg_123",
            "content": "Hello",
        },
    }
    assert message["type"] == "chat.chunk"
    assert message["payload"]["messageId"] == "msg_123"
    assert message["payload"]["content"] == "Hello"


def test_chat_complete_message_structure():
    """Verify chat.complete message has correct structure."""
    message: ChatCompleteMessage = {
        "type": "chat.complete",
        "payload": {
            "messageId": "msg_123",
            "finalContent": "Hello! How can I help?",
            "usage": {
                "inputTokens": 10,
                "outputTokens": 20,
                "cacheReadTokens": 5,
                "reasoningTokens": 0,
            },
        },
    }
    assert message["type"] == "chat.complete"
    assert message["payload"]["messageId"] == "msg_123"
    assert message["payload"]["finalContent"] == "Hello! How can I help?"
    assert message["payload"]["usage"]["inputTokens"] == 10
    assert message["payload"]["usage"]["outputTokens"] == 20


def test_chat_error_message_structure():
    """Verify chat.error message has correct structure."""
    message: ChatErrorMessage = {
        "type": "chat.error",
        "payload": {
            "messageId": "msg_123",
            "error": "Something went wrong",
        },
    }
    assert message["type"] == "chat.error"
    assert message["payload"]["messageId"] == "msg_123"
    assert message["payload"]["error"] == "Something went wrong"


def test_tool_start_message_structure():
    """Verify tool.start message has correct structure."""
    message: ToolStartMessage = {
        "type": "tool.start",
        "payload": {
            "toolCallId": "call_123",
            "toolName": "read_file",
            "arguments": {"path": "/docs/readme.md"},
            "messageId": "msg_123",
        },
    }
    assert message["type"] == "tool.start"
    assert message["payload"]["toolCallId"] == "call_123"
    assert message["payload"]["toolName"] == "read_file"
    assert message["payload"]["arguments"]["path"] == "/docs/readme.md"


def test_tool_end_message_structure():
    """Verify tool.end message has correct structure."""
    message: ToolEndMessage = {
        "type": "tool.end",
        "payload": {
            "toolCallId": "call_123",
            "success": True,
            "output": "File contents here",
        },
    }
    assert message["type"] == "tool.end"
    assert message["payload"]["toolCallId"] == "call_123"
    assert message["payload"]["success"] is True
    assert message["payload"]["output"] == "File contents here"


def test_tool_end_message_without_output():
    """Verify tool.end message works without optional output field."""
    message: ToolEndMessage = {
        "type": "tool.end",
        "payload": {
            "toolCallId": "call_123",
            "success": False,
        },
    }
    assert message["type"] == "tool.end"
    assert message["payload"]["success"] is False
    assert "output" not in message["payload"]


def test_daemon_status_message_structure():
    """Verify daemon.status message has correct structure."""
    message: DaemonStatusMessage = {
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
            },
        },
    }
    assert message["type"] == "daemon.status"
    assert set(message["payload"]["daemon"].keys()) == {
        "state",
        "pid",
        "socketPath",
        "socketHealthy",
        "startedAt",
        "uptimeSeconds",
        "lastHeartbeatAt",
        "lastReloadAt",
        "lastError",
    }
    assert message["payload"]["daemon"]["state"] == "running"
    assert message["payload"]["daemon"]["pid"] == 12345
    assert message["payload"]["daemon"]["socketHealthy"] is True


def test_status_update_message_structure():
    """Verify status.update message has correct structure."""
    message: StatusUpdateMessage = {
        "type": "status.update",
        "payload": {
            "model": "kimi-latest",
            "contextTokens": 2450,
            "inputTokens": 1200,
            "outputTokens": 850,
            "cacheReadTokens": 2000,
            "reasoningTokens": 150,
            "queueLength": 2,
            "isStreaming": True,
        },
    }
    assert message["type"] == "status.update"
    assert message["payload"] == {
        "model": "kimi-latest",
        "contextTokens": 2450,
        "inputTokens": 1200,
        "outputTokens": 850,
        "cacheReadTokens": 2000,
        "reasoningTokens": 150,
        "queueLength": 2,
        "isStreaming": True,
    }


def test_toast_message_structure():
    """Verify toast message has correct structure."""
    message: ToastMessage = {
        "type": "toast",
        "payload": {
            "message": "Job completed",
            "level": "success",
            "duration": 5000,
        },
    }
    assert message["type"] == "toast"
    assert message["payload"]["message"] == "Job completed"
    assert message["payload"]["level"] == "success"
    assert message["payload"]["duration"] == 5000


def test_toast_message_without_duration():
    """Verify toast message works without optional duration field."""
    message: ToastMessage = {
        "type": "toast",
        "payload": {
            "message": "Info message",
            "level": "info",
        },
    }
    assert message["type"] == "toast"
    assert message["payload"]["level"] == "info"
    assert "duration" not in message["payload"]
