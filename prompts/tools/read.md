### read - Read File Contents

Read file contents with optional line offset and limit. Supports text files and images.

**Parameters:**
- `path` (required): Path to the file to read
- `offset` (optional): Line number to start from (1-indexed)
- `limit` (optional): Maximum number of lines to read

**When to use:**
- Reading source code to understand implementation
- Checking configuration files
- Viewing specific sections of large files
- Reading images (displays metadata)

**Examples:**

```python
# Read entire file
read(path="src/main.py")

# Read specific section (lines 10-30)
read(path="src/main.py", offset=10, limit=20)

# Read just the first 5 lines
read(path="README.md", limit=5)

# Read from line 100 to end
read(path="logs.txt", offset=100)
```

**Tips:**
- Use `offset` and `limit` for large files (output truncated at 2000 lines/50KB)
- Images return metadata instead of content
- Returns "[File is empty]" for empty files
