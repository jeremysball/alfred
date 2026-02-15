# Agent Guidelines

## Code Style

### PEP 8

Follow [PEP 8](https://peps.python.org/pep-0008/) for all Python code.

### Docstrings Required

Every module, class, and function must have a docstring.

```python
def process_data(input: str) -> dict:
    """Process raw input into structured data.
    
    Args:
        input: Raw string data to process
        
    Returns:
        Dictionary with extracted fields
        
    Raises:
        ValueError: If input format is invalid
    """
```

### Document All APIs

- Public functions/methods: full docstrings with args/returns/raises
- Classes: purpose and usage examples
- Modules: high-level overview at top of file

## Tool Usage

### ALWAYS Use `uv`

- **Package install**: `uv pip install <package>`
- **Environment**: `uv venv` (not `python -m venv`)
- **Running**: `uv run <command>`
- **Lock file**: `uv lock` / `uv sync`

Never use raw `pip`, `venv`, or `poetry`.

## Git Practices

### Conventional Commits (ALWAYS)

Format: `<type>(<scope>): <subject>`

Types:
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation
- `style:` — Formatting
- `refactor:` — Code change, same behavior
- `test:` — Tests
- `chore:` — Maintenance

Examples:
```
feat(telegram): add typing indicator
fix(dispatcher): handle timeout edge case
docs(readme): update feature list
```

### Atomic Commits

- One logical change per commit
- Small. Reviewable. Revertible.
- Bad: "Fix bugs and add features"
- Good: "fix(storage): handle missing json file" + "feat(bot): add status command"

## Markdown Rendering

### telegramify-markdown

We use [telegramify-markdown](https://github.com/sudoskys/telegramify-markdown) to render markdown with native Telegram entities.

### Key Rules

1. **Always use `telegramify()`** — It's async and auto-splits long messages
2. **Pass entities as `list[dict]`** — Use `[e.to_dict() for e in entities]`
3. **Never set `parse_mode`** — Entities and parse_mode are mutually exclusive
4. **Entity offsets are UTF-16** — The library handles this internally

### Usage

```python
from telegramify_markdown import telegramify

# Convert markdown to Telegram entities
results = await telegramify("**Bold** and _italic_ text")

# Send each part (auto-split for messages > 4096 chars)
for text, entities in results:
    await update.message.reply_text(
        text,
        entities=[e.to_dict() for e in entities]
    )
```

### Important Notes

- `telegramify()` is **async** and must be awaited
- `convert()` is sync but doesn't auto-split
- Entity offsets are in UTF-16 code units (handled by library)
- Works with python-telegram-bot, aiogram, pyTelegramBotAPI

### Tables

Markdown tables render as formatted code blocks automatically:

```markdown
| Name | Value |
|------|-------|
| A    | 1     |
```

Renders as monospace text in Telegram.

### No Streaming Support

Current implementation sends full responses. No streaming.
