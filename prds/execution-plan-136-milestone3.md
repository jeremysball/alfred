# Execution Plan: PRD #136 - Web UI Milestone 3: Tool Call Display

## Overview
Implement visual tool call panels with expand/collapse functionality for the Alfred Web UI.

---

## Milestone 3: Tool Call Display

### WebSocket Protocol for Tool Events

- [x] Test: `test_tool_start_message()` - Verify tool.start message structure
- [x] Implement: Add tool.start, tool.output, tool.end message handling in server
- [x] Run: `uv run pytest tests/webui/test_protocol.py::test_tool_start_message -v`

- [x] Test: `test_tool_output_streaming()` - Verify tool.output chunks flow correctly
- [x] Implement: Wire tool execution to WebSocket streaming
- [x] Run: `uv run pytest tests/webui/test_tool_calls.py -v`

- [x] Test: `test_tool_end_status()` - Verify success/error states are communicated
- [x] Implement: Add tool status tracking in WebSocket handler
- [x] Run: `uv run pytest tests/webui/test_tool_calls.py::test_tool_end_status -v`

### Tool Call Web Component

- [x] Test: `test_tool_call_component_exists()` - Verify <tool-call> component is served
- [x] Implement: Create `<tool-call>` Web Component in static/js/components/
- [x] Run: `uv run pytest tests/webui/test_frontend.py::test_tool_call_component -v`

- [x] Test: `test_tool_call_collapsed_state()` - Verify collapsed display (icon + name + status)
- [x] Implement: Add collapsed state rendering with spinner
- [x] Run: Manual verification - browser check

- [x] Test: `test_tool_call_expanded_state()` - Verify expanded display (args + output)
- [x] Implement: Add expanded state with full argument and output display
- [x] Run: Manual verification - browser check

- [x] Test: `test_tool_call_status_indicators()` - Verify running/success/error states
- [x] Implement: Add status indicator styling (colors, icons)
- [x] Run: `uv run pytest tests/webui/test_frontend.py::test_tool_call_styles -v`

### Global Expand/Collapse

- [x] Test: `test_ctrl_t_shortcut()` - Verify Ctrl+T toggles all tool calls
- [x] Implement: Add keyboard shortcut handler for Ctrl+T
- [x] Run: Manual verification - browser check

- [x] Test: `test_tool_call_toggle_event()` - Verify individual expand/collapse works
- [x] Implement: Add click handler for tool call header
- [x] Run: Manual verification - browser check

### Styling

- [x] Test: `test_tool_call_styles_exist()` - Verify tool call CSS is present
- [x] Implement: Add tool call styling to base.css
- [x] Run: `uv run pytest tests/webui/test_static.py::test_tool_call_styles -v`

---

## Files to Modify/Created

### New Files
1. `src/alfred/interfaces/webui/static/js/components/tool-call.js` - Tool call Web Component
2. `tests/webui/test_tool_calls.py` - Tool call integration tests

### Modified Files
1. `src/alfred/interfaces/webui/server.py` - Add tool event message handlers
2. `src/alfred/interfaces/webui/static/js/main.js` - Add Ctrl+T handler
3. `src/alfred/interfaces/webui/static/css/base.css` - Add tool call styles
4. `src/alfred/interfaces/webui/static/index.html` - Include tool-call component

---

## Verification Commands

### Quick Test
```bash
# Run tool call tests
uv run pytest tests/webui/test_tool_calls.py -v

# Run frontend tests
uv run pytest tests/webui/test_frontend.py -v
```

### Manual Testing
```bash
# Start server
uv run alfred webui --port 8080

# 1. Send a message that triggers a tool call
# 2. Verify tool call appears in collapsed state
# 3. Click to expand
# 4. Verify full output is shown
# 5. Press Ctrl+T to collapse all
# 6. Press Ctrl+T to expand all
```

---

## Progress Summary

### ✅ Completed (9/9 tasks) - MILESTONE 3 COMPLETE!
- ✅ WebSocket Protocol for Tool Events (3/3 tasks)
- ✅ Tool Call Web Component (4/4 tasks)
- ✅ Global Expand/Collapse (2/2 tasks)

---

## Success Criteria

Before marking Milestone 3 complete:

- [x] Tool calls appear inline with assistant messages
- [x] Collapsed state shows icon + tool name + spinner
- [x] Expanded state shows arguments and output
- [x] Ctrl+T toggles all tool calls globally
- [x] Success/error states visually distinct
- [x] All tests passing (87 total)

---

## Completion Summary

### Test Coverage
| Component | Tests | Status |
|-----------|-------|--------|
| Server (M1) | 20 | ✅ Passing |
| Protocol (M2) | 12 | ✅ Passing |
| Chat Integration (M2) | 9 | ✅ Passing |
| Frontend (M2) | 7 | ✅ Passing |
| Validation (M2) | 29 | ✅ Passing |
| Tool Calls (M3) | 10 | ✅ Passing |
| **Total** | **87** | ✅ **All Passing** |

### New Files Created
- `src/alfred/interfaces/webui/static/js/components/tool-call.js` - Tool call Web Component
- `tests/webui/test_tool_calls.py` - 10 tool call tests

### Key Features Implemented
- **ToolOutputMessage**: Added to validation.py for streaming tool output
- **ToolCall Component**: Custom element with expand/collapse functionality
- **Status Indicators**: running (orange), success (green), error (red)
- **Ctrl+T Shortcut**: Global toggle for all tool calls
- **Tool Handlers**: main.js handles tool.start, tool.output, tool.end messages

---

## Dependencies

```toml
# Already available:
# - fastapi
# - websockets
# - pydantic
```

---

## Commit Strategy

```bash
git commit -m "feat(webui): add tool WebSocket protocol handlers"
git commit -m "feat(webui): create <tool-call> Web Component"
git commit -m "feat(webui): implement expand/collapse functionality"
git commit -m "feat(webui): add Ctrl+T global shortcut"
git commit -m "feat(webui): add tool call styling"
git commit -m "test(webui): add tool call integration tests"
```
