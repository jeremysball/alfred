# Alfred

Chat with Pi on Telegram. AI coding help in your group chats.

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code style](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## Features

- **Persistent daemon** — Alfred runs continuously, ready to respond
- **One-shot Pi** — Fresh AI process for every message
- **Multi-thread** — Isolated conversation history per Telegram thread
- **Persistent memory** — Thread history survives restarts (JSON storage)
- **Typing indicator** — Real-time feedback while processing
- **Table rendering** — Markdown tables sent as images (auto-setup)
- **Multi-provider** — Z.AI, Moonshot, others

## Quick Start

**Prerequisites:** Node.js 18+, Python 3.11+

**Install:**

```bash
# Install Pi
npm install -g @mariozechner/pi-coding-agent

# Clone repo
git clone <url>
cd alfred

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
alfred
# or
python -m alfred
```

## Architecture

```
Telegram Bot → Dispatcher → Pi Manager → Pi Subprocess (one-shot)
                    ↓
            Thread Storage (JSON)
```

| File | Purpose |
|------|---------|
| `telegram_bot.py` | Telegram handlers |
| `dispatcher.py` | Message routing |
| `pi_manager.py` | One-shot Pi subprocess management |
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
alfred/            # Main package
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
# Tests (mock-based, fast)
uv run pytest tests/test_dispatcher_commands.py -v

# Type check
uv run mypy alfred/

# Lint
uv run ruff check .
uv run ruff format .
```

### Testing

**Unit tests** (mocked, fast, no API calls):
```bash
uv run pytest tests/test_dispatcher_commands.py tests/test_pi_subprocess.py -v
```

**True E2E tests** (real Telegram + Pi + LLM):
```bash
# Requires env vars and costs real API tokens
export TELEGRAM_BOT_TOKEN=your_bot_token
export TELEGRAM_CHAT_ID=your_chat_id
export LLM_API_KEY=your_llm_key

uv run pytest tests/test_e2e_real.py -v --run-slow
```

E2E tests send real Telegram messages and make real LLM API calls. Use for final validation only.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | — | **Required.** Bot token |
| `LLM_API_KEY` | — | **Required.** API key |
| `PI_PATH` | `./node_modules/.bin/pi` | Pi executable path |
| `WORKSPACE_DIR` | `./workspace` | Workspace path |
| `THREADS_DIR` | `./threads` | Thread storage |
| `SKILLS_DIRS` | — | Comma-separated skill directories for Pi |
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
