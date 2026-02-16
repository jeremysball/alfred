# Alfred

<!-- LOGO_PLACEHOLDER -->
<!-- For Gemini Image Generator, use: docs/logo-prompt.txt -->

[![CI](https://github.com/jeremysball/alfred/workflows/CI/badge.svg)](https://github.com/jeremysball/alfred/actions)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code style](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

AI coding assistant on Telegram. Chat with the Pi agent in your group chats.

## Features

- **Persistent threads** — Conversation history survives restarts
- **One-shot Pi** — Fresh AI process for every message  
- **Multi-thread** — Isolated conversations per Telegram thread
- **Streaming** — Real-time response streaming
- **Token tracking** — Session and daily usage stats
- **Heartbeat monitoring** — Health checks via file
- **Markdown support** — Native Telegram entity formatting
- **Multi-provider** — Z.AI, Moonshot, and others

## Quick Start

**Requirements:** Node.js 18+, Python 3.11+

**Install:**

```bash
npm install -g @mariozechner/pi-coding-agent
git clone <url>
cd alfred
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp -r templates/* workspace/
```

**Configure:**

Create `.env`:

```env
TELEGRAM_BOT_TOKEN=your_token
LLM_API_KEY=your_key
```

**Run:**

```bash
alfred
```

## Commands

| Command | Description |
|---------|-------------|
| `/status` | System status, tokens, threads |
| `/threads` | List all threads |
| `/tokens` | Token usage statistics |
| `/kill <id>` | Terminate a thread |
| `/cleanup` | Kill all processes |
| `/compact` | Compact memory files |
| `/verbose` | Toggle debug logging |
| `/subagent` | Spawn background agent |

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed design.

```
Telegram Bot → Dispatcher → Pi Manager → Pi Subprocess
                     ↓
             Thread Storage (JSON)
```

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | — | **Required.** Bot token |
| `LLM_API_KEY` | — | **Required.** API key |
| `LLM_PROVIDER` | `zai` | Provider (zai, moonshot) |
| `LLM_MODEL` | — | Model name |
| `PI_PATH` | `/usr/bin/pi` | Pi executable |
| `WORKSPACE_DIR` | `./workspace` | Workspace path |
| `THREADS_DIR` | `./threads` | Thread storage |
| `SKILLS_DIRS` | — | Comma-separated skill directories |
| `LOG_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR |

## Development

```bash
# Test
pytest tests/test_dispatcher_commands.py -v

# Type check
mypy alfred/

# Lint
ruff check .
ruff format .
```

## License

MIT
