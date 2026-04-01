# Command Completion System

Alfred's TUI provides inline command completion for slash commands such as:
- `/new`
- `/resume`
- `/sessions`
- `/session`
- `/context`
- `/health`

This document describes the **user-visible behavior** and the current high-level implementation shape.

It is not a stable public Python API for completion internals.

---

## Overview

Type `/` at the start of the input to open the completion menu.

You can:
- navigate options with arrow keys
- accept the highlighted option with `Tab` or `Enter`
- use ghost-text preview to see what will be inserted as you type

The goal is fast, low-friction command discovery inside the TUI.

---

## Key Bindings

| Key | Action |
|-----|--------|
| `/` | Trigger completion when typed at the start of the input |
| `↑` / `↓` | Move through completion options |
| `→` | Accept one ghost character |
| `←` | Reject one ghost character |
| `Tab` / `Enter` | Accept full completion |
| `Esc` | Close the menu |

---

## Ghost Text Behavior

Ghost text shows the remaining characters of the selected completion with the cursor on the first ghost character.

```text
User types: /
Shows:      /n̲ew
```

### Accepting characters

Press `→` to accept ghost characters one at a time:

```text
/̲      → /n̲ew
/n̲ew   → /n e̲w
/n e̲w  → /ne w̲
/ne w̲  → /new
```

### Rejecting characters

Press `←` to put accepted characters back into ghost text:

```text
/new    → /ne w̲
/ne w̲  → /n e̲w
/n e̲w  → /n̲ew
```

This makes it possible to steer completion precisely without retyping the whole command.

---

## Current Implementation Shape

The current TUI completion flow is built around three ideas:

1. **Command registry**  
   Slash commands live under `alfred.interfaces.pypitui.commands`.

2. **Fuzzy matching**  
   Command matching uses `alfred.interfaces.pypitui.fuzzy.fuzzy_match()`.

3. **TUI integration**  
   The actual popup/ghost-text behavior is wired into the TUI runtime rather than exposed as a stable standalone library API.

That means the behavior is intentional, but the internal component boundaries may keep changing as the TUI evolves.

---

## Fuzzy Matching

Alfred uses subsequence-style fuzzy matching for command lookup.

Examples:
- `/r` matches `/resume`
- `res` matches `/resume`
- `/ss` can match a longer slash command if the characters appear in order

The helper lives in:
- `src/alfred/interfaces/pypitui/fuzzy.py`

Example:

```python
from alfred.interfaces.pypitui.fuzzy import fuzzy_match

assert fuzzy_match("/r", "/resume") is True
assert fuzzy_match("xyz", "/resume") is False
```

---

## Commands as the Source of Truth

The completion menu should reflect the command set Alfred actually supports.

Today, the command implementations live under:
- `src/alfred/interfaces/pypitui/commands/`

Examples include:
- `new_session.py`
- `resume_session.py`
- `list_sessions.py`
- `show_session.py`
- `show_context.py`
- `health.py`

If you add, remove, or rename commands, completion behavior should stay aligned with that registry.

---

## Testing Guidance

Prefer testing the user-visible flow over brittle internal details.

Good tests check things like:
- opening the completion menu from `/`
- matching the expected commands
- accepting a completion
- rejecting ghost text correctly
- keeping command discovery aligned with the actual command registry

When TUI internals change, update the tests to preserve the interaction contract rather than old component names.

---

## Related Docs

- [`README.md`](../README.md)
- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`TUI-RENDERING-PITFALLS.md`](TUI-RENDERING-PITFALLS.md)
