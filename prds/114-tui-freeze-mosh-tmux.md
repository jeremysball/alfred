# TUI Display Freeze in Mosh + Tmux

## Problem Statement

When running Alfred through **mosh + tmux**, the TUI display freezes after approximately 10 minutes while input continues to work:

- **Display**: Frozen frame (no updates visible)
- **Input**: Keystrokes ARE processed by Alfred (messages appear after restart)
- **Cursors**: Both virtual and hardware cursors are correctly positioned and visible
- **Environment**: Docker container → mosh → tmux → Alfred

### Key Observation
The bug is specific to **mosh + tmux**. In plain SSH, the issue manifests differently (hardware cursor drift). In mosh, the display structure remains intact but stops updating.

---

## Root Cause Analysis

### Mosh Architecture

```
[Local Terminal] ←→ [mosh-client] ←UDP→ [mosh-server] ←→ [tmux] ←→ [Alfred TUI]
```

1. Keystrokes: Local → mosh-client → UDP → mosh-server → tmux → Alfred ✓ Works
2. Display: Alfred → tmux → mosh-server → UDP → mosh-client → Local ✗ Freezes

### Suspected Causes

#### 1. Synchronized Output (DEC 2026) State Corruption

Both Alfred and PyPiTUI use DEC 2026 (`\x1b[?2026h` / `\x1b[?2026l`) for flicker-free rendering:

- **PyPiTUI**: Wraps every frame in sync markers
- **Alfred**: Uses sync markers in `_populate_scrollback_by_scrolling()`

Potential issues:
- Nested sync markers (Alfred calls scrollback code during PyPiTUI render)
- Incomplete sync sequence (crash/exception between begin/end)
- mosh's predictive rendering interfering with sync state

#### 2. UDP Timeout / Buffer Exhaustion

mosh uses UDP for server→client communication. If:
- UDP packets are dropped
- mosh-server thinks client is stale
- Buffer fills up and blocks

The display updates stop while input continues.

#### 3. Tmux Pane State Issues

tmux may enter a state where:
- Scroll region is set but not reset
- Alternate screen buffer is corrupted
- Output is being captured/scrolled instead of displayed

#### 4. Stdout Blocking

If the stdout buffer fills up (mosh-server not reading), writes could block. However, the async event loop should prevent this.

---

## Diagnostic Plan

Before implementing fixes, we need to confirm the root cause:

### 1. Disable DEC 2026 Synchronized Output

Test if the freeze still occurs without synchronized output:

```python
# In PyPiTUI tui.py, modify _begin_sync() and _end_sync():
def _begin_sync(self) -> str:
    return ""  # Disable sync

def _end_sync(self) -> str:
    return ""  # Disable sync
```

### 2. Add Health Check / Heartbeat

Every N seconds, force a full redraw and check if it appears:

```python
self._last_render_time = time.time()

# In render_frame()
if time.time() - self._last_render_time > 30:
    # Force terminal reset and full redraw
    self._force_terminal_reset()
```

### 3. Detect Mosh Environment

Check if running under mosh:

```bash
# Mosh sets specific environment variables or we can detect via ps
if os.environ.get('MOSH') or 'mosh' in os.environ.get('TERM_PROGRAM', ''):
    # Use mosh-safe rendering
```

### 4. Add Debug Logging

Log every render frame to a file:

```python
with open('/tmp/alfred-render.log', 'a') as f:
    f.write(f"{time.time()}: render_frame called, {len(buffer)} bytes\n")
```

---

## Proposed Solutions

### Solution A: Mosh-Safe Rendering Mode (Recommended)

When mosh is detected, disable optimizations that may cause issues:

1. **Disable DEC 2026**: Use simple rendering without synchronized output
2. **Increase frame rate**: mosh needs more frequent updates for smoothness
3. **Force full redraw periodically**: Every 5 seconds, do `\x1b[2J\x1b[H` + full redraw
4. **Reset scroll region before each frame**: Ensure no stale scroll regions

### Solution B: Watchdog / Recovery

Detect freeze and automatically recover:

1. **Heartbeat timer**: Track last successful render timestamp
2. **Health check**: If no render for 5 seconds, attempt recovery:
   - Reset terminal: `\x1b[?25h\x1b[r\x1b[2J\x1b[H` (show cursor, reset region, clear, home)
   - Force full redraw: Invalidate all caches and redraw everything
   - Log recovery event

### Solution C: Simplified Rendering for Remote Connections

Provide a `--simple` or `--remote` flag:

- Disable all advanced terminal features
- Use basic cursor positioning only
- No scroll regions, no synchronized output, no scrollback manipulation
- Trade visual polish for reliability

---

## Milestones

### M1: Root Cause Confirmation
- [ ] Test with DEC 2026 disabled (Solution A verification)
- [ ] Add render logging to confirm freeze is in output, not rendering logic
- [ ] Verify mosh UDP connection is alive when freeze occurs
- [ ] Document which specific escape sequence causes the freeze

### M2: Mosh Detection and Safe Mode
- [ ] Implement mosh environment detection
- [ ] Create `--mosh-safe` flag or auto-detect
- [ ] When in mosh-safe mode:
  - [ ] Disable DEC 2026 synchronized output
  - [ ] Disable scroll region manipulation in Alfred scrollback
  - [ ] Force full redraw every N frames
- [ ] Test extended session (1+ hour) in mosh+tmux

### M3: Watchdog Recovery Mechanism
- [ ] Implement render heartbeat tracking
- [ ] Add automatic recovery on freeze detection
- [ ] Recovery sequence: reset terminal state + force full redraw
- [ ] Log recovery events for debugging
- [ ] Test recovery triggers correctly and doesn't cause loops

### M4: Performance Validation
- [ ] Benchmark rendering performance in safe mode vs normal mode
- [ ] Ensure no flickering in mosh-safe mode
- [ ] Verify CPU usage remains reasonable
- [ ] Test with large scrollback history

### M5: Documentation and User Guidance
- [ ] Document known issues with mosh/tmux
- [ ] Add `--mosh-safe` to CLI help
- [ ] Add troubleshooting section to README
- [ ] Provide workaround: use plain SSH if mosh continues to have issues

---

## Implementation Details

### Files to Modify

1. **`/workspace/pypitui/src/pypitui/tui.py`**
   - Add `mosh_safe` parameter to `TUI.__init__`
   - Conditionally disable DEC 2026 in `_begin_sync()` / `_end_sync()`
   - Add render heartbeat tracking

2. **`/workspace/alfred-prd/src/interfaces/pypitui/tui.py`**
   - Add mosh detection logic
   - Pass mosh-safe flag to PyPiTUI
   - Disable scroll region manipulation in `_populate_scrollback_by_scrolling()` when in safe mode
   - Add watchdog recovery in main loop

3. **`/workspace/alfred-prd/src/cli/main.py`**
   - Add `--mosh-safe` CLI flag
   - Pass flag to TUI initialization

### Mosh Detection

```python
def is_mosh() -> bool:
    """Detect if running under mosh."""
    # Check environment variables
    if os.environ.get('MOSH'):
        return True
    # Check parent process
    try:
        with open(f'/proc/{os.getppid()}/comm') as f:
            if 'mosh' in f.read():
                return True
    except:
        pass
    return False
```

### Safe Mode Rendering

```python
# In PyPiTUI TUI class
def render_frame(self) -> None:
    if self._stopped:
        return
    
    # Health check
    if self._mosh_safe and time.time() - self._last_successful_render > 5:
        self._recover_from_freeze()
    
    # Normal render with mosh-safe adjustments
    # ...
    
    if self._mosh_safe:
        # Reset scroll region before frame
        buffer = "\x1b[r" + buffer
        self._last_successful_render = time.time()

def _recover_from_freeze(self) -> None:
    """Reset terminal state and force full redraw."""
    self.terminal.write("\x1b[?25h")  # Show cursor
    self.terminal.write("\x1b[r")      # Reset scroll region
    self.terminal.write("\x1b[2J")     # Clear screen
    self.terminal.write("\x1b[H")      # Home cursor
    self._force_full_redraw = True
    self._previous_lines = []
    # Log recovery
```

---

## Success Criteria

- [ ] Alfred runs for 2+ hours in mosh+tmux without display freezing
- [ ] Input remains responsive throughout session
- [ ] No manual intervention required (auto-recovery works)
- [ ] Visual quality acceptable in safe mode (no major flickering)
- [ ] Plain SSH sessions continue to work normally
- [ ] Performance remains acceptable (< 10% CPU increase in safe mode)

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-06 | Focus on mosh-safe rendering | DEC 2026 and scroll regions likely cause freeze |
| 2026-03-06 | Auto-detect mosh vs explicit flag | User shouldn't need to know implementation details |
| 2026-03-06 | Include watchdog recovery | Even with fixes, mosh may fail; auto-recovery ensures usability |

---

## Related

- Previous (incorrect) PRD: #114 (hardware cursor sync) - closed, cursor was not the issue
- Mosh documentation: https://mosh.org/
- DEC 2026 spec: https://gitlab.com/gnachman/iterm2/-/wikis/synchronized-updates-spec
