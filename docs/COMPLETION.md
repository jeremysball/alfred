# Command Completion System

The completion system provides IDE-style inline command suggestions for Alfred's TUI.

## Overview

Type `/` to open the completion menu. Navigate with arrow keys. Accept with `Tab` or `Enter`. The ghost text preview shows what will be inserted as you type.

## Key Bindings

| Key | Action |
|-----|--------|
| `/` | Trigger completion menu (when typed at start) |
| `↑` / `↓` | Navigate through options |
| `→` | Accept one ghost character |
| `←` | Reject one ghost character |
| `Tab` / `Enter` | Accept full completion |
| `Esc` | Close menu without accepting |

## Ghost Text Behavior

Ghost text shows the remaining characters of the selected completion with the cursor on the first ghost character.

```
User types: /
Shows:      /n̲ew  ('n' has cursor, 'ew' is dimmed)
```

### Accepting Characters

Press `→` to accept ghost characters one at a time:

```
/̲      → /n̲ew  (ghost appears)
/n̲ew   → /n e̲w  ('n' accepted, cursor on 'e')
/n e̲w  → /ne w̲  ('e' accepted, cursor on 'w')
/ne w̲ → /new   ('w' accepted, completion done)
```

### Rejecting Characters

Press `←` to put accepted characters back into ghost text:

```
/new   → /ne w̲  ('w' back to ghost)
/ne w̲ → /n e̲w  ('e' back to ghost)
/n e̲w  → /n̲ew   ('n' back to ghost)
```

This bidirectional flow lets you navigate completions precisely.

## Architecture

The completion system consists of three components:

### CompletionAddon

Attaches to a `WrappedInput` field. Registers render hooks and input handlers.

```python
from src.interfaces.pypitui.completion_addon import CompletionAddon

addon = CompletionAddon(
    input_component=input_field,
    provider=command_provider,
    trigger="/",
    max_height=5,
)
```

### CompletionMenu

Renders the popup menu with box-drawing characters and reverse video selection.

### Provider Function

Returns matching completions based on current input:

```python
def provider(text: str) -> list[tuple[str, str | None]]:
    """Return list of (value, description) tuples."""
    if text.startswith("/"):
        return [
            ("/new", "New session"),
            ("/resume", "Resume session"),
        ]
    return []
```

## Implementation Details

### Ghost Text Rendering

Ghost text uses the APC cursor marker (`\x1b_pi:c\x07`) to locate the cursor position. The render hook:

1. Locates the cursor marker and reverse video sequence
2. Replaces the space character with the first ghost character
3. Appends remaining ghost characters in `BRIGHT_BLACK` (gray)

### Arrow Key Handling

- `→` (`\x1b[C`): Accepts first ghost character into input value
- `←` (`\x1b[D`): Removes last input character back to ghost text

Both update `_last_text` to prevent duplicate completion updates.

### Menu Position

The menu renders above the input line using render hooks to prepend lines.

## Testing

Tests cover the completion flow:

```python
def test_right_arrow_accepts_ghost_char():
    """Right arrow accepts first ghost character."""
    input_field.set_value("/")
    addon._on_render(["> /"], 80)
    
    result = addon.handle_input("\x1b[C")  # Right arrow
    assert result == {"consume": True}
    assert input_field.get_value() == "/n"
```

Run completion tests:

```bash
uv run pytest tests/pypitui/test_completion_addon.py -v
```

## Fuzzy Matching

The completion system uses subsequence matching. Characters need not be consecutive, only in order.

| Query | Matches | Does Not Match |
|-------|---------|----------------|
| `/r` | `/resume` | - |
| `res` | `/resume` | - |
| `/rs` | `/resume` | - |
| `xyz` | - | `/resume` |

This lets you type partial matches quickly without exact prefixes.

## Future Extensions

- **History suggestions**: Prioritize recently used commands
- **Context-aware**: Different completions based on conversation state
- **Partial accept**: Accept up to next delimiter (e.g., `/new sess`)
