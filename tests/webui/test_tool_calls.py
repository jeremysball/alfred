"""Tests for tool call WebSocket protocol and integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from alfred.interfaces.webui import create_app


def test_tool_start_message_structure():
    """Verify tool.start message validation works."""
    from alfred.interfaces.webui.validation import ToolStartMessage, ToolStartPayload

    message = ToolStartMessage(
        type="tool.start",
        payload=ToolStartPayload(
            tool_call_id="call_abc123",
            tool_name="read_file",
            arguments={"path": "/tmp/test.txt"},
            message_id="msg-123"
        )
    )
    
    assert message.type == "tool.start"
    assert message.payload.tool_call_id == "call_abc123"
    assert message.payload.tool_name == "read_file"
    assert message.payload.arguments == {"path": "/tmp/test.txt"}


def test_tool_output_message_structure():
    """Verify tool.output message validation works."""
    from alfred.interfaces.webui.validation import ToolOutputMessage, ToolOutputPayload

    message = ToolOutputMessage(
        type="tool.output",
        payload=ToolOutputPayload(
            tool_call_id="call_abc123",
            chunk="File contents here"
        )
    )
    
    assert message.type == "tool.output"
    assert message.payload.tool_call_id == "call_abc123"
    assert message.payload.chunk == "File contents here"


def test_tool_end_message_success():
    """Verify tool.end message with success status."""
    from alfred.interfaces.webui.validation import ToolEndMessage, ToolEndPayload

    message = ToolEndMessage(
        type="tool.end",
        payload=ToolEndPayload(
            tool_call_id="call_abc123",
            success=True,
            output="Final result"
        )
    )
    
    assert message.type == "tool.end"
    assert message.payload.success is True
    assert message.payload.output == "Final result"


def test_tool_end_message_error():
    """Verify tool.end message with error status."""
    from alfred.interfaces.webui.validation import ToolEndMessage, ToolEndPayload

    message = ToolEndMessage(
        type="tool.end",
        payload=ToolEndPayload(
            tool_call_id="call_abc123",
            success=False,
            output=None
        )
    )
    
    assert message.type == "tool.end"
    assert message.payload.success is False
    assert message.payload.output is None


# =============================================================================
# WebSocket Integration Tests
# =============================================================================


def test_websocket_accepts_tool_messages():
    """Verify WebSocket connection handles tool protocol messages."""
    app = create_app()
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Verify connection is established (receives connected message)
        response = websocket.receive_json()
        assert response["type"] == "connected"
        
        # Send a chat message (will be queued since no Alfred instance)
        websocket.send_json({
            "type": "chat.send",
            "payload": {"content": "Read file /tmp/test.txt"}
        })
        
        # In a real scenario with Alfred, would receive chat.started then tool.start
        # Here we just verify the connection handles the message without error


def test_tool_message_serialization():
    """Verify tool messages serialize to correct JSON format."""
    from alfred.interfaces.webui.validation import ToolStartMessage, ToolStartPayload
    
    message = ToolStartMessage(
        type="tool.start",
        payload=ToolStartPayload(
            tool_call_id="call_abc123",
            tool_name="bash",
            arguments={"command": "ls -la"},
            message_id="msg-123"
        )
    )
    
    # Serialize and verify camelCase
    json_data = message.model_dump(by_alias=True)
    
    assert json_data["type"] == "tool.start"
    assert json_data["payload"]["toolCallId"] == "call_abc123"
    assert json_data["payload"]["toolName"] == "bash"
    assert json_data["payload"]["messageId"] == "msg-123"


# =============================================================================
# Frontend Component Tests
# =============================================================================


def test_tool_call_component_exists():
    """Verify tool-call Web Component is served."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/js/components/tool-call.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


def test_tool_call_component_structure():
    """Verify tool-call component has required structure."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/js/components/tool-call.js")
    content = response.text

    # Verify it defines a custom element
    assert "class ToolCall" in content or "tool-call" in content
    assert "customElements.define" in content
    
    # Verify it handles key attributes
    assert "tool-call-id" in content or "toolCallId" in content
    assert "tool-name" in content or "toolName" in content
    assert "status" in content.lower()


def test_tool_call_styles_exist():
    """Verify tool call CSS is present in base.css."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/css/base.css")
    content = response.text

    # Verify tool call related styles
    assert ".tool-call" in content or "tool-call" in content.lower()
    assert ".tool-header" in content or "tool-content" in content


def test_index_html_includes_tool_component():
    """Verify index.html includes tool-call component script."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/index.html")
    content = response.text

    assert "tool-call.js" in content
