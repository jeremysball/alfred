### bash - Execute Shell Commands

Execute bash commands in the workspace directory.

**Parameters:**
- `command` (required): The bash command to execute
- `timeout` (optional): Timeout in seconds (default varies by operation)

**When to use:**
- Running tests
- Checking git status
- Listing directory contents
- Running build scripts
- Installing dependencies

**Examples:**

```python
# Run tests
bash(command="uv run pytest tests/ -v")

# Check git status
bash(command="git status")

# List files with details
bash(command="ls -la src/")

# Run a specific test file
bash(command="uv run pytest tests/test_main.py -v")

# Check code formatting
bash(command="uv run ruff check src/")

# Run type checking
bash(command="uv run mypy src/")
```

**Tips:**
- Commands run in the workspace root directory
- Use `uv run` for Python commands (ensures correct venv)
- Output is captured and returned
- Long-running commands may timeout
- Avoid interactive commands (they will hang)
