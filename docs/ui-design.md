# Alfred CLI UI Design Document

**Created**: 2026-02-22
**PRD**: #87 Session UX Polish
**Purpose**: Visual reference for Alfred CLI UI patterns and behaviors

---

## Overview

Alfred's CLI interface uses **Rich** for rendering and **prompt_toolkit** for input handling. The UI prioritizes:

- **Clarity**: Distinct visual separation between user and assistant messages
- **Responsiveness**: Streaming output with live updates
- **Context visibility**: Status line showing model, tokens, and session state

### Technology Stack

| Component | Library | Purpose |
|-----------|---------|---------|
| Layout | Rich Console | Terminal rendering |
| Panels | Rich Panel | Message containers with borders |
| Markdown | Rich Markdown | Formatting assistant responses |
| Input | prompt_toolkit | Prompt with completion, keybindings |
| Live updates | Rich Live | Streaming content |
| Status | prompt_toolkit bottom_toolbar | Token/context display |

---

## Screenshots

### 1. Startup State

The initial view when Alfred launches:

- Banner panel with title and keybindings
- Empty prompt (`>>> `)
- Status line at bottom showing model and context

```
╭──────────────────────────────────────────────────────────────────────────────────────╮
│                                      Alfred - Your Persistent Memory Assistant       │
╰────────────────────── exit to quit | compact for memory | Ctrl-T toggle tools ───────╯
>>>
> kimi/kimi-k2-5 | in:0 out:0 cache:0 reason:0 | ctx:0  📚 0 | 💬 0 | 📋 AGENTS,SOUL,USER,...
```

### 2. Conversation State

Messages displayed as colored panels:

- **User messages**: Slate blue border (`color(23)`)
- **Assistant messages**: Dark teal border (`color(24)`)
- **Tool calls**: Dim blue (success) or red (error) borders

```
╭─ You ────────────────────────────────────────────────────────────────────────────────╮
│ What can you help me with today?                                                      │
╰───────────────────────────────────────────────────────────────────────────────────────╯
╭─ Alfred ──────────────────────────────────────────────────────────────────────────────╮
│ I can help you with many things!                                                      │
│                                                                                       │
│ - **Remember information** for future conversations                                   │
│ - **Search your memories** to recall past discussions                                 │
│ - **Schedule reminders** using the cron system                                        │
│ - **Run shell commands** to interact with your system                                 │
│                                                                                       │
│ What would you like to do?                                                            │
╰───────────────────────────────────────────────────────────────────────────────────────╯
```

### 3. Streaming State

During LLM response generation:

- Status line hides (prompt_toolkit behavior)
- Throbber animates in bottom-right corner
- Content streams into assistant panel

```
>>> tell me a joke

╭─ Alfred ──────────────────────────────────────────────────────────────────────────────╮
│ Why do programmers prefer dark mode?                                                   │
│                                                                                       │
│ Because light attracts bugs! 🐛                                                       │
╰───────────────────────────────────────────────────────────────────────────────────────╯

                                                   ⠋ Working...
```

**Throbber**: Uses `dots` spinner frames (`⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏`) at 80ms interval.

### 4. Tool Execution

Tool calls appear as panels between conversation turns:

```
╭─ Tool: read ─────────────────────────────────────────────────────────────────────────╮
│ {                                                                                     │
│   "content": "file contents here...",                                                 │
│   "path": "/path/to/file.txt"                                                        │
│ }                                                                                     │
╰───────────────────────────────────────────────────────────────────────────────────────╯
```

- **Success**: Dim blue border
- **Error**: Red border
- **Truncation**: Long results truncated with "... (N more lines)" indicator

### 5. Session Commands

#### /new - Create New Session

```
>>> /new
╭─────────────────────────────────────────────── New Session Created ──────────────────╮
│ Session ID: sess_a8f2370e0eaf                                                         │
╰───────────────────────────────────────────────────────────────────────────────────────╯
```

#### /sessions - List Sessions

```
>>> /sessions
                                Sessions
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ ID                  ┃ Created          ┃ Last Active      ┃ Messages ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ sess_a8f2370e0eaf * │ 2026-02-22 20:46 │ 2026-02-22 20:46 │        0 │
│ sess_e74ff24bc129   │ 2026-02-22 15:41 │ 2026-02-22 15:41 │        0 │
└─────────────────────┴──────────────────┴──────────────────┴──────────┘
```

#### Command Completion

Tab completion shows available commands:

```
>>> /
      /new
      /resume
      /sessions
      /session
```

### 6. Status Line

Bottom toolbar showing context:

```
> kimi/kimi-k2-5 | in:4.0K out:36 cache:0 reason:0 | ctx:2.9K  📚 1 | 💬 40 | 📋 AGENTS,SOUL,USER,...
```

| Field | Description |
|-------|-------------|
| `>` | Activity indicator (streaming: animated spinner) |
| `kimi/kimi-k2-5` | Current model name |
| `in:X` | Input tokens consumed |
| `out:X` | Output tokens generated |
| `cache:X` | Cache read tokens (if any) |
| `reason:X` | Reasoning tokens (if any) |
| `ctx:X` | Estimated context size |
| `📚 N` | Memories in context |
| `💬 N` | Session messages |
| `📋 ...` | Prompt sections loaded |

---

## UI Components

### Message Panels

All conversation messages use Rich `Panel` with consistent styling:

```python
# User message
Panel(
    content,
    title="You",
    title_align="left",
    border_style="color(23)",  # Dark slate blue
    padding=(0, 1),
)

# Assistant message
Panel(
    Markdown(content),
    title="Alfred",
    title_align="left",
    border_style="color(24)",  # Dark teal
    padding=(0, 1),
)
```

### Status Line

Implemented via `prompt_toolkit` `bottom_toolbar`:

```python
def _bottom_toolbar(self) -> Any:
    status_data = self._get_status_data()
    renderer = StatusRenderer(status_data)
    return renderer.to_prompt_toolkit()
```

### Throbber

Right-aligned animated spinner during streaming:

```python
def _render_throbber(self) -> Text:
    frame = self._throbber.advance()
    width = self.console.width
    text = f"{frame} Working..."
    padding = width - len(text) - 1
    return Text(" " * max(0, padding) + text, style="cyan bold")
```

---

## Interactions

### Keybindings

| Key | Action |
|-----|--------|
| `Ctrl-T` | Toggle tool panel visibility |
| `Tab` | Complete commands/session IDs |
| `Enter` | Submit message |
| `Ctrl-C` | Interrupt/exit |

### Commands

| Command | Description |
|---------|-------------|
| `/new` | Create new session |
| `/resume <id>` | Resume existing session |
| `/sessions` | List all sessions |
| `/session` | Show current session info |
| `exit` | Quit Alfred |
| `compact` | Compact context |

---

## Future Improvements

Identified during PRD #87 implementation:

1. **Shift+Enter queue message** - Allow queuing messages while LLM is running
2. **ESC cancel streaming** - Interrupt current LLM call
3. **Background color on panels** - Full background styling (Rich limitation)
4. **Session ID short form** - Allow partial ID matching for `/resume`

---

## References

- PRD #53: Session System
- PRD #81: Enhanced CLI Status Line
- PRD #87: Session UX Polish
- [Rich Documentation](https://rich.readthedocs.io/)
- [prompt_toolkit Documentation](https://python-prompt-toolkit.readthedocs.io/)
