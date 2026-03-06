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

When a notification arrives while the user is typing, the notification appears **above** the prompt, and the prompt is redrawn below with user text intact:

**Before notification:**
```
>>> hello how are|
```

**After notification:**
```
────────────────────── Jobs (1) ──────────────────────
[2026-02-22 15:30:00 JOB NOTIFICATION] Message here
──────────────────────────────────────────────────────

>>> hello how are|
```

The prompt stays at the bottom. User text and cursor position are preserved automatically.

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
- Use `run_in_terminal()` from prompt_toolkit — it handles everything automatically:
  1. Hides the prompt temporarily
  2. Runs a function that prints the notification
  3. Re-renders the prompt below with input buffer and cursor preserved
- No manual state capture/restore needed

**Visual Format Unification**:
- Extract notification formatting into a shared method
- Use Rich console for consistent formatting
- Both streaming (batched) and non-streaming (immediate) use same formatter

---

## Implementation Plan

### Milestone 1: Extract Shared Notification Formatter

**Goal**: Create a unified formatting utility used by both streaming and non-streaming paths

**Tasks**:
- Create `format_notifications()` function in `src/cron/notifier.py`
- Accept list of notification messages and return Rich renderable
- Format: Visual separator with "Jobs (N)" header, timestamped messages, closing separator
- Support single message (immediate) and batch (streaming) modes

**Validation**:
- Unit test: Single message formats correctly
- Unit test: Multiple messages format with correct count in header
- Visual inspection: Output matches streaming format exactly

### Milestone 2: Non-Streaming Notification Display with `run_in_terminal`

**Goal**: Display immediate notifications above prompt without clobbering user input

**Tasks**:
- Modify `CLINotifier` to hold reference to `PromptSession` (or use callback pattern)
- Create `_display_with_prompt()` method that uses `run_in_terminal()`
- Print notification using shared formatter inside `run_in_terminal()` callback
- Update `CLINotifier.send()` to use new display method when prompt is active

**Validation**:
- Manual test: Schedule a job, type text at prompt, wait for notification
- Verify: Notification appears above prompt, user text preserved
- Verify: Cursor position maintained

### Milestone 3: Unified Batching for Streaming

**Goal**: Update streaming notification flush to use same formatter

**Tasks**:
- Modify `CLINotifier.flush_buffer()` to use shared `format_notifications()`
- Ensure visual output is identical to non-streaming path
- Remove old formatting code

**Validation**:
- Test: Verify streaming batch output unchanged (regression test)
- Test: Both paths produce identical visual output

### Milestone 4: Edge Cases and Polish

**Goal**: Handle edge cases and ensure production readiness

**Tasks**:
- Handle very long notifications (wrapping, truncation)
- Handle rapid successive notifications (queue in buffer, display together)
- Handle notification when prompt not active (startup, between interactions)
- Performance: No perceptible delay in prompt redisplay

**Validation**:
- Test: 1000-character notification displays properly
- Test: 5 notifications arrive within 1 second (batched display)
- Test: Notification during startup (graceful fallback)

### Milestone 5: Documentation Update

**Goal**: Update relevant documentation

**Tasks**:
- Add code comments explaining `run_in_terminal()` usage
- Update README.md if needed

**Validation**:
- Code comments explain the "why" of prompt_toolkit integration

---

## Testing Strategy

### Unit Tests

1. **Notification Formatting**:
   ```python
   def test_format_single_notification():
       result = format_notifications(["Test message"])
       # Assert Rich renderable with correct structure
   
   def test_format_multiple_notifications():
       result = format_notifications(["Msg1", "Msg2"])
       # Assert header shows "Jobs (2)"
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
- [ ] Multiple rapid notifications (verify batching)
- [ ] Notification during multi-line input
- [ ] Notification with cursor at start/middle/end of input
- [ ] Notification during streaming (existing behavior unchanged)
- [ ] Notification when prompt not active (startup, between interactions)

---

## Success Criteria

1. **Visual Consistency**: All notifications appear in identical format (verified by visual comparison)
2. **Input Preservation**: 100% of user-typed text preserved across 50 manual test interactions
3. **Cursor Position**: Cursor position maintained within 1 character position in all tests
4. **No Disruption**: User can continue typing immediately after notification without retyping
5. **Performance**: Notification display + prompt redraw completes in <100ms

---

## Open Questions

1. **Multi-line Input**: How does `run_in_terminal()` handle input that spans multiple terminal lines? (Test during implementation)
2. **Concurrent Notifications**: Queue in buffer and display together, or display each immediately? (Recommend: queue in buffer)

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-22 | Use `run_in_terminal()` | prompt_toolkit API handles hide/show prompt, preserves input buffer automatically |
| 2026-02-22 | Notification above prompt (Option B) | Cleaner UX — prompt stays at bottom, notification scrolls above |
| 2026-02-22 | Unified format for all notifications | Consistency is primary goal |
| 2026-02-22 | Preserve cursor position | Complete UX fidelity |

---

## Related Links

- GitHub Issue: #89
- Current Implementation: `src/cron/notifier.py`, `src/interfaces/cli.py`
- Related PRD: #85 (Enhanced CLI Status Line)
