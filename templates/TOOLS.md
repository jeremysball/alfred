---
title: "TOOLS.md"
summary: "Global tool-use heuristics"
read_when:
  - Every conversation start
  - When deciding which tool to use
---

# Tool Use Guide

Tools are capabilities, not permissions. Use the smallest tool that can safely achieve the outcome.

## Core Heuristics

- If a dedicated tool exists and fits the task, use it.
- If no dedicated tool exists but standard shell commands can do the work safely, use `bash`.
- Do not refuse a task solely because there is no specialized tool for it.
- Prefer non-interactive, bounded commands and keep shell output focused.
- Search for prior context before asking the user to repeat themselves.

## Common Choices

### File work
- `read(path, offset?, limit?)` to inspect files
- `edit(path, oldText, newText)` for precise changes
- `write(path, content)` for new files or full rewrites

### Shell work
- `bash(command, timeout?)` for running commands, searching the repo, calling standard CLIs, inspecting data, and other shell-safe work
- Good examples: `rg`, `find`, `git`, `jq`, `sqlite3`, `curl`, test commands, build commands

### Memory and history
- `remember(content, tags?, permanent?)` for durable facts worth recalling later
- `search_memories(query, top_k?)` for preferences, facts, and recurring context
- `search_sessions(query, top_k?, messages_per_session?, after?, before?)` for prior discussions and time-bounded recall

## Retrieval Order

Use this order when prior context may matter:
1. current conversation
2. `search_memories`
3. `search_sessions`
4. ask the user

## Memory Quality

Remember selectively. Good memories are:
- likely to matter again
- concise and searchable
- not noisy duplicates

Bad memories are:
- one-off transient details
- low-value logs pasted into memory
- facts already captured in durable files
