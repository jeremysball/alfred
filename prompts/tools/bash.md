### bash - Execute Shell Commands

Execute bash commands in the workspace directory.

**Parameters:**
- `command` (required): The bash command to execute
- `timeout` (optional): Timeout in seconds (default varies by operation)

**When to use:**
- Running tests, builds, scripts, and project commands
- Searching or inspecting the repository when no dedicated tool exists
- Using standard CLIs such as `rg`, `find`, `git`, `jq`, `sqlite3`, `curl`, `grep`, or `awk`
- Gathering information from files, processes, environment, or generated output
- Performing shell-safe work that available file tools do not cover directly

**Policy:**
- `bash` is the general fallback when a specialized tool is unavailable but shell commands can do the job safely.
- Do not refuse solely because there is no named tool for a task.
- Prefer non-interactive, bounded commands.
- Keep output focused with filters, pipes, or redirection when helpful.
- If `read`, `edit`, or `write` is clearly safer or simpler, prefer those for direct file manipulation.

**Examples:**

```python
# Run tests
bash(command="uv run pytest tests/ -v")

# Search the repo
bash(command="rg -n \"search_memories\" src tests")

# List matching files
bash(command="find src -name '*.py' | sort")

# Inspect JSON or SQLite data with standard tools
bash(command="jq '.name' package.json")
bash(command="sqlite3 data/app.db '.tables'")

# Fetch a page when HTTP access is needed and allowed
bash(command="curl -I https://example.com")
```

**Tips:**
- Commands run in the workspace root directory
- Use `uv run` for Python commands when appropriate
- Avoid interactive commands unless you have an interactive terminal tool
- Large output may be truncated, so prefer targeted queries
