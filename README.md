# Alfred

<p align="center">
  <img src="https://raw.githubusercontent.com/jeremysball/alfred/main/assets/alfred-demo.gif" alt="Alfred Demo" width="800">
</p>

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
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.12+-blue.svg?style=flat-square" alt="Python">
  </a>
</p>

---

Alfred is a **persistent memory system** that lives in your files, remembers your conversations, and helps you build context with LLMs by storing embeddings, searching semantically, and injecting relevant memories — all through familiar interfaces like **Telegram** and **CLI**.

## The Problem

LLMs forget everything when you close the chat. Every conversation starts from zero. You repeat yourself, lose context, and can't build lasting knowledge.

**Alfred solves this** by persisting memories in files you control, making your AI assistant actually useful across sessions.

## Quick Start

```bash
# Install Alfred
pip install alfred-memory

# Configure (one-time setup)
alfred init

# Start chatting
alfred chat
```

Or use Telegram:

```bash
# Set up Telegram bot (see docs)
alfred telegram setup

# Start the bot
alfred telegram start
```

Then message your bot on Telegram (see setup docs).

## How It Works

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Message   │────▶│   Alfred    │────▶│   Search    │
│  (Telegram  │     │   Engine    │     │   Memory    │
│    or CLI)  │     │             │     │             │
└─────────────┘     └──────┬──────┘     └──────┬──────┘
                           │                    │
                           ▼                    │
                    ┌─────────────┐            │
                    │  Generate   │◀───────────┘
                    │  Embedding  │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │    Store    │
                    │  (JSONL +   │
                    │  vectors)   │
                    └─────────────┘
```

**Three steps to persistent memory:**

1. **Store**: Every conversation saved to `data/memories.jsonl` with embeddings
2. **Search**: Semantic search finds relevant past conversations instantly
3. **Inject**: Context automatically added to LLM prompts

## Features

### Core Memory System
- [x] **Persistent Memory**: Conversations stored in JSONL files you control
- [x] **Semantic Search**: OpenAI embeddings for finding relevant context
- [x] **Dual Memory**: Message-level (facts) + session-level (narrative) storage
- [x] **Session Management**: Organize conversations by project or topic
- [x] **Memory Tools**: Search, update, and manage memories programmatically

### Interfaces
- [x] **Telegram Integration**: Chat with Alfred via Telegram bot
- [x] **CLI Interface**: Terminal-based chat with streaming responses
- [x] **Library**: Use `from alfred import Alfred` to integrate into your own applications

### Automation & Scheduling
- [x] **Cron Scheduler**: Schedule jobs with natural language ("remind me every morning at 8am")
- [x] **Job Notifications**: Jobs can send messages back to you via Telegram/CLI
- [x] **System Jobs**: Auto-summarize sessions, compact old memories, health reports
- [x] **Human Approval**: User jobs require approval before execution (security)

### Tools & Capabilities
- [x] **File Operations**: Read, write, and edit files
- [x] **Bash Execution**: Run shell commands in controlled environment
- [x] **Memory CRUD**: Create, read, update, delete memories
- [x] **Search Tools**: Semantic search across memories and sessions
- [x] **Job Management**: Schedule, list, approve, and reject jobs

### Intelligence
- [x] **Context Injection**: Automatic retrieval of relevant past conversations
- [x] **Session Summarization**: Auto-generate conversation summaries
- [x] **Streaming Responses**: Real-time token streaming
- [x] **Multi-Provider**: Support for Kimi, OpenAI, and other LLM providers

### Configuration
- [x] **File-Based Config**: Human-readable `SOUL.md`, `AGENTS.md`, `TOOLS.md`
- [x] **Privacy First**: Everything local — no cloud, no data sent to us

## Interfaces

| Feature | Telegram | CLI | Library |
|---------|----------|-----|---------|
| Chat | ✅ | ✅ | ❌ |
| Memory Search | ✅ | ✅ | ✅ |
| Session Management | ✅ | ✅ | ✅ |
| Tool Execution | ✅ | ✅ | ✅ |
| Job Scheduling | ✅ | ✅ | ✅ |
| Streaming Responses | ✅ | ✅ | ✅ |

**Telegram**: Message your bot or run your own.

**CLI**: Run `alfred chat` for interactive terminal sessions.

**Library**: Use `from alfred import Alfred` to integrate into your own applications.

## Example: Chat with Memory

```python
from alfred import Alfred

# Initialize Alfred
alfred = Alfred()

# Chat — context automatically injected
response = await alfred.chat(
    "What did we discuss about my database schema?"
)
# Alfred searches memory and responds with context

# Search memories programmatically
memories = await alfred.search("database schema", limit=5)
for memory in memories:
    print(f"{memory['timestamp']}: {memory['content']}")
```

## Example: Scheduled Jobs

```python
# Create a job that runs every morning
job = await alfred.schedule_job(
    name="Daily standup reminder",
    schedule="0 9 * * 1-5",  # Weekdays at 9am
    code='''
async def run(context):
    await context.notify("Time for standup! Here's what you did yesterday:")
    memories = await context.search("yesterday", limit=3)
    for m in memories:
        await context.notify(f"• {m['content'][:100]}...")
'''
)

# Alfred will ask for approval before activating the job
```

## Data Transparency

**Alfred stores everything locally:**

- **Conversations**: `data/memories.jsonl` (text, timestamp, embedding)
- **Sessions**: `data/session_summaries.jsonl` (conversation summaries)
- **Jobs**: `data/cron.jsonl` (scheduled jobs) + `data/cron_history.jsonl` (execution history)
- **Config**: `SOUL.md`, `AGENTS.md`, `TOOLS.md` (human-readable)

**No cloud. No data sent to us. No phone home.** Your memories live in files you control.

## Documentation

Documentation coming soon. For now, see:

- [Architecture Diagram](https://github.com/jeremysball/alfred/blob/main/research/78-readme-redesign/assets/architecture-diagram.svg)
- [Demo Script](https://github.com/jeremysball/alfred/blob/main/research/78-readme-redesign/assets/demo-gif-script.md)
- Inline code documentation in `src/`

## Community

- [GitHub Discussions](https://github.com/jeremysball/alfred/discussions) — Ask questions, share ideas
- [GitHub Issues](https://github.com/jeremysball/alfred/issues) — Report bugs, request features
- Discord — Coming soon

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

<p align="center">
  Made with ❤️ and 🧠
</p>

<p align="center">
  <strong>Alfred remembers so you don't have to</strong>
</p>
