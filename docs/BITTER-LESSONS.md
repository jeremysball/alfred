# Bitter Lessons

Hard-won debugging experiences worth remembering.

---

## The Scrollback Explosion (2026-02-27)

### Symptom

At narrow terminal widths (53 cols), sending a message caused scrollback to explode to 4000+ lines after a single response.

### Root Cause

pypitui's `_handle_content_growth()` emitted newlines for **ALL scrollback lines on every frame**, not just new ones.

### The Fix

Track what's already been emitted:

```python
self._emitted_scrollback_lines = 0

# Only emit NEW scrollback lines
for i in range(self._emitted_scrollback_lines, first_visible):
    buffer += "\r\n"
self._emitted_scrollback_lines = first_visible
```

### Lesson

**Cumulative emissions corrupt invisible state.** See [TUI-RENDERING-PITFALLS.md](./TUI-RENDERING-PITFALLS.md) for the full pattern catalog.

---

## Session Resume Scrollback (2026-03-04)

### Symptom

When resuming a session with 32 messages, scrollback was empty - only the last screenful was visible. Users couldn't scroll up to see older messages.

### Root Cause

With **absolute positioning**, content is rendered to specific screen coordinates. Lines 0-300 render to rows 1-300 (mostly off-screen), but they never flow into the terminal's scrollback buffer because nothing "scrolled off" the top.

### The Fix

**Bulk scrollback population**: Render historical content in screen-sized chunks, then use SU (Scroll Up) to push each chunk into scrollback:

```python
def _populate_scrollback_on_resume(self, lines_in_scrollback: int):
    # Render in chunks and scroll into history
    for chunk in chunks(scrollback_content, scrollable_height):
        for i, line in enumerate(chunk):
            buffer += f"\x1b[{i+1};1H\x1b[2K{line}"
        buffer += f"\x1b[{len(chunk)}S"  # Scroll up into scrollback
```

Then tell pypitui the content is handled:
```python
self.tui.set_scrollback_position(lines_in_scrollback)
```

### Key Insight

**Absolute positioning alone doesn't populate scrollback.** To get content into scrollback:
- **Normal operation**: Content grows incrementally, terminal naturally scrolls
- **Resume/startup**: Must manually render and SU to populate scrollback, then use absolute positioning for visible content

### Lesson

**Scrollback requires actual scrolling.** Absolute positioning is great for live updates, but historical content needs to be "scrolled through" to enter the terminal's history buffer.
