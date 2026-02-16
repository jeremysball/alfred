# OpenClaw Pi Architecture

## System Overview

OpenClaw Pi is a Telegram bot that provides persistent, multi-threaded access to the Pi coding agent. Each Telegram thread gets its own isolated conversation context.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Telegram API  │────▶│  TelegramBot    │────▶│   Dispatcher    │
│   (Webhooks)    │     │  (handlers)     │     │   (routing)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                          │
                           ┌──────────────────────────────┘
                           ▼
                  ┌─────────────────┐
                  │  PiManager      │
                  │  (subprocess)   │
                  └─────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  Pi Agent       │
                  │  (--print mode) │
                  └─────────────────┘
                           │
                           ▼
                  ┌─────────────────┐     ┌─────────────────┐
                  │  LLM Provider   │     │  ThreadStorage  │
                  │  (Z.AI, etc.)   │     │  (JSON files)   │
                  └─────────────────┘     └─────────────────┘
```

## Component Responsibilities

### TelegramBot (`telegram_bot.py`)
- Handles Telegram Bot API webhooks
- Routes commands to CommandHandlers
- Shows typing indicators while processing
- Manages bot lifecycle (start/stop)

### Dispatcher (`dispatcher.py`)
- Routes messages to appropriate handlers
- Manages thread lifecycle
- Spawns sub-agents for background tasks
- Handles errors and timeouts

### PiManager (`pi_manager.py`)
- Spawns Pi subprocesses (one per message)
- Tracks "active" threads (during processing)
- Manages API keys and provider config
- Handles timeouts

### ThreadStorage (`storage.py`)
- Persists thread state to JSON files
- One file per thread: `threads/<thread_id>.json`
- Async file I/O with aiofiles

### Memory System (`memory.py`)
- Daily memory files: `memory/YYYY-MM-DD.md`
- Long-term MEMORY.md curation
- Compaction strategies for archiving

### Embeddings (`embeddings.py`)
- OpenAI embeddings for semantic search
- Local fallback with sentence-transformers
- MemoryRetriever for similarity search

## Data Flow

### Message Handling
1. Telegram sends webhook to bot
2. `TelegramBot._handle_message()` receives update
3. Typing indicator started
4. `Dispatcher.handle_message()` called
5. Thread loaded from storage (or created)
6. `PiManager.send_message()` spawns Pi subprocess
7. Pi runs with `--print` flag, returns response
8. Response saved to thread, thread persisted
9. Telegram reply sent, typing stopped

### Command Handling
1. Telegram sends command (e.g., `/status`)
2. `CommandHandler` routes to `_handle_status()`
3. `Dispatcher.handle_command()` executes logic
4. Response sent directly via Telegram API

### Sub-agent Spawning
1. User sends `/subagent <task>`
2. Dispatcher creates sub-agent ID
3. Parent thread marked with active subagent
4. Background task `_run_subagent()` started
5. Isolated workspace created for sub-agent
6. Pi subprocess spawned for task
7. Result saved, parent thread updated

## File Organization

```
openclaw-pi/
├── openclaw_pi/           # Python package
│   ├── telegram_bot.py    # Telegram handlers
│   ├── dispatcher.py      # Message routing
│   ├── pi_manager.py      # Pi subprocess management
│   ├── storage.py         # Thread persistence
│   ├── memory.py          # Memory system
│   ├── embeddings.py      # Semantic search
│   ├── config.py          # Settings
│   └── models.py          # Pydantic models
│
├── workspace/             # User context (gitignored)
│   ├── AGENTS.md          # Agent configuration
│   ├── SOUL.md            # Personality
│   ├── USER.md            # User preferences
│   ├── MEMORY.md          # Long-term memory
│   ├── memory/            # Daily memory files
│   └── skills/            # Skill modules
│
├── threads/               # Thread storage (gitignored)
│   └── <thread_id>.json   # Per-thread state
│
└── docs/                  # Documentation
    ├── architecture/      # System design
    ├── design/            # Decision records
    └── help/              # User guides
```

## Thread State Format

```json
{
  "thread_id": "123_456",
  "chat_id": 123,
  "created_at": "2026-02-15T10:00:00Z",
  "updated_at": "2026-02-15T10:30:00Z",
  "messages": [
    {"role": "user", "content": "Hello", "timestamp": "2026-02-15T10:00:00Z"},
    {"role": "assistant", "content": "Hi!", "timestamp": "2026-02-15T10:00:05Z"}
  ],
  "active_subagent": null
}
```

## Configuration

Environment variables (`.env`):
- `TELEGRAM_BOT_TOKEN` - Bot API token
- `LLM_API_KEY` - Provider API key
- `OPENAI_API_KEY` - For embeddings (optional)
- `WORKSPACE_DIR` - User context directory
- `THREADS_DIR` - Thread storage directory
- `LOG_LEVEL` - DEBUG, INFO, WARNING, ERROR
- `PI_TIMEOUT` - Subprocess timeout (seconds)
- `LLM_PROVIDER` - zai, moonshot, etc.
- `LLM_MODEL` - Model identifier

## Security Model

- **Workspace gitignored** - User context never committed
- **Env vars for secrets** - API keys in `.env`, not code
- **No persistent Pi processes** - One-shot mode reduces attack surface
- **Thread isolation** - Each thread has separate workspace
- **MEMORY.md contextual** - Only loaded in 1:1 chats, not groups
