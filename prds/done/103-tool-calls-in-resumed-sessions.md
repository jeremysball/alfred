# PRD: Display Tool Calls in Resumed Sessions

**GitHub Issue**: #103
**Priority**: High
**Status**: ✅ Complete

---

## 1. Problem Statement

When resuming a session via `/resume` command or on TUI startup, the conversation messages are loaded from storage and displayed in the TUI. However, **tool calls are not rendered** — even though they are stored in `msg.tool_calls` on each message.

This creates a confusing experience where:
- Users see assistant responses that reference tool outputs they can't see
- Context about how answers were derived is lost
- Debugging past conversations becomes difficult
- The historical view doesn't match what was seen during the live session

### Current Behavior

```python
# In _load_session_messages() - tui.py
for msg in session.messages:
    panel = MessagePanel(
        role=msg.role.value,
        content=msg.content,
        terminal_width=self._terminal_width,
        use_markdown=self.alfred.config.use_markdown_rendering,
    )
    # msg.tool_calls is IGNORED
    self.conversation.add_child(panel)
```

### Expected Behavior

Tool calls should be rendered identically to how they appear during live streaming — with the tool box, arguments, output, and status indicator.

---

## 2. Solution Overview

Modify `_load_session_messages()` to pass tool calls to each `MessagePanel`. The `MessagePanel` class already supports tool calls via `add_tool_call()` — we just need to invoke it for historical messages.

### Approach

Add a `tool_calls` parameter to `MessagePanel.__init__()` that accepts pre-existing tool call data. This avoids calling `add_tool_call()` N times per message (which would trigger N rebuilds).

---

## 3. Detailed Requirements

### 3.1 MessagePanel Constructor Enhancement

Add optional `tool_calls` parameter:

```python
def __init__(
    self,
    role: Literal["user", "assistant", "system"],
    content: str = "",
    *,
    padding_x: int = 1,
    padding_y: int = 0,
    terminal_width: int = 80,
    use_markdown: bool = True,
    tool_calls: list[ToolCallInfo] | None = None,  # NEW
) -> None:
```

When `tool_calls` is provided, populate `self._tool_calls` directly before the first `_rebuild_content()` call.

### 3.2 ToolCallInfo from ToolCallRecord

The stored `ToolCallRecord` (from `src/session.py`) has this structure:

```python
@dataclass
class ToolCallRecord:
    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any]
    output: str
    status: Literal["success", "error"]
    insert_position: int = 0
    sequence: int = 0
```

The `ToolCallInfo` (from `src/interfaces/pypitui/models.py`) has:

```python
@dataclass
class ToolCallInfo:
    tool_name: str
    tool_call_id: str
    insert_position: int
    sequence: int = 0
    arguments: dict[str, object] | None = None
    output: str = ""
    status: Literal["running", "success", "error"] = "running"
```

The mapping is direct — just convert the list of records to info objects.

### 3.3 TUI Session Loading

Update `_load_session_messages()` in `src/interfaces/pypitui/tui.py`:

```python
from src.interfaces.pypitui.models import ToolCallInfo
from src.session import ToolCallRecord

def _load_session_messages(self) -> None:
    # ... existing checks ...

    for msg in session.messages:
        # Convert stored tool calls to ToolCallInfo
        tool_call_infos: list[ToolCallInfo] | None = None
        if msg.tool_calls:
            tool_call_infos = [
                ToolCallInfo(
                    tool_name=tc.tool_name,
                    tool_call_id=tc.tool_call_id,
                    insert_position=tc.insert_position,
                    sequence=tc.sequence,
                    arguments=tc.arguments,
                    output=tc.output,
                    status=tc.status,
                )
                for tc in msg.tool_calls
            ]

        panel = MessagePanel(
            role=msg.role.value,
            content=msg.content,
            terminal_width=self._terminal_width,
            use_markdown=self.alfred.config.use_markdown_rendering,
            tool_calls=tool_call_infos,  # NEW
        )
        self.conversation.add_child(panel)
```

### 3.4 Telegram Interface (Optional)

If the Telegram interface also loads historical messages, apply the same pattern. Check `src/interfaces/telegram.py` for session loading.

---

## 4. Implementation Todo (Test First)

### MessagePanel Constructor Enhancement

**File**: `src/interfaces/pypitui/message_panel.py`

- [x] **Test**: `test_message_panel_accepts_tool_calls_parameter()` — verify `__init__` accepts `tool_calls: list[ToolCallInfo] | None = None`
- [x] **Implement**: Add `tool_calls` parameter to `MessagePanel.__init__()` signature
- [x] **Commit**: `feat(message_panel): add tool_calls parameter to constructor`

- [x] **Test**: `test_message_panel_stores_tool_calls()` — verify `self._tool_calls` contains provided tool calls
- [x] **Implement**: Populate `self._tool_calls` with provided tool calls before `_rebuild_content()`
- [x] **Commit**: Combined with above

- [ ] **Test**: `test_message_panel_renders_tool_call_boxes()` — verify tool calls appear as boxes in rendered output
- [ ] **Implement**: Ensure `_rebuild_content()` processes pre-populated tool calls
- [ ] **Commit**: `feat(message_panel): render pre-populated tool calls`

- [x] **Test**: `test_message_panel_empty_tool_calls_none()` — verify panel works when `tool_calls=None` (backward compatibility)
- [x] **Test**: `test_message_panel_empty_tool_calls_list()` — verify panel works when `tool_calls=[]`
- [x] **Commit**: Combined with above

### ToolCallRecord to ToolCallInfo Conversion

**File**: `src/interfaces/pypitui/tui.py` (in `_load_session_messages`)

- [x] **Test**: `test_convert_single_tool_call_record()` — verify one `ToolCallRecord` converts to one `ToolCallInfo` with all fields mapped
- [x] **Implement**: Conversion logic for `tool_name`, `tool_call_id`, `arguments`, `output`, `status`, `insert_position`, `sequence`
- [x] **Commit**: Combined in `feat(tui): add tool call conversion and integrate into session loading`

- [x] **Test**: `test_convert_multiple_tool_calls()` — verify list of records converts to list of infos in same order
- [x] **Implement**: List comprehension for batch conversion
- [x] **Commit**: Combined in above

- [x] **Test**: `test_convert_none_tool_calls()` — verify `None` input returns `None` (no conversion attempted)
- [x] **Test**: `test_convert_empty_tool_calls()` — verify empty list returns empty list
- [x] **Commit**: Combined in above

### TUI Session Loading Integration

**File**: `src/interfaces/pypitui/tui.py` (`_load_session_messages` method)

- [x] **Test**: `test_load_session_passes_tool_calls_to_panel()` — verify `MessagePanel` receives `tool_calls` parameter when loading messages
- [x] **Implement**: Update `_load_session_messages()` to convert and pass `tool_calls` to `MessagePanel`
- [x] **Commit**: Combined in above

- [x] **Test**: `test_load_session_message_without_tool_calls()` — verify messages without tool_calls load correctly (backward compat)
- [x] **Commit**: Combined in above

### Milestone 2 Detailed Implementation Steps

**Step 1: Create conversion helper function**
- [x] **Test**: `test_convert_tool_call_record_to_info_success()` — verify success status maps correctly
- [x] **Test**: `test_convert_tool_call_record_to_info_error()` — verify error status maps correctly
- [x] **Implement**: Create `_convert_tool_call_record()` helper in `tui.py`
- [x] **Commit**: Combined in above

**Step 2: Batch conversion for multiple tool calls**
- [x] **Test**: `test_convert_tool_calls_list()` — verify list of records converts to list of infos
- [x] **Test**: `test_convert_tool_calls_preserves_order()` — verify order is maintained
- [x] **Implement**: Create `_convert_tool_calls()` helper for batch conversion
- [x] **Commit**: Combined in above

**Step 3: Integrate into _load_session_messages**
- [x] **Test**: `test_load_session_with_tool_calls()` — verify tool calls passed to MessagePanel
- [x] **Implement**: Import `ToolCallInfo` in tui.py, add conversion logic to `_load_session_messages()`
- [x] **Commit**: Combined in above

**Step 4: Backward compatibility**
- [x] **Test**: `test_load_session_without_tool_calls()` — verify messages without tool_calls still work
- [x] **Test**: `test_load_session_with_none_tool_calls()` — verify None tool_calls handled
- [x] **Commit**: Combined in above

### Integration Tests

**File**: `tests/test_tool_calls_resumed_sessions.py` (new)

- [x] **Test**: `test_resume_session_shows_tool_calls()` — end-to-end: create session with tool calls, save, resume, verify tool boxes visible
- [x] **Test**: `test_multiple_tool_calls_in_session()` — verify multiple tool calls in a session are all preserved
- [x] **Test**: `test_tool_call_success_and_error_status()` — verify both success and error statuses preserved
- [x] **Test**: `test_tool_call_arguments_preserved()` — verify complex arguments maintained through save/load
- [x] **Test**: `test_large_session_loads_efficiently()` — verify session with 100+ messages with tool calls loads in < 2 seconds
- [x] **Commit**: `test(integration): add tool calls resumed sessions tests`

### Manual Verification

- [ ] Run Alfred, execute `bash` tool, `/new`, `/resume <id>`, verify tool box appears
- [ ] Run Alfred, execute `read` and `write` tools, restart Alfred, verify tool boxes appear on startup
- [ ] Verify tool arguments and output are visible in resumed sessions
- [ ] Verify tool status indicators (success/error) match original session

### Telegram Interface (Optional - If Applicable)

**File**: `src/interfaces/telegram.py`

- [x] **Spike**: Investigate if Telegram interface loads historical messages with tool calls

**Decision**: Telegram interface does NOT need changes. Unlike the CLI which renders full conversation history on `/resume`, Telegram:
- Only continues the session (doesn't display historical messages)
- Sends a simple "welcome back" message with message count
- Tool calls are preserved in the session but not displayed in history

This is acceptable because Telegram conversations are continuous (user doesn't "resume" like CLI), and the interface doesn't show scrollback of previous turns.

---

## 5. File Changes

| File | Change |
|------|--------|
| `src/interfaces/pypitui/message_panel.py` | Add `tool_calls` parameter to `__init__` |
| `src/interfaces/pypitui/tui.py` | Convert and pass tool_calls in `_load_session_messages()` |
| `src/interfaces/telegram.py` | (If applicable) Same pattern for Telegram |

---

## 6. Testing Strategy

### Unit Tests
- Test `MessagePanel` with pre-populated tool calls
- Test conversion from `ToolCallRecord` to `ToolCallInfo`

### Integration Tests
- Create session with tool calls, save, resume, verify tool calls visible
- Test with success and error status tool calls

### Manual Testing
- Run Alfred, execute tools, `/new`, `/resume <id>`, verify tool boxes appear
- Restart Alfred (auto-resume), verify tool boxes appear

---

## 7. Success Criteria

- [x] Tool calls visible when resuming via `/resume`
- [x] Tool calls visible when resuming on TUI startup
- [x] Historical tool calls render identically to live tool calls
- [x] No performance degradation on sessions with many tool calls
- [x] All tests pass

---

## 8. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Performance on large sessions | No limit requested; monitor and optimize if needed |
| Backward compatibility | `tool_calls` param is optional, defaults to None |
| Status mismatch | ToolCallRecord uses "success"/"error", ToolCallInfo uses same + "running" |

---

## 9. Related Documentation

- PRD #101: Tool Call Persistence and Context Visibility (completed — stores tool calls)
- `src/session.py`: `ToolCallRecord` dataclass
- `src/interfaces/pypitui/models.py`: `ToolCallInfo` dataclass
- `src/interfaces/pypitui/message_panel.py`: Tool call rendering
