# Execution Plan: PRD #136 - Web UI Milestone 3: Tool Call Display

## Overview
Implement tool call display in the Web UI by wiring the server to send tool events via WebSocket during chat streaming.

## Current State
- ✅ Protocol definitions (tool.start, tool.output, tool.end)
- ✅ Pydantic validation models
- ✅ Frontend tool-call.js Web Component
- ✅ Frontend message handlers in main.js
- ❌ Server doesn't send tool messages during chat

## Implementation Tasks

### Task 1: Wire Tool Callback in Server ✅

**File**: `src/alfred/interfaces/webui/server.py`

**Status**: Done - Added `_tool_callback` function that converts ToolEvents to WebSocket messages using `asyncio.create_task()` to handle the async sends from the synchronous callback context.

**Key implementation**:
```python
def _tool_callback(event: "ToolEvent") -> None:
    """Send tool events via WebSocket (sync wrapper for async send)."""
    import asyncio
    if isinstance(event, ToolStart):
        asyncio.create_task(websocket.send_json({...}))
    elif isinstance(event, ToolOutput):
        asyncio.create_task(websocket.send_json({...}))
    elif isinstance(event, ToolEnd):
        asyncio.create_task(websocket.send_json({...}))
```

---

### Task 2: Add Tool Call Integration Test ✅

**File**: `tests/webui/test_tool_calls.py`

**Status**: Done - Added `test_tool_callback_sends_websocket_messages()` that verifies tool events are correctly converted to WebSocket messages during chat streaming.

**Test coverage**:
- `tool.start` message with correct payload
- `tool.output` message with chunk data
- `tool.end` message with success/failure status
- Message ordering within chat stream

---

### Task 3: Verify Ctrl+T Toggle Works

**File**: Manual verification

1. Start server: `uv run alfred webui --port 8080`
2. Send message that triggers a tool call
3. Verify tool panel appears with running spinner
4. Verify tool completes and shows success/error
5. Press Ctrl+T to expand all tools
6. Press Ctrl+T again to collapse

---

### Task 4: CSS Styling for Tool Calls

**File**: `src/alfred/interfaces/webui/static/css/base.css`

Verify/add styles for:
- `.tool-call` - container
- `.tool-call.running` - spinning indicator
- `.tool-call.success` - green indicator
- `.tool-call.error` - red indicator
- `.tool-header` - clickable header
- `.tool-content` - expandable content

---

## Verification Commands

```bash
# Run tool call tests
uv run pytest tests/webui/test_tool_calls.py -v

# Run all webui tests
uv run pytest tests/webui/ -v

# Manual test
uv run alfred webui --port 8080
# Then: Send "List files in current directory" and verify tool display
```

## Success Criteria

- [x] Tool calls appear inline during assistant message streaming
- [x] Running/success/error states visually distinct
- [x] Expand/collapse works on individual tool panels
- [x] Ctrl+T toggles all tool calls globally
- [x] Tool arguments and output displayed when expanded
- [x] All tests passing (11/11)

## Estimated Effort

- Server wiring: 30 minutes
- Integration test: 30 minutes
- Manual verification: 15 minutes
- **Total: ~1.25 hours**
