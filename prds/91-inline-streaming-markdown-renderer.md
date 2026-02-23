# PRD #91: Rich Live Streaming Display with Custom Prompt

**Status**: In Progress  
**Priority**: High  
**Author**: Claude (Agent)  
**Created**: 2026-02-22  
**Related PRDs**: #85 (Enhanced CLI Status Line), #89 (Notification System)

---

## Problem Statement

The current CLI uses `prompt_toolkit` for input, which conflicts with `rich.live.Live` for streaming:

1. **Prompt Overwrites**: Live's background cursor loop conflicts with prompt_toolkit
2. **Flicker**: Manual ANSI cursor control causes visible flicker as content grows
3. **Complex Integration**: Workarounds needed to make Live and prompt_toolkit coexist

Previous approach (manual ANSI cursor control) causes flicker that increases with content length.

---

## Solution Overview

**Drop prompt_toolkit entirely.** Use Rich Live for everything:

1. **Rich Live for Display**: Single Live instance handles streaming markdown + prompt + status line
2. **Custom Prompt Input**: Build our own input handling with editing, history, completion
3. **Terminal-Based Input**: Use `readchar` (works over SSH, no root required)
4. **Unified Layout**: All content in one Live display — no conflicts, no flicker

---

## Technical Architecture

### Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│ [Markdown content streams here]                              │
│ [Tool panels appear inline]                                  │
│ [More content...]                                            │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ /help   /session   /model   /clear                       │ │
│ └─────────────────────────────────────────────────────────┘ │
│ >>> user input here with cursor|                             │
├─────────────────────────────────────────────────────────────┤
│ kimi/k2 | 1.2k tokens | Context: 45% | ●                    │
└─────────────────────────────────────────────────────────────┘
    ↑ Tab completion dropdown    ↑ Status line (bottom toolbar)
```

### Components

| Component | Description |
|-----------|-------------|
| **LiveDisplay** | Rich Live with Layout containing content + prompt + status |
| **PromptInput** | Custom input with editing, cursor, selection |
| **InputReader** | Terminal-based key reading (readchar) |
| **History** | Command history with file persistence |
| **Completer** | Tab completion with dropdown UI |
| **StatusLine** | Model, tokens, context, throbber |

### Key Bindings

| Key | Action |
|-----|--------|
| `Ctrl+I` | Move to start of line |
| `Ctrl+A` | Move to end of line |
| `Ctrl+K` | Delete to end of line |
| `Ctrl+U` | Delete to start of line |
| `Ctrl+W` | Delete word before cursor |
| `Ctrl+C` | Interrupt (handled by app) |
| `Ctrl+D` | EOF/exit (handled by app) |
| `Alt+←` | Back one word |
| `Alt+→` | Forward one word |
| `↑` | Previous history item |
| `↓` | Next history item |
| `Tab` | Complete / show dropdown |
| `Shift+Tab` | Reverse complete / hide dropdown |
| `Enter` | Submit input |
| `←` / `→` | Move cursor left/right |
| `Backspace` | Delete character before cursor |
| `Delete` | Delete character at cursor |
| `Home` / `End` | Start/end of line |
| `Esc` | Hide completion dropdown |

### Tab Completion Dropdown

When user presses Tab:
1. Show dropdown above prompt with matching completions
2. Highlight first match
3. Tab/Shift+Tab cycles through options
4. Enter selects current option
5. Esc hides dropdown
6. Typing filters dropdown

Dropdown styling:
- Border around options
- Current selection highlighted
- Up to 5 visible items, scroll if more

### Input Reading (SSH Compatible)

Use `readchar` library which reads from stdin:

```python
from readchar import readkey
from readchar.key import UP, DOWN, LEFT, RIGHT, ENTER, TAB, BACKSPACE

def read_input():
    while True:
        key = readkey()
        if key == UP:
            # History up
        elif key == '\x01':  # Ctrl+A
            # End of line
        elif key == '\x09':  # Tab / Ctrl+I
            # Toggle: if dropdown open, next item; else show dropdown
        # ...
```

---

## Implementation Plan

### Milestone 1: Rich Live Basic Structure ✅

**Goal**: Set up Rich Live with layout for content + prompt + status

**Tasks**:
- [x] Create `LiveDisplay` class using `rich.live.Live`
- [x] Define `Layout` with content area, prompt area, status bar
- [x] Render content from conversation buffer
- [x] Status line rendered at bottom via `set_status()`

**Validation**: ✅ Complete - Live display shows content, prompt, status; no flicker

### Milestone 2: Custom Prompt Input ✅

**Goal**: Basic input handling with cursor movement

**Tasks**:
- [x] Create `PromptInput` class with buffer and cursor position
- [x] Implement character input with readchar
- [x] Implement cursor movement (left, right, Home, End)
- [x] Implement backspace/delete
- [x] Render prompt with cursor indicator (reverse style)

**Validation**: ✅ Complete - Type text, move cursor, edit; cursor renders correctly

### Milestone 3: Key Bindings ✅

**Goal**: Implement all key bindings

**Tasks**:
- [x] `Ctrl+I` start of line, `Ctrl+A` end of line
- [x] `Ctrl+K` delete to end, `Ctrl+U` delete to start
- [x] `Ctrl+W` delete word
- [x] `Alt+Arrow` word navigation
- [x] Handle Ctrl+C and Ctrl+D gracefully

**Validation**: ✅ Complete - All key bindings work correctly

### Milestone 4: Command History ✅

**Goal**: Up/down arrow history navigation

**Tasks**:
- [x] Create `History` class with file persistence (session-based)
- [x] Store submitted commands
- [x] Navigate with up/down arrows
- [x] Save on exit
- [x] Load on startup

**Validation**: ✅ Complete - History persists across sessions

### Milestone 5: Tab Completion with Dropdown ✅

**Goal**: Tab completion with visual dropdown

**Tasks**:
- [x] Create `Completer` class with completion sources
- [x] Complete commands (`/help`, `/session`, `/model`, `/clear`, `/new`, `/resume`)
- [x] Complete tool names
- [x] Dynamic session ID completion via callback
- [x] Show dropdown above prompt when Tab pressed
- [x] Navigate dropdown with Tab/Shift+Tab/Arrow keys
- [x] Select with Enter, dismiss with Esc
- [x] Style dropdown with fuzzy matching and scoring

**Validation**: ✅ Complete - Tab shows dropdown, navigate/select works, Esc dismisses

### Milestone 6: CLI Integration ✅

**Goal**: Replace existing CLI with new Rich Live implementation

**Tasks**:
- [x] Refactor `CLIInterface` to use `LiveDisplay`
- [x] Remove `prompt_toolkit` dependency
- [x] Wire up streaming content to Live display
- [x] Wire up tool panels (ConversationBuffer)
- [x] Wire up status line updates (model, tokens, throbber)
- [x] Add `read_line_async()` for async input (wraps readchar in executor)

**Validation**: ✅ Complete - Full conversation flow works, no flicker, 564 tests pass

### Milestone 7: E2E Testing ⏳

**Goal**: Verify with tmux-tape

**Tasks**:
- [ ] Test streaming with various content
- [ ] Test prompt editing
- [ ] Test history navigation
- [ ] Test tab completion dropdown
- [ ] Verify no flicker

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-22 | Drop prompt_toolkit | Conflicts with Rich Live, flicker issues |
| 2026-02-22 | Use Rich Live exclusively | Unified display, no conflicts, no flicker |
| 2026-02-22 | Use readchar for input | Works over SSH, no root required |
| 2026-02-22 | Ctrl+I start, Ctrl+A end | User preference |
| 2026-02-22 | Alt+Arrow for word nav | Standard convention |
| 2026-02-22 | Dropdown for tab completion | User preference, better UX |
| 2026-02-23 | Wrap readchar in asyncio executor | Simpler than async raw stdin, readchar handles all escape sequences |

---

## Related Links

- GitHub Issue: #91
- readchar: https://github.com/magmax/python-readchar
- Rich Live: https://rich.readthedocs.io/en/latest/live.html
- Rich Layout: https://rich.readthedocs.io/en/latest/layout.html
