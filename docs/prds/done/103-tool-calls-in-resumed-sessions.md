# PRD: Display Tool Calls in Resumed Sessions

**GitHub Issue**: #103
**Priority**: High
**Status**: Ready for Implementation

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

## 4. Implementation Milestones

### Milestone 1: MessagePanel Tool Calls Parameter

- [ ] Add `tool_calls` parameter to `MessagePanel.__init__()`
- [ ] Populate `self._tool_calls` before first rebuild
- [ ] Test: Create panel with tool_calls, verify rendered correctly

### Milestone 2: TUI Session Loading

- [ ] Import `ToolCallInfo` and `ToolCallRecord` in tui.py
- [ ] Convert `msg.tool_calls` to `ToolCallInfo` list in `_load_session_messages()`
- [ ] Pass `tool_calls` to MessagePanel constructor
- [ ] Test: Resume session with tool calls, verify they appear

### Milestone 3: Telegram Interface (If Applicable)

- [ ] Check if Telegram interface loads historical messages
- [ ] Apply same pattern if needed
- [ ] Test: Telegram resume shows tool calls

### Milestone 4: Integration Testing

- [ ] Test: Session with multiple tool calls renders correctly
- [ ] Test: Tool call status (success/error) displays correctly
- [ ] Test: Tool arguments and output display correctly
- [ ] Test: Large sessions with many tool calls load without performance issues

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

- [ ] Tool calls visible when resuming via `/resume`
- [ ] Tool calls visible when resuming on TUI startup
- [ ] Historical tool calls render identically to live tool calls
- [ ] No performance degradation on sessions with many tool calls
- [ ] All tests pass

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
