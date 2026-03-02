# PRD #97: Command Completion System for TUI

## Overview

Add tab-triggered command completion with a dropdown menu that renders above the input line. The system uses composition to attach completion behavior to any input component without inheritance.

---

## Problem Statement

Users must type complete commands like `/resume abc123` without any assistance. There is no discovery mechanism for:
- Available slash commands (`/new`, `/resume`, `/sessions`)
- Session IDs for the `/resume` command
- Future command arguments (file paths, memory IDs, etc.)

This creates friction and requires users to remember exact command syntax.

---

## Solution

A composable completion system that:
1. Attaches to any input component via `with_completion()` fluent API
2. Activates when input matches a trigger prefix (default: `/`)
3. Calls a registered provider function on every keystroke
4. Renders a dropdown menu **above** the input line
5. Supports fuzzy filtering (provider returns options based on current text)
6. Accepts selection via **Tab** or **Enter**
7. Navigates with **Up/Down** arrows
8. Closes with **Esc** or when trigger prefix is deleted

---

## User Experience

### Flow

```
1. User types "/"
   → Menu appears above input showing all commands
   
2. User types "r"
   → Menu filters to show "/resume", "/reset" (fuzzy match)
   
3. User presses Tab or Enter
   → "/resume " inserted (with trailing space)
   → Provider called with "/resume "
   → Menu updates to show session IDs
   
4. User types "abc" or navigates with arrows
   → Session list filters/narrows
   
5. User accepts completion
   → Full command inserted, menu closes
```

### Visual Design

```
┌─────────────────────────────────────┐
│ /resume  Resume previous session    │  ← Menu (renders upward)
│ /reset   Reset conversation         │
│ /restart Restart with new context   │
├─────────────────────────────────────┤
│ /res█                               │  ← Input line
└─────────────────────────────────────┘
```

**Menu styling:**
- Border: dim single line (`┌─┐│`)
- Selected item: reverse video highlight
- Description: dim text right-aligned
- Width: max(input width, longest option + description)
- Height: min(len(options), max_height param)

---

## API Design

### Composition API

```python
# Usage - attach completion to any input
input_field = WrappedInput(placeholder="Message Alfred...")
input_field.with_completion(
    provider=command_provider,
    trigger="/",
    max_height=5,
)
```

### CompletionAddon Component

```python
class CompletionAddon:
    """Composable completion behavior that wraps any input component."""
    
    def __init__(
        self,
        input_component: WrappedInput,
        provider: Callable[[str], list[tuple[str, str | None]]],
        trigger: str = "/",
        max_height: int = 5,
    ) -> None:
        """Attach completion behavior to input component.
        
        Args:
            input_component: The input to attach completion to
            provider: Function called on every keystroke while trigger matches.
                     Takes current input text, returns list of (value, description).
                     Return empty list to hide menu.
            trigger: Prefix that activates completion mode.
            max_height: Maximum menu height (renders upward from input).
        """
```

### WrappedInput Hook Support

```python
class WrappedInput:
    """Base input with hook support for composable behaviors."""
    
    def add_input_filter(self, filter_fn: Callable[[str], bool]) -> None:
        """Register a key filter. If filter returns True, key is consumed."""
    
    def add_render_filter(self, filter_fn: Callable[[list[str], int], list[str]]) -> None:
        """Register a render filter that can modify output lines."""
    
    def with_completion(self, **kwargs: Any) -> "WrappedInput":
        """Fluent API to attach completion behavior. Returns self for chaining."""
```

### Provider Example

```python
def command_provider(text: str) -> list[tuple[str, str | None]]:
    """Provide completions for / commands."""
    # Command listing
    commands = [
        ("/new", "Start a new session"),
        ("/resume", "Resume a previous session"),
        ("/sessions", "List all sessions"),
        ("/session", "Show current session info"),
        ("/help", "Show available commands"),
    ]
    
    # Session ID completion after "/resume "
    if text.startswith("/resume "):
        prefix = text[8:]  # After "/resume "
        sessions = get_session_ids()  # [("abc123", "2024-03-01"), ...]
        return [
            (sid, f"Session from {date}")
            for sid, date in sessions
            if sid.startswith(prefix) or fuzzy_match(prefix, sid)
        ]
    
    # Fuzzy filter commands
    return [
        (cmd, desc) for cmd, desc in commands
        if fuzzy_match(text.lower(), cmd.lower())
    ]

# Wire into TUI
input_field = WrappedInput(placeholder="Message Alfred...")
input_field.with_completion(
    provider=command_provider,
    trigger="/"
)
```

---

## Key Behaviors

### Menu Open/Close

| Event | Action |
|-------|--------|
| Text starts with `trigger` | Open menu, call provider |
| Provider returns empty list | Hide menu (keep typing) |
| Text no longer starts with `trigger` | Close menu |
| `Esc` pressed | Close menu, keep text |
| Completion accepted | Close menu, insert value |

### Navigation (while menu open)

| Key | Action |
|-----|--------|
| `Tab` | Accept selected (or first) completion |
| `Enter` | Accept selected (or first) completion |
| `Up` | Move selection up (don't move text cursor) |
| `Down` | Move selection down (don't move text cursor) |
| `→` | Accept one ghost character |
| `←` | Reject one ghost character |
| `Esc` | Close menu without accepting |
| Any other key | Pass to input, re-filter menu |

### Ghost Text (Inline Preview)

When a completion is selected, ghost text appears inline showing the remaining characters:

```
Typed: /          Shows: /n̲ew  ('n' has cursor, 'ew' dimmed)
Typed: /n         Shows: /n e̲w  ('n' accepted, 'e' has cursor)
Typed: /ne        Shows: /ne w̲ ('ne' accepted, 'w' has cursor)
```

**Ghost text styling:**
- First ghost character: reverse video (cursor position)
- Remaining characters: dim (BRIGHT_BLACK)
- Updates dynamically as characters accepted/rejected

**Bidirectional flow:**
- `→` moves cursor forward, accepting characters into input
- `←` moves cursor backward, returning characters to ghost text
- Once back to trigger (`/`), `←` passes through to normal cursor movement

### Fuzzy Matching

```python
def fuzzy_match(query: str, target: str) -> bool:
    """Check if query matches target as subsequence (case-insensitive)."""
    query_lower = query.lower()
    target_lower = target.lower()
    
    qi = 0
    for char in target_lower:
        if qi < len(query_lower) and char == query_lower[qi]:
            qi += 1
    
    return qi == len(query_lower)

# Examples:
fuzzy_match("/r", "/resume")    # True
fuzzy_match("res", "/resume")   # True  
fuzzy_match("/rs", "/resume")   # True (subsequence)
fuzzy_match("xyz", "/resume")   # False
```

---

## Integration Points

### AlfredTUI Changes

```python
class AlfredTUI:
    def __init__(self, ...):
        # Use WrappedInput with completion attached
        self.input_field = WrappedInput(placeholder="Message Alfred...")
        self.input_field.with_completion(
            provider=self._completion_provider,
            trigger="/"
        )
    
    def _completion_provider(self, text: str) -> list[tuple[str, str | None]]:
        """Provide completions based on current input."""
        # Delegate to SessionManager for session IDs
        # Return command list for bare "/"
        pass
```

### SessionManager Integration

```python
class SessionManager:
    def get_completion_options(self, prefix: str) -> list[tuple[str, str]]:
        """Return session IDs matching prefix for completion."""
        # Return [(session_id, formatted_date), ...]
        pass
```

---

## Architecture Decision: Composition Over Inheritance

**Decision**: Use composition (`CompletionAddon`) instead of inheritance (`CompletingInput extends WrappedInput`)

**Date**: 2026-03-01

**Rationale**:
- Completion is optional behavior - not all inputs need it
- Composition keeps `WrappedInput` simple and focused
- Multiple behaviors can be chained: `input.with_completion(...).with_history(...)`
- Easier to test components in isolation
- Follows principle: favor composition over inheritance

**Implementation**:
- `CompletionAddon` hooks into `WrappedInput` via `add_input_filter()` and `add_render_filter()`
- Input filters intercept keys when menu is active
- Render filters prepend menu lines to input render output
- `with_completion()` provides fluent API for easy attachment

---

## Milestones

### Milestone 1: Core CompletionMenu Component ✅
**Deliverable:** `CompletionMenu` class that renders above input
- [x] Renders upward from specified position
- [x] Handles selection state (up/down navigation)
- [x] Renders with box-drawing characters
- [x] Supports descriptions (dim, right-aligned)
- [x] Limited height with scroll indicator if overflow

**Validation:** Unit tests verify rendering at various sizes

### Milestone 2: CompletionAddon Integration ✅
**Deliverable:** `CompletionAddon` composable behavior
- [x] `WrappedInput` supports `add_input_filter()` and `add_render_filter()` hooks
- [x] `CompletionAddon` attaches to input via hooks
- [x] Intercepts Tab/Enter/Up/Down/Esc when menu open
- [x] Calls provider on every keystroke matching trigger
- [x] `with_completion()` fluent API on WrappedInput

**Validation:** Tests verify provider called, menu shows/hides, keys intercepted

### Milestone 3: Fuzzy Matching & Filtering ✅
**Deliverable:** Fuzzy matching algorithm integrated
- [x] `fuzzy_match()` utility function
- [x] Provider results filtered by fuzzy match score
- [x] Results sorted by match quality (exact prefix > subsequence)
- [ ] Visual highlight of matched characters (optional stretch - deferred)

**Validation:** Tests verify fuzzy matching behavior

### Milestone 4: AlfredTUI Integration ✅
**Deliverable:** Command completion works in Alfred TUI
- [x] `WrappedInput.with_completion()` used in `AlfredTUI`
- [x] Provider implementation for `/` commands
- [x] Provider implementation for `/resume ` session IDs
- [x] Session IDs fetched from `SessionManager`

**Validation:** Manual test - type `/`, see commands; type `/resume `, see sessions

### Milestone 5: Edge Cases & Polish ✅
**Deliverable:** Production-ready completion system
- [x] Menu closes when terminal resized
- [x] Menu handles rapid typing (debounce if needed)
- [x] Provider errors don't crash UI (catch and log)
- [x] Empty provider result shows "No matches" message
- [x] Menu width adapts to content and terminal size

**Validation:** All tests pass, manual stress testing

### Milestone 6: Ghost Text (Inline Preview) ✅
**Deliverable:** Inline preview of selected completion with bidirectional navigation
- [x] Ghost text renders after typed text with cursor on first ghost character
- [x] First ghost character shown in reverse video (cursor)
- [x] Remaining ghost characters dimmed (BRIGHT_BLACK)
- [x] Right arrow accepts one ghost character into input
- [x] Left arrow rejects one character back to ghost text
- [x] Ghost suffix updates dynamically as characters accepted/rejected

**Visual Example:**
```
User types: /
Shows:      /n̲ew  ('n' has cursor, 'ew' is dimmed)

Press RIGHT: /n e̲w  ('n' accepted, cursor on 'e')
Press RIGHT: /ne w̲  ('e' accepted, cursor on 'w')
Press LEFT:  /n e̲w  ('w' back to ghost, cursor on 'e')
```

**Key Bindings Added:**
| Key | Action |
|-----|--------|
| `→` | Accept one ghost character |
| `←` | Reject one ghost character |

**Validation:** Tests verify bidirectional ghost text flow

---

## Success Criteria ✅

- [x] Typing `/` shows all available commands
- [x] Typing `/r` filters to commands containing "r"
- [x] `/resume ` shows available session IDs
- [x] Tab and Enter both accept completions
- [x] Up/Down arrows navigate without moving text cursor
- [x] Esc closes menu without accepting
- [x] Menu renders above input (not below)
- [x] Provider called on every keystroke (Option 2 behavior)
- [x] `with_completion()` fluent API works for attaching completion
- [x] Ghost text shows inline preview with cursor on first character
- [x] Right arrow accepts ghost characters one at a time
- [x] Left arrow rejects ghost characters one at a time

---

## Implementation Status

**Status:** ✅ COMPLETE (2026-03-01)

**Files Created:**
- `src/interfaces/pypitui/completion_menu.py` - Menu rendering component
- `src/interfaces/pypitui/completion_addon.py` - Composable completion behavior
- `src/interfaces/pypitui/fuzzy.py` - Fuzzy matching utility

**Files Modified:**
- `src/interfaces/pypitui/wrapped_input.py` - Added hook support and `with_completion()` API
- `src/interfaces/pypitui/tui.py` - Integrated completion into AlfredTUI

**Tests:** 87+ tests in `tests/pypitui/test_completion*.py` - all passing

**Documentation:** `docs/COMPLETION.md` - User guide for completion system

**Deferred:** Visual highlight of matched characters (stretch goal, not required for MVP)

---

## Open Questions

1. **Async providers?** Should providers support async for file system queries?
2. **Multi-provider?** Support multiple providers with priority/merging?
3. **History integration?** Should Up arrow in empty input show history vs navigate menu?
4. **Provider caching?** Cache provider results for performance, or always call?

---

## References

- Issue: #97
- Related: `WrappedInput` in `src/interfaces/pypitui/wrapped_input.py`
- Related: `AlfredTUI` in `src/interfaces/pypitui/tui.py`
