# OpenClaw Pi — Model Documentation

> Documentation for AI agents working on or with the OpenClaw Pi codebase.

## What is OpenClaw Pi?

OpenClaw Pi is a **Telegram bot dispatcher** that enables multi-threaded conversations with the Pi coding agent. Each Telegram thread gets its own isolated Pi subprocess with persistent state.

## Architecture Overview

```
Telegram Message → TelegramBot → Dispatcher → PiManager → Pi Subprocess
                                         ↓
                                    ThreadStorage (JSON)
```

### Key Components

| File | Responsibility |
|------|---------------|
| `telegram_bot.py` | Handles Telegram Bot API, message routing, typing indicators |
| `dispatcher.py` | Routes commands and messages to appropriate handlers |
| `pi_manager.py` | Manages Pi subprocess lifecycle (one per thread) |
| `storage.py` | Persistent thread storage (JSON files) |
| `config.py` | Environment-based configuration via pydantic-settings |
| `models.py` | Pydantic models for Thread, Message, etc. |

## File Locations

### Source Code
```
openclaw_pi/              # Main Python package
├── __init__.py           # Package exports
├── __main__.py           # python -m entry point
├── main.py               # CLI entry point (cli() function)
├── config.py             # Settings management
├── dispatcher.py         # Core message routing
├── pi_manager.py         # Pi subprocess management
├── telegram_bot.py       # Telegram integration
├── storage.py            # Thread persistence
├── models.py             # Data models
├── llm_api.py            # LLM API interface
└── subagent.py           # Subagent support
```

### Configuration
```
.env                      # Environment variables (gitignored)
pyproject.toml            # Package metadata and dependencies
```

### Runtime Data
```
workspace/                # User context (gitignored)
├── AGENTS.md             # This agent's configuration
├── SOUL.md               # Personality definition
├── USER.md               # User preferences
├── MEMORY.md             # Long-term memory
├── TOOLS.md              # Tool configuration
├── HEARTBEAT.md          # Periodic tasks
└── skills/               # Skill modules

threads/                  # Thread storage (JSON files, gitignored)
├── <chat_id>_<thread_id>.json
└── ...

memory/                   # Daily memory files (optional)
└── YYYY-MM-DD.md
```

### Templates
```
templates/                # Template files for bootstrapping
├── AGENTS.md
├── SOUL.md
├── USER.md
├── IDENTITY.md
├── TOOLS.md
├── HEARTBEAT.md
├── BOOT.md
├── BOOTSTRAP.md
└── *.dev.md             # Developer variants
```

## Configuration System

Uses `pydantic-settings` for environment-based configuration:

```python
from openclaw_pi.config import Settings

settings = Settings()
# settings.workspace_dir → Path
# settings.telegram_bot_token → str
# settings.llm_provider → str
```

### Environment Variables

**Required:**
- `TELEGRAM_BOT_TOKEN` — Telegram Bot API token

**Optional:**
- `WORKSPACE_DIR` — Default: `./workspace`
- `THREADS_DIR` — Default: `./threads`
- `LOG_LEVEL` — Default: `INFO`
- `PI_TIMEOUT` — Default: `300` (seconds)
- `LLM_PROVIDER` — Default: `zai`
- `LLM_API_KEY` — API key for provider
- `LLM_MODEL` — Model identifier
- `MAX_THREADS` — Default: `50`

## How Threads Work

1. **Thread ID Generation:** `{chat_id}_{message_thread_id}` (or just `chat_id` for DMs)
2. **Storage:** Each thread saved as JSON in `threads/` directory
3. **Pi Process:** One subprocess per thread, spawned on first message
4. **Session Files:** Pi sessions stored as `{thread_id}.json` in workspace

### Thread Lifecycle

```python
# Dispatcher.handle_message() flow:
1. Extract thread_id from update
2. Load thread from storage (or create new)
3. Get PiSubprocess from PiManager
4. Send message to pi subprocess
5. Receive response
6. Save thread with new messages
7. Return response to Telegram
```

## Commands

Dispatcher handles these slash commands:

| Command | Handler | Description |
|---------|---------|-------------|
| `/status` | `_handle_command` | Show active/stored thread counts |
| `/threads` | `_handle_command` | List stored thread IDs |
| `/kill <id>` | `_handle_command` | Kill a thread's Pi process |
| `/cleanup` | `_handle_command` | Kill all active processes |
| `/help` | `_handle_command` | Show help message |

## Pi Subprocess Management

Pi runs in `--print` mode (non-interactive) per message:

```python
# From pi_manager.py
cmd = [
    "pi",
    "--print",              # Non-interactive
    "--provider", provider,
    "--session", session_file,
    "--model", model,       # Optional
    message                 # The user's message
]
```

Each invocation:
1. Loads previous session (if exists)
2. Processes the message
3. Saves session state
4. Returns response

## Development Guidelines

### Adding a New Command

1. Add command handler in `dispatcher.py::_handle_command()`
2. Return string response (sent to user)
3. Use `pi_manager.list_active()` for process info
4. Use `storage.list_threads()` for stored threads

Example:
```python
elif cmd == "/mycommand":
    result = do_something()
    return f"Result: {result}"
```

### Adding a New Config Option

1. Add field to `config.py::Settings` class
2. Use UPPER_CASE for env var compatibility
3. Add property accessor for snake_case access
4. Document in `.env.example`

Example:
```python
MY_SETTING: str = "default"

@property
def my_setting(self) -> str:
    return self.MY_SETTING
```

### Testing

Tests use `pytest-asyncio` and temporary directories:

```python
@pytest.mark.asyncio
async def test_something(tmp_path: Path):
    workspace = tmp_path / "workspace"
    threads = tmp_path / "threads"
    # ... create dispatcher, test logic
```

Run tests:
```bash
uv run pytest
```

## Common Tasks

### Install in Development Mode
```bash
uv pip install -e ".[dev]"
```

### Type Check
```bash
uv run mypy openclaw_pi/
```

### Lint
```bash
uv run ruff check .
uv run ruff format .
```

### Run Bot
```bash
# With CLI
openclaw-pi

# As module
python -m openclaw_pi
```

## Important Notes

- **Workspace is gitignored** — Never commit user context files
- **Threads are JSON files** — Human-readable, editable
- **Pi runs per-message** — Not a persistent daemon per thread
- **Sessions are separate** — Pi session files != Thread storage files
- **Signal handling** — SIGINT/SIGTERM gracefully shuts down all processes
