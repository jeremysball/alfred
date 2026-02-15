# OpenClaw Pi

Telegram bot dispatcher for [Pi](https://github.com/mariozechner/pi). Multi-thread, persistent conversations.

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code style](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## Features

- **Multi-thread** — Each Telegram thread runs its own Pi session
- **Persistent** — Thread history survives restarts
- **Typing indicators** — Real-time feedback while processing
- **Multi-provider** — Z.AI, Moonshot, others
- **Commands** — List, kill, cleanup threads

## Quick Start

**Prerequisites:** Node.js 18+, Python 3.11+

**Install:**

```bash
# Install Pi
npm install -g @mariozechner/pi-coding-agent

# Clone repo
git clone <url>
cd openclaw-pi

# Install package
python3 -m venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Set up workspace
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
openclaw-pi
# or
python -m openclaw_pi
```

## Architecture

```
Telegram Bot → Dispatcher → Pi Manager (subprocess)
                    ↓
            Thread Storage (JSON)
```

| File | Purpose |
|------|---------|
| `telegram_bot.py` | Telegram handlers |
| `dispatcher.py` | Message routing |
| `pi_manager.py` | Pi subprocess management |
| `storage.py` | Thread persistence |
| `config.py` | Environment config |

## Commands

| Command | Description |
|---------|-------------|
| `/status` | Active/stored thread counts |
| `/threads` | List thread IDs |
| `/kill <id>` | Kill thread process |
| `/cleanup` | Kill all processes |
| `/help` | Show help |

## Project Structure

```
openclaw_pi/       # Main package
├── telegram_bot.py
├── dispatcher.py
├── pi_manager.py
└── ...

templates/         # Template files
workspace/         # User context (gitignored)
└── skills/        # Skill modules
```

## Development

```bash
# Tests
uv run pytest

# Type check
uv run mypy openclaw_pi/

# Lint
uv run ruff check .
uv run ruff format .
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | — | **Required.** Bot token |
| `LLM_API_KEY` | — | **Required.** API key |
| `PI_PATH` | `./node_modules/.bin/pi` | Pi executable path |
| `WORKSPACE_DIR` | `./workspace` | Workspace path |
| `THREADS_DIR` | `./threads` | Thread storage |
| `LOG_LEVEL` | `INFO` | Log level |
| `LLM_PROVIDER` | `zai` | Provider (zai, moonshot) |
| `LLM_MODEL` | — | Model name |

## Troubleshooting

Set `LOG_LEVEL=DEBUG` for verbose output.

**Pi not found:**
```
npm install -g @mariozechner/pi-coding-agent
# or set PI_PATH
```

**No API key:**
```
export LLM_API_KEY=your_key
# or set ZAI_API_KEY / MOONSHOT_API_KEY
```

## License

MIT
