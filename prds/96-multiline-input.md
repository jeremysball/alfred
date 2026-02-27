# PRD: Multi-line Input for Alfred CLI

**Status**: Proposed
**Priority**: Medium
**Created**: 2026-02-26
**Depends on**: 95-pypitui-cli

---

## Problem Statement

The current input field is single-line only. Users cannot:
- Write multi-line messages (code snippets, lists, paragraphs)
- Navigate with arrow keys within wrapped text
- Paste multi-line content properly

This limits Alfred's usefulness for coding tasks and detailed questions.

---

## Solution Overview

Enhance the Input component to support multi-line editing with:

1. **Visual word wrapping** — Long lines wrap at terminal width
2. **Arrow key navigation** — Move cursor within wrapped display
3. **Shift+Enter** — Insert newline without submitting
4. **Multi-line paste** — Handle pasted newlines correctly
5. **Scrolling input** — When input exceeds available space

---

## Architecture

### Current State

```
Input (single line)
├── _value: str
├── _cursor_pos: int (character position)
└── render() → single line with cursor marker
```

### Proposed State

```
Input (multi-line)
├── _value: str (may contain newlines)
├── _cursor_pos: int (character position in value)
├── _scroll_offset: int (first visible line)
└── render(width, max_lines) → wrapped lines with cursor
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Storage | Single string with `\n` | Simple, matches user mental model |
| Cursor | Character position in string | Works across line boundaries |
| Display | Wrap to width at render time | Responsive to terminal resize |
| Submit | Enter (single line) / Shift+Enter (newline) | Standard pattern |
| Max height | 5 lines visible, scroll beyond | Balance input vs conversation |

---

## Implementation TODO

### Phase 1: Basic Multi-line

**Tests first:**
- [ ] `test_input_accepts_newline()` — Shift+Enter inserts `\n`
- [ ] `test_input_renders_multiline()` — Value with `\n` renders as multiple lines
- [ ] `test_cursor_navigates_newline()` — Left/right crosses line boundaries
- [ ] `test_submit_sends_multiline()` — Enter sends full multi-line value

**Implementation:**
- [ ] Modify `Input._handle_key()` to detect Shift+Enter
- [ ] Insert `\n` at cursor position on Shift+Enter
- [ ] Update `render()` to split on `\n` and wrap each line
- [ ] Cursor position calculation across lines

### Phase 2: Arrow Key Navigation

**Tests first:**
- [ ] `test_left_arrow_at_line_start()` — Moves to end of previous line
- [ ] `test_right_arrow_at_line_end()` — Moves to start of next line
- [ ] `test_up_arrow_moves_to_previous_line()` — Up navigates vertically
- [ ] `test_down_arrow_moves_to_next_line()` — Down navigates vertically
- [ ] `test_vertical_movement_targets_closest_column()` — Up/down maintains column

**Implementation:**
- [ ] Track display column (where cursor appears visually)
- [ ] Calculate line start/end positions for navigation
- [ ] Map display coordinates to string position
- [ ] Handle wrapped lines (one logical line = multiple display lines)

### Phase 3: Word Wrapping

**Tests first:**
- [ ] `test_long_line_wraps()` — Line longer than width wraps
- [ ] `test_wrap_preserves_content()` — Wrapped content matches original
- [ ] `test_cursor_in_wrapped_line()` — Cursor navigates wrapped segments
- [ ] `test_resize_rewraps()` — Changing width re-wraps content

**Implementation:**
- [ ] Use `wrap_text_with_ansi()` from pypitui
- [ ] Calculate cursor position in wrapped display
- [ ] Handle ANSI codes in wrapped text

### Phase 4: Scrolling

**Tests first:**
- [ ] `test_input_scrolls_when_exceeds_max()` — Only last N lines visible
- [ ] `test_cursor_scroll_adjustment()` — Typing scrolls to keep cursor visible
- [ ] `test_scroll_with_page_keys()` — Page Up/Down scrolls input

**Implementation:**
- [ ] Add `_scroll_offset` state
- [ ] Calculate visible lines based on `max_visible_lines`
- [ ] Scroll to keep cursor in view
- [ ] Page Up/Down key handling

### Phase 5: Paste Handling

**Tests first:**
- [ ] `test_paste_multiline()` — Paste with newlines inserts correctly
- [ ] `test_paste_replaces_selection()` — Selected text replaced by paste
- [ ] `test_large_paste_truncated()` — Very large paste limited

**Implementation:**
- [ ] Detect bracketed paste mode sequences
- [ ] Insert paste content at cursor
- [ ] Handle newlines in paste

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Submit message |
| `Shift+Enter` | Insert newline |
| `↑` | Move up one line |
| `↓` | Move down one line |
| `←` | Move left one character |
| `→` | Move right one character |
| `Ctrl+A` / `Home` | Move to start of line |
| `Ctrl+E` / `End` | Move to end of line |
| `Ctrl+U` | Delete to start of line |
| `Ctrl+K` | Delete to end of line |
| `Page Up` | Scroll input up |
| `Page Down` | Scroll input down |

---

## Visual Design

```
┌─ Message (3 lines) ─────────────────────────┐
│ This is a multi-line message that wraps     │
│ across several lines when the terminal is   │
│ narrow.█                                    │
└─────────────────────────────────────────────┘

Status: kimi/kimi-k2-5 | ↓1.2K ↑150 | 💬3
```

- Cursor shown as `█` block
- No border around input (cleaner look)
- Height expands to max 5 lines, then scrolls

---

## Edge Cases

- **Empty lines** — Preserve blank lines in input
- **Only whitespace** — Submit should ignore (existing behavior)
- **Very long single word** — Break at width boundary
- **Unicode** — Handle multi-byte characters correctly
- **ANSI codes** — Preserve color codes in wrapped text

---

## Testing Strategy

### Unit Tests
- All navigation scenarios
- Wrap calculations
- Scroll behavior

### E2E Tests (tmux)
```bash
# Type multi-line message
tmux send-keys "line 1" Shift-Enter "line 2" Enter
# Verify both lines in response
```

### Manual Validation
- [ ] Type 3 lines, verify all sent
- [ ] Navigate up/down within input
- [ ] Paste code snippet
- [ ] Resize terminal while typing

---

## Out of Scope

- Rich text formatting in input
- Tab completion
- Input history (up arrow for previous messages)

---

## References

- pypitui Input component: `/workspace/pypitui/src/pypitui/components.py`
- wrap_text_with_ansi: `/workspace/pypitui/src/pypitui/utils.py`
