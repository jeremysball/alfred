### write - Write File Contents

Create a new file or overwrite an existing file with content.

**Parameters:**
- `path` (required): Path where to write the file
- `content` (required): Content to write to the file

**When to use:**
- Creating new source files
- Writing configuration files
- Generating documentation
- Saving output/data to files

**Examples:**

```python
# Create a new Python module
write(
    path="src/utils/helpers.py",
    content="""def format_date(dt):
    return dt.strftime("%Y-%m-%d")
"""
)

# Write JSON configuration
write(
    path="config.json",
    content='{"debug": true, "port": 8080}'
)

# Create a README
write(
    path="README.md",
    content="# My Project\n\nDescription here."
)
```

**Tips:**
- Overwrites existing files without warning
- Creates parent directories if they don't exist
- Use `edit` for modifying existing files instead
