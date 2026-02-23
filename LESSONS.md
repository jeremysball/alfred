# Lessons Learned

Critical patterns discovered during development that prevent bugs.

---

## CLI Interface Architecture

### Live Display + Console Scrollback Pattern

**Pattern:** Use Rich Live only for the active input area and streaming content. Print completed messages to console for natural scrolling.

**Why:** Live display maintains a fixed position. If you put scrollback history in Live, it flickers, can't be scrolled, and consumes excessive memory.

**Rich Documentation Confirms:**
> "If you print or log to this console, the output will be displayed **above** the live display."

This means printing to `live.console` automatically places content above the Live display - no stop/start needed.

**Correct Architecture:**
```
┌─────────────────────────────────────┐
│ [Console scrollback - prints]       │  ← live.console.print()
│ User: Hello                         │     Automatically appears above Live
│ Alfred: Hi there!                   │     Scrolls naturally
│ User: How are you?                  │
│ Alfred: I'm doing well!             │
├─────────────────────────────────────┤
│ > [prompt]                          │  ← Rich Live display
│ kimi | in:1.2K out:500 | 💬 5       │     Fixed at bottom
└─────────────────────────────────────┘
```

**Implementation:**
```python
async def _stream_response(self, user_input: str) -> None:
    # ... stream into buffer with Live updates ...

    # Finalize the assistant message
    self.buffer.finalize_message()

    # Print to Live's console - automatically appears ABOVE the live display
    if self._live_display:
        for renderable in self.buffer.render():
            self._live_display.console.print(renderable)

    # Clear buffer - messages are now in console scrollback
    self.buffer.clear()

    # Clear Live display content (keep just prompt + status)
    if self._live_display:
        self._live_display.set_content([])
        self._live_display.update()
```

### When to Use Each Output Method

| Context | Method | Why |
|---------|--------|-----|
| Streaming response | Live display | In-place updates, no flicker |
| Completed messages | `live.console.print()` | Appears above Live, scrollable |
| Commands (/new, /resume) | `live.console.print()` | Appears above Live, scrollable |
| Status line | Live display | Fixed position, always visible |
| Prompt | Live display | Fixed position, always visible |

### Key Insight

**Print to `live.console`, not `self.console`.** The Live display's console automatically positions printed content above the Live area. No need to stop/start Live.

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
