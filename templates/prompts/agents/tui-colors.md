## TUI Color System

Alfred's TUI supports **ANSI color placeholders** for styling agent responses. Use curly brace syntax `{color}` to add colors and styles to text.

**Always use color placeholders in your responses** instead of hardcoded ANSI escape codes. This improves readability and maintains consistency across the codebase.

### Usage

Wrap text with color placeholders:

```
{cyan}command{reset} executed {bold}{green}successfully{reset}
```

This renders as colored text in the TUI. **Always use `{reset}`** to end styling.

**Encouraged for agent responses:**
- Use `{cyan}` or `{green}` for commands and actions
- Use `{red}` for errors and warnings
- Use `{bold}` to emphasize important information
- Use `{dim}` for secondary or subtle information

### Available Colors

**Basic colors:** `{black}`, `{red}`, `{green}`, `{yellow}`, `{blue}`, `{magenta}`, `{cyan}`, `{white}`

**Bright colors:** `{bright_black}`, `{bright_red}`, `{bright_green}`, `{bright_yellow}`, `{bright_blue}`, `{bright_magenta}`, `{bright_cyan}`, `{bright_white}`

**Backgrounds:** Prefix any color with `on_` — `{on_red}`, `{on_green}`, `{on_blue}`, `{on_cyan}`, `{on_magenta}`, `{on_yellow}`, `{on_black}`, `{on_white}`

**Bright backgrounds:** `{on_bright_red}`, `{on_bright_green}`, etc.

| Wrong | Right |
|-------|-------|
| `{bg_red}` | `{on_red}` |
| `{background_red}` | `{on_red}` |
| `{red_bg}` | `{on_red}` |

### Available Styles

- `{bold}` — Bold text
- `{dim}` — Dimmed text
- `{italic}` — Italic text
- `{underline}` — Underlined text
- `{reset}` — Reset all styling (required to end colors)

### Examples

| Input | Result |
|-------|--------|
| `{red}Error:{reset} file not found` | Red "Error:" prefix |
| `{cyan}git status{reset}` | Cyan command name |
| `{bold}{green}✓{reset} Done` | Bold green checkmark |
| `{yellow}Warning:{reset} {dim}deprecated{reset}` | Yellow warning, dim note |
| `{on_red}{white}ALERT{reset}` | White text on red background |

### Code Blocks

Placeholders **do not work inside markdown code blocks**. This is intentional—code should display literally.

````markdown
# This shows literal {cyan}text{reset}, not colored text
```python
print("{cyan}hello{reset}")  # Displays literally
```
````

For colored code output, use placeholders outside the code block or use inline code with styling before/after.

### Implementation

The color system is in `src/interfaces/pypitui/ansi.py`. The `apply_ansi()` function replaces placeholders with ANSI escape codes before display.

**Two approaches for different contexts:**

1. **Agent responses** (text content): Use placeholder syntax like `{cyan}text{reset}`
2. **TUI rendering code** (low-level display): Import constants from `ansi.py`:
   ```python
   from src.interfaces.pypitui.ansi import BRIGHT_BLACK, RESET, REVERSE
   ```
