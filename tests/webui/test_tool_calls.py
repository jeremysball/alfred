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
# Tool Callback Integration Test
# =============================================================================

def test_tool_callback_sends_websocket_messages():
    """Verify tool callback sends correct WebSocket messages."""
    from alfred.agent import ToolStart, ToolOutput, ToolEnd
    from alfred.interfaces.webui.server import _handle_chat_message
    import asyncio

    # Track messages sent via WebSocket
    sent_messages = []

    class MockWebSocket:
        """Mock WebSocket that captures sent messages."""

        async def send_json(self, data):
            sent_messages.append(data)

    class MockAlfred:
        """Mock Alfred that simulates chat with tool calls."""

        async def chat_stream(self, content, tool_callback=None):
            """Simulate chat streaming with tool calls."""
            yield "I'll help you read that file."

            # Simulate tool start
            if tool_callback:
                tool_callback(ToolStart(
                    tool_call_id="call_abc123",
                    tool_name="read_file",
                    arguments={"path": "/tmp/test.txt"}
                ))

            await asyncio.sleep(0)  # Let event loop process the task
            yield " "

            # Simulate tool output
            if tool_callback:
                tool_callback(ToolOutput(
                    tool_call_id="call_abc123",
                    tool_name="read_file",
                    chunk="File contents here"
                ))

            await asyncio.sleep(0)
            yield "Done"

            # Simulate tool end
            if tool_callback:
                tool_callback(ToolEnd(
                    tool_call_id="call_abc123",
                    tool_name="read_file",
                    result="File contents here",
                    is_error=False
                ))

            await asyncio.sleep(0)

    async def run_test():
        mock_ws = MockWebSocket()
        mock_alfred = MockAlfred()

        await _handle_chat_message(mock_ws, mock_alfred, "Read /tmp/test.txt")

        # Give event loop time to process any pending tasks
        await asyncio.sleep(0.1)

        return sent_messages

    # Run the async test
    messages = asyncio.run(run_test())

    # Verify message types
    message_types = [m["type"] for m in messages]

    # Should have: chat.started, chat.chunk(s), tool.start, tool.output, tool.end, chat.complete
    assert "chat.started" in message_types, f"Expected chat.started in {message_types}"
    assert "chat.complete" in message_types, f"Expected chat.complete in {message_types}, got {messages}"
    assert "tool.start" in message_types, f"Expected tool.start in {message_types}"
    assert "tool.output" in message_types, f"Expected tool.output in {message_types}"
    assert "tool.end" in message_types, f"Expected tool.end in {message_types}"

    # Verify tool.start payload
    tool_start_msg = next(m for m in messages if m["type"] == "tool.start")
    assert tool_start_msg["payload"]["toolCallId"] == "call_abc123"
    assert tool_start_msg["payload"]["toolName"] == "read_file"
    assert tool_start_msg["payload"]["arguments"] == {"path": "/tmp/test.txt"}

    # Verify tool.output payload
    tool_output_msg = next(m for m in messages if m["type"] == "tool.output")
    assert tool_output_msg["payload"]["toolCallId"] == "call_abc123"
    assert tool_output_msg["payload"]["chunk"] == "File contents here"

    # Verify tool.end payload
    tool_end_msg = next(m for m in messages if m["type"] == "tool.end")
    assert tool_end_msg["payload"]["toolCallId"] == "call_abc123"
    assert tool_end_msg["payload"]["success"] is True
    assert tool_end_msg["payload"]["output"] == "File contents here"


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
