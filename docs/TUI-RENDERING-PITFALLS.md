# TUI Rendering Pitfalls

Patterns of bugs that keep recurring in the pypitui-based TUI. Read this before making rendering changes.

---

## The Core Problem

Terminal UIs have **invisible state** that's easy to corrupt:
- Cursor position (where am I?)
- Scrollback buffer (what's above the visible area?)
- Line width (ANSI codes don't count, but visible chars do)
- Render cache (what did I draw last frame?)

When these get out of sync, you get:
- Extra blank lines flooding scrollback
- Content appearing in wrong position
- Borders breaking on narrow terminals
- Flickering or ghost content

---

## Pitfall #1: Cumulative Emissions

**Bug:** Emitting the same content multiple times across frames.

**Example (scrollback explosion):**
```python
# BUGGY - emits ALL scrollback lines every frame
for i in range(first_visible):  # first_visible = 76, then 79, then 82...
    buffer += lines[i] + "\n"   # Re-emits lines 0-75 every single frame!
```

**Fix:** Track what's already been emitted:
```python
# CORRECT - only emit NEW lines
for i in range(self._emitted_count, first_visible):
    buffer += lines[i] + "\n"
self._emitted_count = first_visible
```

**Symptoms:**
- Scrollback grows exponentially (4k+ lines after one message)
- Lots of blank lines in terminal history
- Gets worse with more content or narrower terminals

**Commits:** scrollback explosion fix (2026-02-27)

---

## Pitfall #2: Width Calculation with ANSI Codes

**Bug:** Counting ANSI escape codes as visible characters.

**Example:**
```python
# BUGGY - cursor char adds 1 visible char
line = f"{text}\x1b[7m█\x1b[27m"  # If text is 53 chars, line is now 54!
```

**Fix:** Use styling that doesn't add visible width:
```python
# CORRECT - reverse video doesn't add width
line = f"{before}\x1b[7m{char}\x1b[27m{after}"  # Stays 53 chars
```

**Symptoms:**
- Lines wrap unexpectedly on narrow terminals
- Borders misaligned by 1-2 characters
- Works at 80 cols, breaks at 53 cols

**Commits:** 8bf147f (cursor char), 1339c81 (border wrapping)

---

## Pitfall #3: Word-Wrapping Breaking Layout

**Bug:** Content contains spaces that the text wrapper splits on.

**Example:**
```python
# BUGGY - wrapper splits on spaces, breaking the format
line = "session-123  2026-02-27 14:30  5 msgs"
# Becomes:
# session-123
# 2026-02-27 14:30  5 msgs
```

**Fix:** Use non-breaking spaces where wrapping shouldn't occur:
```python
# CORRECT - NBSP prevents word wrap
line = "session-123\xa0\xa02026-02-27\xa0\xa05 msgs"
```

**Symptoms:**
- Formatted output splits across lines
- Tables/headers become unreadable
- Works with short content, breaks with longer content

**Commits:** 75cd3e0 (/sessions), 1339c81 (tool boxes)

---

## Pitfall #4: Extra Padding Adding Blank Lines

**Bug:** Components have default padding that adds unwanted blank lines.

**Example:**
```python
# BUGGY - Text defaults to padding_y=1, adding blank lines
self.add_child(Text(content))  # Blank line above and below!
```

**Fix:** Explicitly set padding to zero:
```python
# CORRECT - no extra padding
self.add_child(Text(content, padding_y=0))
```

**Symptoms:**
- Extra blank lines between content
- Scrollback pollution from commands
- Vertical spacing looks wrong

**Commits:** 09a3cff (reverted), 125ecea (revert), final fix embedded in later commits

---

## Pitfall #5: Frame-to-Frame State Corruption

**Bug:** Not tracking what changed between frames, causing re-render issues.

**Example:**
```python
# BUGGY - clear() preserves _previous_lines, defeating diff rendering
self.conversation.clear()
self.conversation.add_child(new_content)
# Now _previous_lines doesn't match, causes ghost content
```

**Fix:** Use force redraw when structure changes:
```python
# CORRECT - force full redraw after clear
self.conversation.clear()
self.conversation.add_child(new_content)
self.tui.request_render(force=True)
```

**Symptoms:**
- Ghost content from previous screens
- Flickering on screen transitions
- Differential rendering breaks

**Commits:** eb01dde (flickering fix)

---

## Testing Checklist

Before merging TUI changes, test at:

- [ ] **53 columns** - narrow terminal stress test
- [ ] **80 columns** - standard terminal
- [ ] **120 columns** - wide terminal
- [ ] **24 lines height** - triggers scrollback
- [ ] **Long content** - exceeds terminal height
- [ ] **Streaming content** - multiple render frames
- [ ] **Screen transitions** - clear and redraw

---

## Debug Techniques

1. **Count newlines** - if output has 1000+ lines after one message, cumulative emission bug
2. **Check visible width** - `visible_width(line)` should equal terminal width
3. **Trace render calls** - log what's being emitted each frame
4. **Test narrow first** - bugs appear sooner at 53 cols than 80 cols
5. **Check pypitui source** - the bug might be upstream

---

## Pitfall #6: Scrollback Doesn't Populate With Absolute Positioning

**Bug:** Using only absolute positioning on resume leaves scrollback empty.

**Example:**
```python
# BUGGY - renders all content to screen coordinates, scrollback stays empty
for i, line in enumerate(all_322_lines):
    buffer += f"\x1b[{i+1};1H{line}"  # Lines 0-300 render off-screen
# User sees last 24 lines, but Shift+PgUp shows nothing
```

**Fix:** Populate scrollback first with SU, then render visible content:
```python
# CORRECT - populate scrollback in chunks
scrollback_lines = total_lines - scrollable_height

for chunk in chunks(content[:scrollback_lines], scrollable_height):
    for i, line in enumerate(chunk):
        buffer += f"\x1b[{i+1};1H\x1b[2K{line}"
    buffer += f"\x1b[{len(chunk)}S"  # Push into scrollback

# Tell TUI content is in scrollback
tui.set_scrollback_position(scrollback_lines)

# Normal render for visible portion
tui.request_render()
```

**Key Insight:** Absolute positioning renders to screen coordinates. Line 200 goes to row 200 (off-screen), but it never enters the terminal's scrollback buffer because the terminal didn't "scroll" it off. You need SU (Scroll Up) to actually push content into scrollback history.

**Symptoms:**
- Resume session with 100+ messages
- Only last screenful visible
- Shift+PgUp shows empty or unrelated content
- Normal conversation (growing incrementally) works fine

**When This Happens:**
- Session resume with many messages
- Loading large chat history
- Switching to a conversation with lots of context

**Not About Cursor Movement:** This is NOT about absolute vs relative cursor positioning. Both work fine. The issue is that absolute positioning doesn't trigger terminal scrollback - you need actual scroll operations (SU) to populate it.

---

## Pitfall #7: DECSTBM Protects Static UI From Scrollback

**Bug:** Static components (status bar, input) get pushed into scrollback during scroll operations.

**Example:**
```python
# BUGGY - scrolling pushes status bar into scrollback
buffer += "\x1b[300S"  # Scroll up 300 lines
# Status bar scrolled off screen into history!
```

**Fix:** Set scroll region with DECSTBM:
```python
# CORRECT - protect static components at bottom
scrollable_height = term_height - static_height
buffer += f"\x1b[1;{scrollable_height}r"  # Only scroll top N lines
buffer += "\x1b[300S"  # Scroll only affects rows 1-N
buffer += "\x1b[r"  # Reset when done
```

**Mark components as static:**
```python
class StatusLine(Component):
    @property
    def is_static(self) -> bool:
        return True  # Fixed at bottom, don't scroll
```

**Symptoms:**
- Status bar disappears during heavy scrolling
- Input field pushed into scrollback
- UI elements "float" up during session resume

---

## The Meta-Lesson

Terminal rendering is **stateful** but the state is **invisible**. Every time you emit output, you're modifying hidden terminal state (cursor position, scrollback, etc.). Always ask:

1. What state am I modifying?
2. Did I already modify it in a previous frame?
3. Will this work at 53 columns?
4. **Is scrollback being populated correctly?**

When in doubt, **track what you've already done** and **only emit new content**.
