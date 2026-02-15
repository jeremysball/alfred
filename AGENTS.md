# Agent Guidelines

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

## Table Rendering Plan

### Goal
Send tables as images, not text blocks.

### Approach

**Phase 1: Markdown → HTML → Image**
- Use `markdown` library to convert table markdown to HTML
- Use `playwright` or `imgkit` (wkhtmltoimage) to render HTML to PNG
- Alternative: `selenium` with headless Chrome

**Phase 2: Multi-Part Messages**
If table + context exceeds limits:
1. Send introductory text
2. Send table as image
3. Send follow-up text

**Implementation Sketch**
```python
# Pseudocode
async def send_table(update, table_md: str, caption: str = ""):
    html = markdown.markdown(table_md, extensions=['tables'])
    styled = f"<style>table{{border-collapse:collapse}}...</style>{html}"
    
    # Render to image
    image = await render_html_to_png(styled)
    
    # Send
    await update.message.reply_photo(photo=image, caption=caption)
```

**Tools to Evaluate**
- `imgkit` + `wkhtmltoimage` — Simple, requires binary
- `playwright` — Modern, renders accurately, heavier
- `weasyprint` — Pure Python, CSS support

**Decision**: Start with `playwright` for accuracy. Fallback to `imgkit` if size matters.

### No Streaming Support

Current implementation sends full responses via `reply_text()`. No streaming.
