# PRD: Ctrl-T Tool Call Expansion

## Issue

[#131](https://github.com/jeremysball/alfred/issues/131)

---

## Problem

Users cannot view the full output of tool calls without manually scrolling through conversation history. Tool call boxes currently show truncated output (200 characters maximum), making it difficult to see complete results—especially for:

- File reads with extensive content
- Command outputs with multiple lines
- Tool results containing structured data (JSON, lists)
- Error messages that exceed the truncation limit

Users must mentally reconstruct partial information or re-run tools to see complete output.

---

## Solution

Add a **Ctrl-T** keyboard shortcut that toggles all tool call boxes between **compact** and **expanded** views. When expanded, tool calls display their complete output without truncation. This provides immediate "inspect all tools" capability without navigating individual messages.

### User Experience

1. User presses **Ctrl-T** at any time
2. All tool call boxes in the conversation immediately expand to full height
3. Full tool output is visible (no 200-char truncation)
4. User presses **Ctrl-T** again to collapse back to compact view
5. Entire scrollback rerenders to accommodate new box sizes

---

## Technical Requirements

### Core Functionality

- [ ] Add global `tool_calls_expanded` state to `AlfredTUI`
- [ ] Add Ctrl-T keybinding detection in input listener
- [ ] Modify `MessagePanel` to accept and respect expanded/collapsed state
- [ ] Update `_build_content_with_tools()` to conditionally truncate based on state
- [ ] Trigger full scrollback rerender when state toggles

### Visual Behavior

- **Compact view** (default): Tool output truncated to 200 characters, single-line args
- **Expanded view**: Full tool output, arguments fully visible, no truncation
- Both views preserve existing color coding and formatting
- Border styling unchanged between states

### Keybinding Details

| Key | Action |
|-----|--------|
| `Ctrl-T` | Toggle all tool calls between expanded/compact |

Keybinding integrates with existing `_input_listener` method in `tui.py`.

---

## Implementation Plan

### Milestone 1: State Management and Keybinding

Add global expansion state and wire up Ctrl-T detection.

**Files:**
- `src/alfred/interfaces/pypitui/tui.py`

**Changes:**
- Add `_tool_calls_expanded: bool = False` to `AlfredTUI.__init__`
- Add Ctrl-T detection in `_input_listener()`
- Create `_toggle_tool_expansion()` method

**Validation:**
- Ctrl-T logs state change (debug mode)
- State toggles between True/False

---

### Milestone 2: MessagePanel Expansion Support

Modify `MessagePanel` to render content based on expansion state.

**Files:**
- `src/alfred/interfaces/pypitui/message_panel.py`

**Changes:**
- Add `expanded: bool = False` parameter to `__init__`
- Add `set_expanded(expanded: bool)` method
- Modify `_build_content_with_tools()` to check `self._expanded`
- When expanded: show full `tc.output` without truncation
- When expanded: show full arguments without truncation

**Validation:**
- Unit tests for expanded vs compact rendering
- Tool output truncation respects state

---

### Milestone 3: Global State Propagation

Propagate expansion state to all message panels and trigger rerender.

**Files:**
- `src/alfred/interfaces/pypitui/tui.py`

**Changes:**
- In `_toggle_tool_expansion()`, iterate all conversation children
- Call `set_expanded()` on each `MessagePanel`
- Trigger `_populate_scrollback_by_scrolling()` to rerender entire history

**Validation:**
- All message panels receive state change
- Scrollback correctly recalculates

---

### Milestone 4: Integration Testing

Test complete feature with real conversation scenarios.

**Test scenarios:**
- Session with multiple tool calls across messages
- Tool calls with output >200 chars
- Toggle multiple times (expand → collapse → expand)
- Resize terminal while expanded
- Load session with existing tool calls, then expand

**Files:**
- `tests/pypitui/test_tool_expansion.py`

---

### Milestone 5: Documentation and Polish

Update help text and ensure smooth UX.

**Changes:**
- Add Ctrl-T to `ShortcutHelp.SHORTCUTS` in `key_bindings.py`
- Update help text to describe toggle behavior
- Ensure throbber animation continues smoothly during rerender

---

## Code Locations

### Primary Files

| File | Purpose |
|------|---------|
| `src/alfred/interfaces/pypitui/tui.py` | Main TUI class, keybinding handling |
| `src/alfred/interfaces/pypitui/message_panel.py` | Tool call rendering logic |
| `src/alfred/interfaces/pypitui/key_bindings.py` | Help text for shortcuts |

### Key Methods

| Method | Location | Change |
|--------|----------|--------|
| `_input_listener()` | `tui.py` | Add Ctrl-T detection |
| `_toggle_tool_expansion()` | `tui.py` | New method (state toggle) |
| `_build_content_with_tools()` | `message_panel.py` | Respect expanded state |
| `set_expanded()` | `message_panel.py` | New method |

---

## Truncation Logic Reference

Current truncation in `_build_content_with_tools()`:

```python
# Truncate output for display (show beginning, not end)
display_output = tc.output[:200] if len(tc.output) > 200 else tc.output
```

When `expanded=True`, this truncation should be skipped:

```python
# Expanded: show full output
# Compact: truncate to 200 chars
display_output = tc.output if self._expanded else (tc.output[:200] if len(tc.output) > 200 else tc.output)
```

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| No tool calls in conversation | Ctrl-T has no visible effect (no-op) |
| All tool calls already visible | Expansion shows more content; scrollback grows |
| Terminal very narrow | Expanded content may wrap heavily; acceptable |
| Streaming in progress | Toggle applies to completed tool calls; current continues |
| Session load then expand | Works correctly; all loaded tool calls expand |

---

## Success Criteria

- [ ] Ctrl-T toggles expansion state immediately
- [ ] All tool calls in conversation respect expansion state
- [ ] Full scrollback rerenders correctly (no visual glitches)
- [ ] Expanded view shows complete tool output (no truncation)
- [ ] Compact view preserves existing 200-char truncation
- [ ] Help text includes Ctrl-T shortcut
- [ ] Tests cover toggle behavior and edge cases

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-15 | Global toggle (not per-tool) | Simpler UX; "show me everything" is primary use case |
| 2026-03-15 | State not persisted | Temporary inspection view; reset on restart is acceptable |
| 2026-03-15 | Full rerender on toggle | Tool boxes change height; differential renderer handles efficiently |
| 2026-03-15 | No animation | Immediate toggle feels more responsive |

---

## Related PRDs

- PRD #94: PyPiTUI CLI (scrollback architecture)
- PRD #101: Tool Call Persistence (tool call storage)
