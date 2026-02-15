# OpenClaw Pi — Model Documentation

Telegram bot dispatcher for Pi coding agent. Multi-thread, persistent conversations.

## Architecture

```
Telegram Bot → Dispatcher → Pi Manager → Pi Subprocess
                    ↓
            Thread Storage (JSON)
```

| File | Purpose |
|------|---------|
| `telegram_bot.py` | Telegram handlers |
| `dispatcher.py` | Message routing |
| `pi_manager.py` | Pi subprocess lifecycle |
| `storage.py` | Thread persistence |
| `config.py` | Settings (pydantic) |
| `models.py` | Pydantic models |

## File Locations

**Source:**
```
openclaw_pi/
├── config.py, dispatcher.py, pi_manager.py
├── telegram_bot.py, storage.py, models.py
├── llm_api.py, subagent.py
├── main.py (CLI entry), __main__.py (module entry)
└── __init__.py
```

**Config:** `.env`, `pyproject.toml`

**Runtime (gitignored):**
```
workspace/           # User context
├── AGENTS.md, SOUL.md, USER.md
└── skills/

threads/             # Thread JSON files
memory/              # Daily notes (optional)
```

**Templates:** `templates/` — Bootstrap files

## Configuration

```python
from openclaw_pi.config import Settings
settings = Settings()
```

**Required:** `TELEGRAM_BOT_TOKEN`, `LLM_API_KEY`

**Optional:** `WORKSPACE_DIR`, `THREADS_DIR`, `LOG_LEVEL`, `PI_TIMEOUT`, `LLM_PROVIDER`, `LLM_MODEL`, `MAX_THREADS`

## Thread Lifecycle

1. Extract `thread_id` (`{chat_id}_{thread_id}` or `chat_id`)
2. Load thread from storage (or create)
3. Get `PiSubprocess` from `PiManager`
4. Send to Pi, get response
5. Save thread state
6. Return response

## Commands

Dispatcher handles: `/status`, `/threads`, `/kill <id>`, `/cleanup`, `/help`

Add commands in `dispatcher.py::_handle_command()`:

```python
elif cmd == "/mycommand":
    return f"Result: {do_something()}"
```

## Pi Subprocess

Pi runs in `--print` mode per message:

```bash
pi --print --provider zai --session <file> --model <model> <message>
```

## Add Config Option

```python
# config.py
MY_SETTING: str = "default"

@property
def my_setting(self) -> str:
    return self.MY_SETTING
```

## Development

```bash
uv pip install -e ".[dev]"
uv run pytest
uv run mypy openclaw_pi/
uv run ruff check . && uv run ruff format .
openclaw-pi  # or: python -m openclaw_pi
```

## Key Points

- Workspace gitignored — never commit user files
- Threads are JSON — human-readable
- Pi runs per-message — not persistent per thread
- Pi session files != thread storage files
- SIGINT/SIGTERM shuts down gracefully
