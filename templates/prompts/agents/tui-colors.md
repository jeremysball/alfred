## TUI Color Placeholders

Only use TUI color placeholders when color adds clarity.

- Use `{color}` ... `{reset}` instead of raw ANSI escape codes.
- Common choices: `{cyan}` for commands, `{green}` for success, `{red}` for errors, `{dim}` for secondary text.
- Background colors use `{on_red}`, `{on_blue}`, and similar forms — not `bg_red`.
- Placeholders do not render inside fenced code blocks.
