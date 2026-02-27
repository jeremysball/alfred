# PRD: Streaming Throbber for Alfred CLI

**Status**: In Progress — Bugs to Fix 🐛
**Priority**: Low
**Created**: 2026-02-26
**Completed**: 2026-02-26
**Depends on**: 95-pypitui-cli

## Open Issues

1. **Throbber delay** — Should start immediately on send, not when streaming begins
   - **Status**: ✅ FIXED - Added `_is_sending` state that triggers immediately on submit
   
2. **Scrollback on resize** — Verify content re-prints correctly after terminal resize  
   - **Status**: 🐛 OPEN - Needs investigation
   
3. **Status line layout** — Always appears compact; width detection may be broken
   - **Status**: 🐛 OPEN - Added debug logging, needs runtime verification

---

## Problem Statement

When Alfred is streaming a response, there's no visual indication that activity is happening. On slow responses, users may wonder if the application is frozen.

---

## Solution Overview

Add an animated throbber (spinner) to the status line during streaming that provides visual feedback that the LLM is generating a response.

---

## Design Options

### Option A: Braille Spinner

```
⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏
```

- **Pros**: Smooth, compact, widely used
- **Cons**: Requires braille font support

### Option B: Dot Pulse

```
●○○○  ○●○○  ○○●○  ○○○●
```

- **Pros**: Simple, universal
- **Cons**: Larger, less smooth

### Option C: ASCII Spinner

```
| / - \
```

- **Pros**: Universal compatibility
- **Cons**: Retro look, less polished

### Recommendation

Use **Braille spinner** with **ASCII fallback** if braille detection fails.

---

## Implementation TODO

### Phase 1: Basic Animation

**Tests first:**
- [x] `test_throbber_advances_on_tick()` — Each tick moves to next frame
- [x] `test_throbber_loops()` — After last frame, returns to first
- [x] `test_throbber_hidden_when_not_streaming()` — No throbber in idle state

**Implementation:**
- [x] Create `Throbber` class with frame sequence
- [x] Add `tick()` method to advance frame
- [x] Add `render()` method to return current frame

### Phase 2: Status Line Integration

**Tests first:**
- [x] `test_status_shows_throbber_when_streaming()` — Throbber appears during stream
- [x] `test_throbber_position()` — Placed before model name
- [x] `test_throbber_tick_advances()` — Animation advances in main loop

**Implementation:**
- [x] Add `streaming` flag to StatusLine.update()
- [x] Call `throbber.tick()` via `tick_throbber()` method
- [x] Render throbber before model name in status line

### Phase 3: Animation Loop

**Tests first:**
- [x] `test_throbber_updates_in_main_loop()` — tick_throbber called each frame
- [x] `test_throbber_resets_on_stream_end()` — Animation resets when streaming stops

**Implementation:**
- [x] Call `status_line.tick_throbber()` in main loop
- [x] Reset throbber when streaming ends (in update with streaming=False)

---

## Throbber Class

```python
class Throbber:
    """Animated loading indicator."""

    BRAILLE_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    ASCII_FRAMES = ["|", "/", "-", "\\"]

    def __init__(self, use_braille: bool = True):
        self._frames = self.BRAILLE_FRAMES if use_braille else self.ASCII_FRAMES
        self._index = 0

    def tick(self) -> None:
        """Advance to next frame."""
        self._index = (self._index + 1) % len(self._frames)

    def render(self) -> str:
        """Return current frame."""
        return self._frames[self._index]

    def reset(self) -> None:
        """Reset to first frame."""
        self._index = 0
```

---

## Status Line Layout with Throbber

```
⠋ kimi/kimi-k2-5 | ↓1.2K ↑150
```

Or after tokens:

```
kimi/kimi-k2-5 | ↓1.2K ↑150 | ⠋
```

**Recommendation**: Before model name, as it indicates activity on that model.

---

## Animation Timing

| Setting | Value | Rationale |
|---------|-------|-----------|
| Frame rate | 10 fps | Smooth but not distracting |
| Frame duration | 100ms | Easy to calculate |
| Sync with render | Yes | Update in main loop |

---

## Color Options

| Option | ANSI | Use Case |
|--------|------|----------|
| Dim cyan | `\x1b[36m` | Calm, matches streaming theme |
| Dim yellow | `\x1b[33m` | More visible, attention-grabbing |
| Dim white | `\x1b[2m` | Subtle, doesn't distract |

**Recommendation**: Dim cyan for calm, professional look.

---

## Testing Strategy

### Unit Tests
- Frame advancement
- Loop behavior
- Color application

### Visual Testing
```bash
# Start Alfred, send message
# Verify throbber animates during response
# Verify throbber stops when complete
```

---

## Bug Fixes Required

### Bug 1: Throbber Should Start Immediately After Sending

**Current behavior:** Throbber starts when streaming begins (network response received).

**Expected behavior:** Throbber should start immediately when user presses Enter, before network request.

**Root cause:** `_is_streaming` is set to `True` at the start of `_send_message()`, but network latency means there's a visible delay before any animation appears.

**Fix:** Set `streaming=True` immediately in `_on_submit()` before creating the async task, or add a new "sending" state that shows throbber while waiting for first chunk.

---

### Bug 2: Scrollback Not Re-printed After Resize

**Current behavior:** When terminal is resized, conversation content may not re-render correctly.

**Expected behavior:** All scrollback content should be re-printed at new width on resize.

**Root cause:** PyPiTUI handles resize via `terminal.get_size()` in render, but the conversation Container may not be triggering a full re-render of all messages.

**Fix:** Verify that resize triggers `request_render()` on the conversation container and that all MessagePanel components re-render with new width.

**Verification:**
```bash
# 1. Start alfred, send several messages
# 2. Resize terminal window (make narrower or wider)
# 3. Check if all previous messages re-wrap correctly
# 4. Verify scrollback buffer contains properly formatted content
```

---

### Bug 3: Status Line Always Uses Compact Layout

**Current behavior:** Status line always appears to use the smallest/compact layout regardless of terminal width.

**Expected behavior:** Status line should use full/medium/compact layout based on actual terminal width.

**Root cause investigation needed:**
1. Is `width` parameter in `render(width)` correct?
2. Are the threshold constants (`STATUS_WIDTH_FULL`, etc.) appropriate?
3. Is the width being passed from TUI correctly?

**Debug steps:**
```python
# Add logging to StatusLine.render()
print(f"DEBUG: render called with width={width}")
print(f"DEBUG: thresholds: full={STATUS_WIDTH_FULL}, medium={STATUS_WIDTH_MEDIUM}")
print(f"DEBUG: _is_streaming={self._is_streaming}, _model={self._model}")
```

**Potential issues:**
- Width may be 0 or incorrect during initial render
- TUI may not be passing terminal width correctly
- Threshold constants may be too high for typical terminal sizes

---

## Out of Scope

- Custom throbber styles (user configurable)
- Sound notification
- Progress percentage (not available from LLM)

---

## References

- StatusLine component: `src/interfaces/pypitui/status_line.py`
- Main loop: `src/interfaces/pypitui/tui.py`
- AlfredTUI: `src/interfaces/pypitui/tui.py`
