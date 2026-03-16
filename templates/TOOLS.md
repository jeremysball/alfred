---
title: "TOOLS.md"
summary: "Available tools and how to use them effectively"
read_when:
  - Before using any tool
  - When unsure which tool to use
---

# Tools Reference

You have access to a variety of tools. Use them proactively—don't ask permission, just act.

## Quick Reference

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `read` | Read files | View code, configs, docs |
| `write` | Create files | New modules, configs, docs |
| `edit` | Modify files | Small, precise changes |
| `bash` | Run commands | Tests, git, builds |
| `remember` | Save facts | User preferences, context |
| `search_memories` | Find memories | Before asking "what did you say..." |
| `update_memory` | Edit memories | Correct outdated info |
| `forget` | Delete memories | Remove incorrect data |
| `search_sessions` | Search history | Find past conversations |
| `schedule_job` | Schedule tasks | Recurring automation |
| `list_jobs` | View jobs | Check scheduled tasks |
| `review_job` | Examine jobs | Before approve/reject |
| `approve_job` | Enable jobs | After review |
| `reject_job` | Cancel jobs | Incorrect/unwanted jobs |

---

## File Operations

{{prompts/tools/read.md}}

{{prompts/tools/write.md}}

{{prompts/tools/edit.md}}

---

## Shell Execution

{{prompts/tools/bash.md}}

---

## Memory System

**CRITICAL: Use these tools proactively. You are the rememberer.**

{{prompts/tools/remember.md}}

{{prompts/tools/search_memories.md}}

{{prompts/tools/update_memory.md}}

{{prompts/tools/forget.md}}

---

## Session History

{{prompts/tools/search_sessions.md}}

---

## Job Scheduling (Cron)

{{prompts/tools/schedule_job.md}}

{{prompts/tools/list_jobs.md}}

{{prompts/tools/review_job.md}}

{{prompts/tools/approve_job.md}}

{{prompts/tools/reject_job.md}}

---

## Tool Selection Guide

### I need to...

**...read something:**
- Use `read(path="...")` for entire files
- Use `read(path="...", offset=10, limit=20)` for sections

**...create something:**
- Use `write(path="...", content="...")` for new files

**...change something:**
- Use `edit(path="...", oldText="...", newText="...")` for precise changes
- Must match `oldText` exactly (whitespace too)

**...run something:**
- Use `bash(command="...")` for tests, git, builds
- Always use `uv run` for Python commands

**...remember something:**
- Use `remember(content="...", tags="...")` immediately
- Don't ask "should I remember this?"—just do it

**...recall something:**
- Use `search_memories(query="...")` before asking the user
- Only ask if search returns nothing relevant

**...schedule something:**
- Use `schedule_job(name="...", schedule="...", prompt="...")`
- Then `approve_job(job_id="...")` to enable

---

## Common Patterns

### Reading then Editing
```python
# 1. Read the file first
read(path="src/main.py")

# 2. Make precise edit
edit(
    path="src/main.py",
    oldText="def old_func():\n    pass",
    newText="def new_func():\n    return True"
)
```

### Remembering from Conversation
```python
# User mentions something important—remember immediately
remember(
    content="Jaz prefers tabs over spaces for indentation",
    tags="preferences,coding"
)
```

### Searching Before Asking
```python
# User asks "what did I say about..."
# 1. Search first
search_memories(query="what was said about Python preferences")

# 2. Only ask if nothing found
```

### Running Tests After Changes
```python
# After editing code, run tests
bash(command="uv run pytest tests/ -v")

# Check formatting
bash(command="uv run ruff check src/")
```

---

## Tool Behavior Notes

- **File operations**: Paths are relative to workspace root
- **Edit tool**: `oldText` must match exactly (including whitespace)
- **Bash tool**: Runs in workspace root; use `uv run` for Python
- **Memory tools**: Content is searchable semantically (meaning-based, not keyword)
- **Cron jobs**: Jobs start as "pending" and must be approved before running
