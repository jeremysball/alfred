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

## Table Rendering

### Automatic Setup

Playwright browsers install **automatically** on first run. No manual steps.

If auto-install fails:
```bash
uv run playwright install chromium
```

### How It Works

**Phase 1: Markdown → HTML → Image**
- `markdown` library converts table markdown to HTML
- `playwright` renders HTML to PNG via headless Chromium
- Result: Clean, styled table images

**Phase 2: Multi-Part Messages**
If message + table exceeds limits:
1. Send introductory text
2. Send table as image
3. Send follow-up text

### Implementation

```python
from alfred.table_renderer import TableRenderer

renderer = TableRenderer()
image = await renderer.render_table("| Name | Value |\n|------|-------|\n| A | 1 |")
await update.message.reply_photo(photo=image)
```

### Dependencies

Already in `pyproject.toml`:
- `markdown>=3.5`
- `playwright>=1.40`

### No Streaming Support

Current implementation sends full responses via `reply_text()`. No streaming.
