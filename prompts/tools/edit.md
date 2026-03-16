### edit - Edit File Contents

Make precise, surgical edits to existing files using string replacement.

**Parameters:**
- `path` (required): Path to the file to edit
- `oldText` (required): Exact text to find (including whitespace)
- `newText` (required): Replacement text

**When to use:**
- Modifying specific lines in existing files
- Refactoring code
- Updating configuration values
- Fixing typos or bugs

**Examples:**

```python
# Fix a typo
edit(
    path="src/main.py",
    oldText="def calulate_total(price):",
    newText="def calculate_total(price):"
)

# Add a parameter to a function
edit(
    path="src/config.py",
    oldText="def load_config():\n    return {}",
    newText="def load_config(path=\"config.json\"):\n    return {}"
)

# Update a version number
edit(
    path="pyproject.toml",
    oldText='version = "1.0.0"',
    newText='version = "1.1.0"'
)
```

**Tips:**
- `oldText` must match exactly including whitespace and indentation
- For multi-line edits, include the newline characters
- Use `read` first to see the exact content
- Fails if `oldText` is not found
