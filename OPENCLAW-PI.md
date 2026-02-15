# OpenClaw Pi — Model Documentation

Telegram bot dispatcher for Pi coding agent. Persistent Pi processes per thread.

## Architecture

```
Telegram Bot → Dispatcher → Pi Manager → Pi Subprocess (persistent)
                    ↓                         ↓
            Thread Storage (JSON)      Sub-agents (background)
```

| File | Purpose |
|------|---------|
| `telegram_bot.py` | Telegram handlers + CommandHandler |
| `dispatcher.py` | Message routing, sub-agent spawning |
| `pi_manager.py` | Persistent Pi process lifecycle |
| `storage.py` | Thread persistence (JSON) |
| `config.py` | Settings (pydantic) |

## Key Concept: Stored vs Active Threads

- **Stored threads** = JSON files in `threads/` (persisted history)
- **Active threads** = Running Pi processes (spawned lazily)

## Thread Lifecycle

1. Extract `thread_id`
2. Load/create thread JSON
3. **Lazy spawn:** `PiManager.get_or_create()` starts Pi if not running
4. Send message via stdin, read response via stdout
5. Save thread JSON

## Persistent Pi Process

Pi runs as persistent subprocess per thread:

```
pi --provider zai --session <file> --model <model>
```

Protocol:
- Send: `message + "\n\n__END__\n"`
- Read: lines until `__END__`

## Commands

Telegram CommandHandler commands:

| Command | Description |
|---------|-------------|
| `/status` | Active processes + stored threads |
| `/threads` | List all threads (🟢 active, ⚪ stored) |
| `/kill <id>` | Kill thread's Pi process |
| `/cleanup` | Kill all Pi processes |
| `/subagent <task>` | Spawn background sub-agent |

## Sub-agents

Background tasks spawned via `/subagent <task>`:

1. Create isolated workspace: `workspace/subagents/<subagent_id>/`
2. Spawn new Pi process
3. Run task, save result
4. Update parent thread
5. Cleanup process

## Development

```bash
uv pip install -e ".[dev]"
uv run pytest
uv run mypy openclaw_pi/
openclaw-pi
```

## Key Points

- One Pi process per thread (persistent, not one-shot)
- Lazy spawn on first message
- Sub-agents are separate Pi processes in isolated workspaces
- SIGINT/SIGTERM shuts down all processes gracefully
