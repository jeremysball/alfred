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
