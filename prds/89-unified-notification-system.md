# PRD #89: Unified Notification System with Prompt Preservation

**Status**: Draft  
**Priority**: High  
**Author**: Claude (Agent)  
**Created**: 2026-02-22  
**Related PRDs**: #85 (Enhanced CLI Status Line)

---

## Problem Statement

The current CLI notification system has two UX inconsistencies:

1. **Inconsistent Format**: Notifications displayed during streaming (batched at the end) use a visual separator with "Jobs (N)" header, while notifications sent when NOT streaming are printed immediately as plain text with timestamp brackets. This creates a jarring, inconsistent experience.

2. **Prompt Clobbering**: When a notification arrives while the user is typing at the prompt, it writes directly to stdout, destroying the prompt line and any text the user has typed. The user must retype their input.

### Current Behavior

**During Streaming** (batched):
```
Alfred's response here...

────────────────────── Jobs (2) ──────────────────────
[2026-02-22 15:30:00 JOB NOTIFICATION] First message
[2026-02-22 15:30:01 JOB NOTIFICATION] Second message
──────────────────────────────────────────────────────

>>>
```

**Not Streaming** (immediate, clobbers prompt):
```
>>> user typing here[2026-02-22 15:30:00 JOB NOTIFICATION] Message appears inline, breaking everything
```

### Desired Behavior

All notifications should appear in the same visual format, and the prompt should always be preserved below them with user text intact:

```
>>> user typing here

────────────────────── Jobs (1) ──────────────────────
[2026-02-22 15:30:00 JOB NOTIFICATION] Message here
──────────────────────────────────────────────────────

>>> user typing here|   (cursor preserved)
```

---

## Goals

1. **Unified Visual Format**: All notifications use the same visual style regardless of when they arrive
2. **Prompt Preservation**: User-typed text is never lost; prompt redraws below notifications
3. **Cursor Position**: Cursor position within the input is maintained after redraw
4. **No Input Disruption**: The user can continue typing seamlessly after a notification appears

---

## Non-Goals

1. **Notification History**: Not implementing a scrollback buffer for past notifications
2. **Interactive Notifications**: Not adding buttons or actions to notifications
3. **Configurable Format**: Not making the visual format user-configurable (yet)
4. **Sound/Visual Alerts**: Not adding audio or OS-level notifications

---

## Technical Architecture

### Components Affected

1. **`src/cron/notifier.py`** — `CLINotifier._display()` method
2. **`src/interfaces/cli.py`** — `CLIInterface` class
3. **`src/interfaces/notification_buffer.py`** — `NotificationBuffer` class (minor changes)

### Key Technical Challenge

The primary challenge is integrating with **prompt_toolkit** to:
1. Clear the current prompt line(s) without losing the input buffer
2. Display the notification in the unified format
3. Redraw the prompt below with the user's partial input restored
4. Preserve cursor position within the input

### Solution Approach

**Prompt Toolkit Integration**:
- Access the `PromptSession`'s `app` instance to get the current input buffer
- Use `run_in_terminal()` to temporarily exit the prompt, print notification, then return
- Alternative: Use `patch_stdout` context manager adjustments for notification handling

**State Management**:
- Capture current input buffer content and cursor position before displaying
- Display notification using Rich console (for consistent formatting with streaming)
- Restore input buffer and cursor position after display

**Visual Format Unification**:
- Extract notification formatting into a shared method
- Use Rich Panels/Tables for consistent visual style
- Both streaming (batched) and non-streaming (immediate) use same formatter

---

## Implementation Plan

### Milestone 1: Extract Shared Notification Formatter

**Goal**: Create a unified formatting utility used by both streaming and non-streaming paths

**Tasks**:
- Create `format_notification()` function in `src/cron/notifier.py` or new module
- Accept notification message(s) and return Rich renderable(s)
- Format: Visual separator with "Jobs (N)" header, timestamped messages, closing separator
- Support single message (immediate) and batch (streaming) modes

**Validation**:
- Unit test: Single message formats correctly
- Unit test: Multiple messages format with correct count in header
- Visual inspection: Output matches streaming format exactly

### Milestone 2: Prompt State Capture and Restoration

**Goal**: Capture and restore prompt state without losing user input

**Tasks**:
- Implement `capture_prompt_state()` to get input buffer content and cursor position
- Implement `restore_prompt_state()` to redraw prompt with preserved state
- Handle multi-line input correctly
- Handle edge cases: empty input, input at column 0, etc.

**Validation**:
- Test: Type text, trigger notification, verify text preserved
- Test: Type text with cursor in middle, trigger notification, verify cursor position
- Test: Multi-line input preservation

### Milestone 3: Non-Streaming Notification Display

**Goal**: Display immediate notifications in unified format without clobbering prompt

**Tasks**:
- Modify `CLINotifier._display()` to use new formatter
- Integrate with prompt_toolkit's `run_in_terminal()` or equivalent
- Display notification below prompt, then redraw prompt with preserved input
- Handle concurrent notifications (queue if display in progress)

**Validation**:
- Manual test: Schedule a job, wait for notification while typing
- Verify visual format matches streaming batch format
- Verify prompt redraws correctly with user text

### Milestone 4: Unified Batching for Streaming

**Goal**: Update streaming notification flush to use same formatter

**Tasks**:
- Modify `CLINotifier.flush_buffer()` to use shared formatter
- Ensure visual output is identical to non-streaming path
- Remove old formatting code

**Validation**:
- Test: Verify streaming batch output unchanged (regression test)
- Test: Both paths produce identical visual output

### Milestone 5: Edge Cases and Polish

**Goal**: Handle edge cases and ensure production readiness

**Tasks**:
- Handle very long notifications (wrapping, truncation)
- Handle rapid successive notifications (debounce or queue)
- Handle terminal resize during notification display
- Handle Ctrl+C during notification display
- Performance: No perceptible delay in prompt redisplay

**Validation**:
- Test: 1000-character notification displays properly
- Test: 5 notifications arrive within 1 second (queue behavior)
- Test: Resize terminal, trigger notification
- Test: Ctrl+C during notification display (graceful handling)

### Milestone 6: Documentation Update

**Goal**: Update relevant documentation

**Tasks**:
- Update `docs/API.md` if notification interfaces changed
- Update README.md "Features" section if needed
- Add code comments explaining prompt state management

**Validation**:
- Documentation accurately reflects new behavior
- Code comments explain the "why" of prompt toolkit integration

---

## Testing Strategy

### Unit Tests

1. **Notification Formatting**:
   ```python
   def test_format_single_notification():
       result = format_notification("Test message")
       # Assert Rich renderable with correct structure
   
   def test_format_multiple_notifications():
       result = format_notifications(["Msg1", "Msg2"])
       # Assert header shows "Jobs (2)"
   ```

2. **Prompt State**:
   ```python
   def test_capture_restore_prompt_state():
       # Mock prompt_toolkit state
       # Capture, modify, restore, verify
   ```

### Integration Tests

1. **End-to-End Notification Flow**:
   ```python
   async def test_notification_preserves_input():
       # Start CLI, type text, trigger notification, verify preservation
   ```

### Manual Testing Checklist

- [ ] Single notification while typing short text
- [ ] Single notification while typing long text (wraps)
- [ ] Multiple rapid notifications
- [ ] Notification during multi-line input
- [ ] Notification with cursor at start/middle/end of input
- [ ] Notification during streaming (existing behavior)
- [ ] Terminal resize during notification
- [ ] Ctrl+C during notification display

---

## Success Criteria

1. **Visual Consistency**: All notifications appear in identical format (verified by visual comparison)
2. **Input Preservation**: 100% of user-typed text preserved across 50 manual test interactions
3. **Cursor Position**: Cursor position maintained within 1 character position in all tests
4. **No Disruption**: User can continue typing immediately after notification without retyping
5. **Performance**: Notification display + prompt redraw completes in <100ms

---

## Open Questions

1. **prompt_toolkit Integration**: Should we use `run_in_terminal()` or manipulate the renderer directly?
2. **Multi-line Input**: How to handle input that spans multiple terminal lines?
3. **Concurrent Notifications**: Queue or debounce when multiple arrive simultaneously?

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-22 | Option B (immediate display + redraw) | User wants real-time feedback, accepts complexity |
| 2026-02-22 | Unified format for all notifications | Consistency is primary goal |
| 2026-02-22 | Preserve cursor position | Complete UX fidelity |

---

## Related Links

- GitHub Issue: #89
- Current Implementation: `src/cron/notifier.py`, `src/interfaces/cli.py`
- Related PRD: #85 (Enhanced CLI Status Line)
