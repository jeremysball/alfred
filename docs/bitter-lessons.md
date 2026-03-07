# Bitter Lessons

Hard-won knowledge from debugging painful issues.

---

## Terminal Cursor Handling

**Lesson**: The hardware cursor and virtual cursor are separate concerns. Never assume they're synchronized.

**What went wrong**: Over SSH with network lag, the hardware cursor (terminal's native cursor) became visible and drifted from our virtual cursor (reverse video in the input field). After ~10 minutes they converged at the status line, breaking input.

**Root cause**: We hid the hardware cursor once at startup (`\x1b[?25l`) but never repositioned it. Terminal state corruption (from resize, focus changes, or network issues) could make it visible again.

**Solution**: 
- Hardware cursor must be moved to match virtual cursor every frame
- Use `CURSOR_MARKER` (`\x1b_pi:c\x07`) to locate virtual cursor in rendered output
- Position hardware cursor via `terminal.move_cursor(row, col)`
- If hardware cursor becomes visible, at least it's in the right place

**Code pattern**:
```python
# Extract virtual cursor position from rendered lines
cursor_pos = self._extract_cursor_position(lines, term_height)
if cursor_pos:
    row, col = cursor_pos
    # Convert to screen coordinates and position hardware cursor
    screen_row = row - first_visible
    if screen_row >= 0:
        self.terminal.move_cursor(screen_row, col)
```

---

## SIGWINCH and Terminal Resize

**Lesson**: Polling for terminal size every frame is wasteful and misses rapid resizes. Use SIGWINCH.

**What went wrong**: We called `terminal.get_size()` every frame (~60/sec) to detect resizes. This caused unnecessary syscalls and could miss resizes that happened between frames.

**Root cause**: No signal handling for window resize events.

**Solution**:
- Set up SIGWINCH handler that flags resize needs
- Update cached size only when SIGWINCH fires
- PyPiTUI cache + Alfred components update separately

**Code pattern**:
```python
# Alfred sets up handler
def _setup_sigwinch_handler(self):
    def handle_sigwinch(signum, frame):
        self._resize_pending = True
    signal.signal(signal.SIGWINCH, handle_sigwinch)

# Main loop handles when flag is set
if self._resize_pending:
    self.tui.request_resize_check()  # Update PyPiTUI cache
    self._update_components()         # Update Alfred stuff
    self.tui.request_render(force=True)
```

---

## DEC 2026 Synchronized Output

**Lesson**: DEC 2026 (`\x1b[?2026h`/`\x1b[?2026l`) can cause display freeze if end sync is lost.

**What went wrong**: (Investigating) Terminal may be stuck waiting for end sync marker.

**Hypothesis**: If `\x1b[?2026h` (begin sync) is sent but `\x1b[?2026l` (end sync) is lost or corrupted over network, terminal buffers all subsequent output indefinitely.

**Potential solutions**:
- Add timeout: if no frame rendered for >5s, force `\x1b[?2026l` and reset
- Recovery sequence: `\x1b[?2026l\x1b[r\x1b[2J\x1b[H` (end sync, reset region, clear, home)
- Disable DEC 2026 in problematic environments (mosh, high-latency SSH)
- Ensure sync markers are always paired (even on exception paths)

---
