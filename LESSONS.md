# Lessons Learned

Critical patterns discovered during development that prevent bugs.

---

## CLI Interface Architecture

### Live Display Pattern for Chat Interfaces

**Pattern:** Rich Live with fixed-size Layout for prompt+status at bottom. Content prints to `live.console` which automatically appears above the Live display.

**Architecture:**
```
┌─────────────────────────────────────┐
│ [Console scrollback]                │  ← live.console.print()
│ User: Hello                         │     Appears above Live
│ Alfred: Hi there!                   │     Scrolls naturally
├─────────────────────────────────────┤
│ > [prompt]                          │  ← Rich Live with Layout
│ kimi | in:1.2K out:500 | 💬 5       │     Fixed 2-line bottom (size=2)
└─────────────────────────────────────┘
```

**Implementation:**

1. **Layout with fixed-size bottom region:**
```python
self._layout = Layout()
self._layout.split_column(
    Layout(name="spacer", size=0),  # Takes no space
    Layout(name="prompt", size=2),  # Fixed 2 lines for prompt+status
)
```

2. **Live runs continuously, status updates during streaming:**
```python
async for chunk in self.alfred.chat_stream(user_input):
    self.buffer.add_text(chunk)
    # Print chunk to live.console (appears above Live)
    self._live_display.console.print(chunk, end="")
    # Update status line (shows throbber)
    self._live_display.set_status(self._render_status_line())
    self._live_display.update()
```

3. **Final message prints formatted:**
```python
self.buffer.finalize_message()
for renderable in self.buffer.render():
    self._live_display.console.print(renderable)
self.buffer.clear()
```

### Key Insights

1. **Layout with size=2 for prompt** - Keeps prompt anchored at bottom
2. **Live runs continuously** - Throbber/status updates during streaming
3. **`live.console.print()` appears above Live** - Per Rich docs
4. **No transient, no stop/start** - Just continuous Live with content above

---

## Session Management

### Token Restoration

When resuming a session, restore token counts from history to show accurate status:

```python
msg_count = self.alfred.restore_session_tokens()
```

This estimates:
- `input_tokens` from user messages
- `output_tokens` from assistant messages
- `context_tokens` including base prompt overhead (~15K chars)

---

## Status Line Updates

Always update status BEFORE entering the LiveDisplay context so the first render is correct:

```python
self._live_display.set_status(self._render_status_line())

with self._live_display:
    # ... main loop ...
```

After commands that change state, update both content AND status:

```python
self._live_display.set_content(self.buffer.render())
self._live_display.set_status(self._render_status_line())
self._live_display.update()
```
