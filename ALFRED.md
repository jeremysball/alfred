# Alfred — Model Documentation

Telegram bot interface for Pi coding agent. One-shot subprocess per message with persistent thread history.

## Architecture

```
Telegram Bot → Dispatcher → Pi Manager → Pi Subprocess (one-shot)
                    ↓
            Thread Storage (JSON)
```

| File | Purpose |
|------|---------|
| `telegram_bot.py` | Telegram handlers + CommandHandler |
| `dispatcher.py` | Message routing, sub-agent spawning |
| `pi_manager.py` | One-shot Pi subprocess lifecycle |
| `storage.py` | Thread persistence (JSON) |
| `config.py` | Settings (pydantic) |

## Key Concept: One-Shot Processes

- **No persistent Pi processes** — Fresh subprocess spawned per message
- **Thread history** = JSON files in `threads/` (persisted conversation)
- **Active tracking** = In-memory set of threads with pending operations

## Message Lifecycle

1. Extract `thread_id`
2. Load thread history from JSON
3. Spawn new Pi subprocess with context
4. Send message, capture response
5. Process exits, save updated history

## Pi Subprocess

Pi runs as one-shot subprocess per message:

```
pi --print --provider zai --session <file> --model <model> "message"
```

- `--print`: Output to stdout
- `--session`: Load/save conversation context
- Message passed as final argument

## Commands

Telegram CommandHandler commands:

| Command | Description |
|---------|-------------|
| `/status` | Active threads + stored threads |
| `/threads` | List all threads |
| `/kill <id>` | Remove thread from active set |
| `/cleanup` | Clear all active threads |
| `/subagent <task>` | Spawn background sub-agent |

## Sub-agents

Background tasks spawned via `/subagent <task>`:

1. Create isolated workspace: `workspace/subagents/<subagent_id>/`
2. Spawn new Pi subprocess
3. Run task, save result
4. Update parent thread
5. Cleanup workspace

## Development

```bash
uv pip install -e ".[dev]"
uv run pytest
uv run mypy alfred/
alfred
```

## Key Points

- One Pi subprocess per message (exits after response)
- Thread history persists in JSON files
- Sub-agents are separate one-shot processes in isolated workspaces
- SIGINT/SIGTERM shuts down gracefully
