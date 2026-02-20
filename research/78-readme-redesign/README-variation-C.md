# Alfred

Persistent memory for LLMs. Stores conversations locally, searches semantically, injects context automatically.

[![Tests](https://img.shields.io/github/actions/workflow/status/jeremysball/alfred/ci.yml?branch=main&label=tests)](https://github.com/jeremysball/alfred/actions/workflows/ci.yml)
[![Version](https://img.shields.io/github/v/release/jeremysball/alfred)](https://github.com/jeremysball/alfred/releases)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Quick Start

```bash
pip install alfred-memory
alfred init
alfred chat
```

Or via Telegram:

```bash
alfred telegram setup
alfred telegram start
```

## What It Does

Alfred stores every conversation in JSONL files, generates embeddings for semantic search, and automatically injects relevant past context into LLM prompts.

Storage: `data/memories.jsonl` (text + embeddings)  
Config: `SOUL.md`, `AGENTS.md`, `TOOLS.md` (human-readable)  
Search: Cosine similarity on OpenAI embeddings  
Interfaces: Telegram, CLI, Python library

## Example

```python
from alfred import Alfred

alfred = Alfred()

# Chat with automatic memory
response = await alfred.chat("What did we decide about the database?")

# Search memories directly
memories = await alfred.search("database schema", limit=5)
```

## Features

- Persistent storage in JSONL files
- Semantic search with embeddings
- Telegram bot interface
- CLI with streaming responses
- Session management
- 100% local (no cloud)

## Interfaces

| Feature | Telegram | CLI | Library |
|---------|----------|-----|---------|
| Chat | Yes | Yes | No |
| Memory search | Yes | Yes | Yes |
| Session management | Yes | Yes | Yes |
| Tool execution | Yes | Yes | Yes |

## Architecture

```
Message → Alfred → Generate Embedding → Store (JSONL)
                       ↓
              Search (cosine similarity)
                       ↓
              Inject context → LLM → Response
```

## Documentation

- [Getting Started](docs/getting-started.md)
- [Configuration](docs/configuration.md)
- [API Reference](docs/api.md)

## License

MIT
