# Alfred

<p align="center">
  <strong>Alfred remembers so you don't have to</strong>
</p>

<p align="center">
  <a href="https://github.com/jeremysball/alfred/actions/workflows/ci.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/jeremysball/alfred/ci.yml?branch=main&label=tests&style=flat-square" alt="Tests">
  </a>
  <a href="https://github.com/jeremysball/alfred/releases">
    <img src="https://img.shields.io/github/v/release/jeremysball/alfred?style=flat-square" alt="Version">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square" alt="License">
  </a>
</p>

---

Alfred is a persistent memory system for LLMs. He stores your conversations locally, searches them semantically, and injects relevant context into prompts automatically. Chat via Telegram or CLI.

## Quick Start

```bash
pip install alfred-assistant
alfred init
alfred chat
```

## What It Does

LLMs forget everything when you close the chat. Alfred solves this by:

1. **Storing** every conversation to `data/memories.jsonl` with embeddings
2. **Searching** semantically when you ask a question
3. **Injecting** relevant context into the LLM prompt automatically

All local. No cloud. Your data stays in files you control.

## Features

- **Persistent Memory** — JSONL files with OpenAI embeddings
- **Dual Storage** — Message-level facts + session-level narratives
- **Semantic Search** — Find relevant context instantly
- **Telegram Bot** — Chat anywhere
- **CLI** — Terminal interface with streaming
- **Scheduled Jobs** — "Remind me every morning at 8am"
- **File Tools** — Read, write, edit, bash execution
- **Human Approval** — Jobs require approval before running

## Example

```python
from alfred import Alfred

alfred = Alfred()

# Chat with automatic memory
response = await alfred.chat("What did we decide about the database?")

# Search memories
memories = await alfred.search("database schema", limit=5)
```

## Data Storage

- `data/memories.jsonl` — Conversations with embeddings
- `data/session_summaries.jsonl` — Conversation summaries
- `data/cron.jsonl` — Scheduled jobs
- `SOUL.md`, `AGENTS.md`, `TOOLS.md` — Configuration

## Documentation

- [Architecture Diagram](research/78-readme-redesign/assets/architecture-diagram.svg)
- [Research & Variations](research/78-readme-redesign/)

## Community

- [GitHub Discussions](https://github.com/jeremysball/alfred/discussions)
- [GitHub Issues](https://github.com/jeremysball/alfred/issues)

## License

MIT

---

<p align="center">Made with ❤️ and 🧠</p>
