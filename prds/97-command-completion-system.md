# PRD #97: Command Completion System for TUI

## Overview

Add tab-triggered command completion with a dropdown menu that renders above the input line. The system calls a registered provider function on every keystroke to get filtered completion options.

---

## Problem Statement

Users must type complete commands like `/resume abc123` without any assistance. There is no discovery mechanism for:
- Available slash commands (`/new`, `/resume`, `/sessions`)
- Session IDs for the `/resume` command
- Future command arguments (file paths, memory IDs, etc.)

This creates friction and requires users to remember exact command syntax.

---

## Solution

A completion system integrated into `WrappedInput` that:
1. Activates when input matches a trigger prefix (default: `/`)
2. Calls a registered provider function on every keystroke
3. Renders a dropdown menu **above** the input line
4. Supports fuzzy filtering (provider returns all options, filters client-side)
5. Accepts selection via **Tab** or **Enter**
6. Navigates with **Up/Down** arrows
7. Closes with **Esc** or when trigger prefix is deleted

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

### Registration

```python
class CompletingInput(WrappedInput):
    def register_completion_provider(
        self,
        provider: Callable[[str], list[tuple[str, str | None]]],
        trigger: str = "/",
        max_height: int = 5,
    ) -> None:
        """Register a completion provider.
        
        Args:
            provider: Function called on every keystroke while trigger matches.
                     Takes current input text, returns list of (value, description).
                     Return empty list to hide menu.
            trigger: Prefix that activates completion mode.
            max_height: Maximum menu height (renders upward from input).
        """
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
input_field = CompletingInput(placeholder="Message Alfred...")
input_field.register_completion_provider(command_provider, trigger="/")
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
| `Esc` | Close menu without accepting |
| Any other key | Pass to input, re-filter menu |

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
        # Replace WrappedInput with CompletingInput
        self.input_field = CompletingInput(placeholder="Message Alfred...")
        
        # Register completion provider
        self.input_field.register_completion_provider(
            self._completion_provider,
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

## Milestones

### Milestone 1: Core CompletionMenu Component
**Deliverable:** `CompletionMenu` class that renders above input
- [ ] Renders upward from specified position
- [ ] Handles selection state (up/down navigation)
- [ ] Renders with box-drawing characters
- [ ] Supports descriptions (dim, right-aligned)
- [ ] Limited height with scroll indicator if overflow

**Validation:** Unit tests verify rendering at various sizes

### Milestone 2: CompletingInput Integration
**Deliverable:** `CompletingInput` extends `WrappedInput` with completion
- [ ] `register_completion_provider()` API
- [ ] Calls provider on every keystroke matching trigger
- [ ] Integrates `CompletionMenu` into render cycle
- [ ] Intercepts Tab/Enter/Up/Down/Esc when menu open
- [ ] Delegates other keys to parent `WrappedInput`

**Validation:** Tests verify provider called, menu shows/hides, keys intercepted

### Milestone 3: Fuzzy Matching & Filtering
**Deliverable:** Fuzzy matching algorithm integrated
- [ ] `fuzzy_match()` utility function
- [ ] Provider results filtered by fuzzy match score
- [ ] Results sorted by match quality (exact prefix > subsequence)
- [ ] Visual highlight of matched characters (optional stretch)

**Validation:** Tests verify fuzzy matching behavior

### Milestone 4: AlfredTUI Integration
**Deliverable:** Command completion works in Alfred TUI
- [ ] `CompletingInput` replaces `WrappedInput` in `AlfredTUI`
- [ ] Provider implementation for `/` commands
- [ ] Provider implementation for `/resume ` session IDs
- [ ] Session IDs fetched from `SessionManager`

**Validation:** Manual test - type `/`, see commands; type `/resume `, see sessions

### Milestone 5: Edge Cases & Polish
**Deliverable:** Production-ready completion system
- [ ] Menu closes when terminal resized
- [ ] Menu handles rapid typing (debounce if needed)
- [ ] Provider errors don't crash UI (catch and log)
- [ ] Empty provider result shows "No matches" message
- [ ] Menu width adapts to content and terminal size

**Validation:** All tests pass, manual stress testing

---

## Success Criteria

- [ ] Typing `/` shows all available commands
- [ ] Typing `/r` filters to commands containing "r"
- [ ] `/resume ` shows available session IDs
- [ ] Tab and Enter both accept completions
- [ ] Up/Down arrows navigate without moving text cursor
- [ ] Esc closes menu without accepting
- [ ] Menu renders above input (not below)
- [ ] Provider called on every keystroke (Option 2 behavior)

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
