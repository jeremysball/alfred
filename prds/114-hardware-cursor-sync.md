# Hardware Cursor Synchronization in PyPiTUI

## Issue #114

---

## Problem Statement

When using Alfred over SSH with network lag, the hardware cursor becomes desynchronized from the virtual cursor (reverse video in the input field). After approximately 10 minutes:

1. The hardware cursor drifts and becomes visible at the status line
2. The virtual cursor remains correctly positioned in the input field (green background after diagnostic change)
3. User input becomes impossible because keystrokes are sent to the hardware cursor position (wrong location)

This is a terminal state corruption issue where the hidden hardware cursor becomes visible and loses its position synchronization.

---

## Root Cause Analysis

### Current Behavior

| Phase | Hardware Cursor | Virtual Cursor |
|-------|----------------|----------------|
| TUI Start | `hide_cursor()` → `\x1b[?25l` | Rendered at input field |
| Operation | **Never touched** | Updated as user types |
| TUI Stop | `show_cursor()` → `\x1b[?25h` | - |

The hardware cursor is hidden once and never repositioned. The virtual cursor uses:
- `CURSOR_MARKER = "\x1b_pi:c\x07"` (APC sequence for detection)
- Reverse video or colored background (user-visible cursor)

### Why It Fails

Over SSH with network conditions:
1. Terminal resize events, focus changes, or escape sequence corruption can cause the hidden hardware cursor to become visible
2. Since we never position the hardware cursor, it stays wherever the terminal last left it
3. Eventually it drifts to the status line (last rendered content before input field)
4. **Result**: Two visible cursors - virtual (correct) and hardware (wrong position)
5. Terminal sends input to the **hardware cursor position** → broken input

### Existing Infrastructure

PyPiTUI already has:
- `_extract_cursor_position(lines, height)` - Finds `CURSOR_MARKER` in rendered output
- `terminal.move_cursor(row, col)` - Positions hardware cursor
- `CURSOR_MARKER` constant - APC sequence for marking cursor position

**The method exists but is never called.**

---

## Solution

### Core Fix

Every frame in `render_frame()`:

1. Extract virtual cursor position from rendered lines using `_extract_cursor_position()`
2. Convert scrollback-relative coordinates to screen-relative coordinates
3. Move hardware cursor to match: `terminal.move_cursor(screen_row, col)`
4. Keep hardware cursor hidden (`\x1b[?25l`) - but if it becomes visible, it's in the right place

### Coordinate Conversion

```python
def render_frame(self) -> None:
    # ... existing render logic ...
    
    # Extract virtual cursor position
    cursor_pos = self._extract_cursor_position(lines, term_height)
    if cursor_pos:
        row, col = cursor_pos
        # Convert from scrollback-relative to screen-relative
        first_visible = max(0, len(lines) - term_height)
        screen_row = row - first_visible
        if screen_row >= 0:  # Cursor is visible on screen
            self.terminal.move_cursor(screen_row, col)
    
    # ... rest of render ...
```

### Edge Cases

1. **No cursor marker found**: Input field not focused - don't move hardware cursor
2. **Cursor above viewport**: Scrolled out of view - don't move (hardware cursor stays at last visible position)
3. **Overlays with input**: Topmost focused component's cursor wins (last rendered)
4. **Terminal doesn't support cursor positioning**: Graceful degradation (hardware cursor just won't sync)

---

## Milestones

### M1: Extract and Position Hardware Cursor
- [ ] Call `_extract_cursor_position()` every frame in `render_frame()`
- [ ] Calculate screen-relative coordinates from scrollback-relative position
- [ ] Call `terminal.move_cursor(screen_row, col)` to sync hardware cursor
- [ ] Handle case when no cursor marker is found (no focused input)

### M2: Test with SSH and Network Lag
- [ ] Run Alfred over SSH for extended period (30+ minutes)
- [ ] Verify hardware cursor stays synchronized with virtual cursor
- [ ] Confirm input works correctly even if hardware cursor becomes visible
- [ ] Test with terminal resize events during operation

### M3: Handle Edge Cases
- [ ] Cursor scrolled above viewport (don't position off-screen)
- [ ] Multiple input fields in overlays (topmost wins)
- [ ] Rapid focus switching (cursor follows correctly)
- [ ] Terminal resize mid-frame (coordinates recalculated)

### M4: Performance Optimization
- [ ] Only move cursor when position changed (avoid unnecessary terminal writes)
- [ ] Cache last cursor position to detect changes
- [ ] Benchmark frame time impact (should be negligible)

### M5: Regression Testing
- [ ] Ensure existing TUI functionality unaffected
- [ ] Verify cursor positioning works on different terminal emulators
- [ ] Test with mosh (mobile shell) which has different buffering behavior
- [ ] Confirm no visual artifacts or flickering

---

## Success Criteria

- [ ] Hardware cursor stays synchronized with virtual cursor during extended SSH sessions
- [ ] Input works correctly even if hardware cursor becomes visible due to terminal state issues
- [ ] No performance degradation (frame time stays < 16ms for 60fps)
- [ ] Works across terminal emulators: iTerm2, Terminal.app, Alacritty, GNOME Terminal, etc.
- [ ] Works with connection tools: SSH, mosh, tmux, screen

---

## Technical Notes

### Files to Modify

1. **`/workspace/pypitui/src/pypitui/tui.py`**
   - `render_frame()` method - Add cursor extraction and positioning
   - Add `_last_cursor_pos` instance variable for change detection

### Implementation Details

```python
# In TUI.__init__
self._last_cursor_screen_pos: tuple[int, int] | None = None

# In render_frame(), after compositing overlays and applying resets:
cursor_pos = self._extract_cursor_position(lines, term_height)
if cursor_pos:
    row, col = cursor_pos
    first_visible = max(0, len(lines) - term_height)
    screen_row = row - first_visible
    
    if screen_row >= 0:
        new_pos = (screen_row, col)
        if new_pos != self._last_cursor_screen_pos:
            self.terminal.move_cursor(screen_row, col)
            self._last_cursor_screen_pos = new_pos
```

### Testing Strategy

1. **Manual**: Extended SSH session with periodic typing
2. **Manual**: Terminal resize during operation
3. **Manual**: Focus switch between input fields
4. **Manual**: Scrollback navigation (Shift+PgUp/PgDn)
5. **Automated**: Unit test for coordinate conversion
6. **Automated**: Mock terminal to verify move_cursor calls

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-06 | Sync hardware cursor every frame | Ensures immediate correction if terminal state drifts |
| 2026-03-06 | Only move when position changes | Avoids unnecessary terminal writes for performance |
| 2026-03-06 | Keep cursor hidden normally | Hardware cursor positioning is defensive - primary cursor is virtual |

---

## Related

- Issue #114 (this PRD)
- PyPiTUI repository: `/workspace/pypitui/`
- Alfred TUI implementation: `/workspace/alfred-prd/src/interfaces/pypitui/`
