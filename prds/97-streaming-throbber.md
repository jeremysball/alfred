# PRD: Streaming Throbber for Alfred CLI

**Status**: Complete ✅
**Priority**: Low
**Created**: 2026-02-26
**Completed**: 2026-02-26
**Depends on**: 95-pypitui-cli

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

## Out of Scope

- Custom throbber styles (user configurable)
- Sound notification
- Progress percentage (not available from LLM)

---

## References

- StatusLine component: `src/interfaces/pypitui/status_line.py`
- Main loop: `src/interfaces/pypitui/tui.py`
