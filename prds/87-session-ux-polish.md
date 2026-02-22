# PRD: Session UX Polish

**Issue**: #87
**Status**: Open
**Priority**: High
**Created**: 2026-02-22
**Updated**: 2026-02-22
**Related**: #53 (Session System), #81 (Enhanced CLI Status Line)

---

## Problem Statement

Several UX issues degrade the CLI session experience:

1. **Job notifications clobber the prompt** - Cron job output prints next to the active input line while user is typing
2. **Resumed session history looks unnatural** - Should display as seamless conversation blocks, not distinguishable from new messages
3. **Status line doesn't update on `/new`** - Creating a new session leaves the status line stale
4. **No command completion** - Users must remember `/new`, `/resume`, `/sessions` commands exactly
5. **Throbber regression** - The activity throbber from PRD #81 is no longer visible in the bottom-right corner during streaming

---

## Solution Overview

### 1. Job Notification Handling

Suppress job notifications during active LLM response or user input. Queue them and display after response completes in a dedicated notification area (not mixed with chat messages).

**Implementation:**
- Track "active input" state in CLI
- Buffer job notifications while active
- Flush buffer after LLM response completes
- Display with visual separator (e.g., `── Jobs ──`)

### 2. Session History as Message Blocks

Render conversation history with background colors for visual block effect:

- **User messages**: Dark slate blue (`#1e3a5f` or Rich color)
- **Assistant messages**: Dark teal (`#1a3d3d` or Rich color)
- Full history displayed on `/resume` (no truncation)
- No visual distinction between resumed and new messages (seamless)

**Implementation:**
- Use Rich `Panel` or custom `padding` + `bg` styling
- Apply to both loaded history and new messages
- Consistent width, left-aligned text

### 3. Status Line Refresh on `/new`

Trigger status line re-render after session creation.

**Implementation:**
- Call status renderer after `session_manager.start_session()`
- Update session count and current session display

### 4. Promptkit Command Completion

Add autocomplete for `/` commands using promptkit's completion system.

**Commands to complete:**
- `/new` - Create new session
- `/resume <id>` - Resume session (show IDs)
- `/sessions` - List sessions
- `/session` - Show current session

**Implementation:**
- Use `prompt_toolkit.completion.WordCompleter` or custom completer
- Dynamic ID completion for `/resume` (load from session list)

### 5. Throbber in Bottom-Right Corner (Regression Fix)

The status line from PRD #81 disappears during streaming (desired behavior). However, a throbber should appear in the bottom-right corner to indicate activity.

**Current behavior:**
- Status line hides during streaming ✅ (desired)
- Small square appears in bottom-right during streaming (artifact, not intentional)
- No animated throbber visible

**Desired behavior:**
- Status line hides during streaming ✅
- Animated throbber (dots spinner: `⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏`) appears in bottom-right corner
- Throbber animates at 80ms interval (same as PRD #81)
- Throbber disappears when streaming completes

**Implementation:**
- Use Rich `Live` with a bottom-right overlay or separate renderable
- Reuse `SPINNER_FRAMES` from `status.py` for consistency
- Position in bottom-right using Rich layout or ANSI escape codes

**Research note**: The `dots` spinner (`⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏`) is the best choice for terminal throbbers:
- Fast 80ms interval for smooth animation
- Braille dots work in all terminals
- Already established pattern from PRD #81
- More elegant than ASCII alternatives (`-\|/`) Requires a Nerd Font to be installed in the terminal.

### 6. UI Documentation with tmux-tape

Create a visual design document capturing the current CLI UI state using the tmux-tape skill for screenshots.

**Purpose:**
- Document current UI patterns and behaviors
- Create reference screenshots for future development
- Identify UX inconsistencies or issues
- Provide visual baseline for regression testing

**Implementation:**
- Use tmux-tape skill to capture CLI in various states:
  - Idle state (prompt visible, status line shown)
  - Streaming state (throbber active, content scrolling)
  - Tool execution (tool panels visible)
  - Session commands (`/sessions`, `/resume`, etc.)
- Write design document analyzing current UI
- Identify areas for improvement

---

## Technical Architecture

### Message Block Rendering

```python
from rich.console import Console
from rich.text import Text

USER_BG = "color(23)"      # Dark slate blue
ASSISTANT_BG = "color(24)" # Dark teal

def render_message(role: str, content: str) -> Text:
    bg = USER_BG if role == "user" else ASSISTANT_BG
    return Text(content, style=f"on {bg}")
```

### Job Notification Buffer

```python
class CLINotificationBuffer:
    def __init__(self):
        self._buffer: list[str] = []
        self._active = False

    def buffer(self, message: str) -> None:
        if self._active:
            self._buffer.append(message)
        else:
            self._display(message)

    def flush(self) -> None:
        if self._buffer:
            # Display with separator
            for msg in self._buffer:
                self._display(msg)
            self._buffer.clear()
```

### Command Completion

```python
from prompt_toolkit.completion import WordCompleter, Completer, Completion

class SessionCommandCompleter(Completer):
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if text.startswith("/"):
            # Match commands
            commands = ["/new", "/resume", "/sessions", "/session"]
            for cmd in commands:
                if cmd.startswith(text):
                    yield Completion(cmd, start_position=-len(text))
```

### Throbber Rendering

```python
from rich.spinner import SPINNERS
from rich.text import Text

# Reuse dots spinner from PRD #81
SPINNER_FRAMES = SPINNERS["dots"]["frames"]  # "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
SPINNER_INTERVAL = 80  # ms

def render_throbber(frame: str) -> Text:
    """Render throbber for bottom-right corner."""
    return Text(frame, style="cyan bold")
```

---

## Milestone Roadmap

| # | Milestone | Description | Status |
|---|-----------|-------------|--------|
| 1 | **Job Notification Buffer** | Suppress during active input, display after | ✅ Done |
| 2 | **Message Block Styling** | Background colors for user/assistant | ✅ Done |
| 3 | **Status Line Refresh** | Update on `/new` | 🔲 Todo |
| 4 | **Command Completion** | Autocomplete for `/` commands | 🔲 Todo |
| 5 | **Throbber Fix** | Add animated throbber to bottom-right during streaming | ✅ Done |
| 6 | **UI Documentation** | Capture and document current UI with tmux-tape screenshots | 🔲 Todo |

---

## File Changes

| File | Change |
|------|--------|
| `src/interfaces/cli.py` | Notification buffer, throbber, message styling, status refresh, completions |
| `src/interfaces/notification_buffer.py` | New file: Notification buffer for queuing during active states |
| `src/cron/notifier.py` | Add buffer support to CLINotifier |
| `src/alfred.py` | Expose notifier for buffer configuration |
| `src/interfaces/status.py` | May need refresh trigger |
| `docs/ui-design.md` | New file: Visual UI documentation with screenshots |

---

## Success Criteria

- [x] Job notifications never appear next to active prompt
- [x] Resumed session displays as natural conversation blocks
- [x] User and assistant messages have distinct background colors
- [ ] `/new` immediately updates status line
- [ ] Tab completes `/new`, `/resume`, `/sessions`, `/session`
- [x] Animated throbber visible in bottom-right during streaming
- [ ] UI design document created with tmux-tape screenshots

---

## Dependencies

- `prompt_toolkit` (already installed)
- Rich (already installed)
- Existing session system (PRD #53)
- tmux-tape skill (for M6)

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-22 | Use `dots` spinner for throbber | Consistent with PRD #81, smooth 80ms animation, works in all terminals |
| 2026-02-22 | Throbber in bottom-right corner | Status line hides during streaming (desired), throbber provides activity feedback |
| 2026-02-22 | Rename workflow milestone removed | Already completed |
| 2026-02-22 | NotificationBuffer with callback | Callback pattern allows CLIInterface to control active state without tight coupling |
| 2026-02-22 | Panel-based message styling | Rich Panel with colored borders instead of text background; matches tool call styling for visual consistency |
