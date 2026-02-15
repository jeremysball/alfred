# OpenClaw Pi

> A Telegram bot dispatcher for the [Pi coding agent](https://github.com/mariozechner/pi), enabling persistent multi-thread conversations with AI-assisted software development.

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code style](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## Features

- **Multi-thread Support** — Each Telegram thread gets its own isolated Pi session
- **Persistent Conversations** — Thread history survives restarts
- **Streaming Responses** — Real-time typing indicators and progressive responses
- **Multiple LLM Providers** — Supports Z.AI, Moonshot, and other providers
- **Session Management** — List, kill, and cleanup active threads via commands
- **Skills Integration** — Extensible skill system for specialized capabilities

## Quick Start

### Prerequisites

1. **Node.js 18+** — Required for the Pi coding agent
2. **Python 3.11+** — Required for the dispatcher
3. **uv** (recommended) or **pip** — Python package manager

### Installation

#### 1. Install Pi Coding Agent

```bash
# Install globally via npm
npm install -g @mariozechner/pi-coding-agent

# Verify installation
pi --version
```

#### 2. Clone and Install OpenClaw Pi

```bash
# Clone the repository
git clone <repository-url>
cd openclaw-pi

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with uv (recommended)
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"
```

#### 3. Set Up Workspace

```bash
# Copy templates to workspace
cp -r templates/* workspace/

# Customize your agent context
# Edit: workspace/AGENTS.md, workspace/SOUL.md, workspace/USER.md
```

### Configuration

Create a `.env` file in the project root:

```env
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here

# LLM Provider (default: zai)
LLM_PROVIDER=zai
LLM_API_KEY=your_api_key_here
LLM_MODEL=glm-4-flash

# Optional
LOG_LEVEL=INFO
PI_TIMEOUT=300
MAX_THREADS=50
```

### Running

```bash
# Run the bot
openclaw-pi

# Or as a module
python -m openclaw_pi
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Telegram Bot   │────▶│   Dispatcher    │────▶│   Pi Manager    │
│  (asyncio)      │     │   (routing)     │     │   (subprocess)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  Thread Storage │
                       │  (JSON files)   │
                       └─────────────────┘
```

### Components

| Component | Purpose |
|-----------|---------|
| `telegram_bot.py` | Telegram Bot API integration, message handlers |
| `dispatcher.py` | Routes messages, manages thread lifecycle |
| `pi_manager.py` | Spawns and manages Pi subprocesses per thread |
| `storage.py` | Persistent thread state (JSON) |
| `config.py` | Environment-based configuration (pydantic-settings) |

## Commands

Users can interact with the bot using these commands:

| Command | Description |
|---------|-------------|
| `/start` | Show welcome message and available commands |
| `/status` | Show active and stored thread counts |
| `/threads` | List all stored thread IDs |
| `/kill <id>` | Terminate a specific thread's Pi process |
| `/cleanup` | Kill all active Pi processes |
| `/help` | Show help message |

## Project Structure

```
openclaw-pi/
├── openclaw_pi/           # Main Python package
│   ├── __init__.py
│   ├── __main__.py        # Entry point for python -m
│   ├── main.py            # CLI entry point
│   ├── config.py          # Settings management
│   ├── dispatcher.py      # Message routing
│   ├── pi_manager.py      # Subprocess management
│   ├── telegram_bot.py    # Telegram integration
│   ├── storage.py         # Thread persistence
│   ├── models.py          # Data models
│   ├── llm_api.py         # LLM provider interface
│   └── subagent.py        # Subagent support
├── tests/                 # Test suite
├── templates/             # Template files for new workspaces
├── workspace/             # User context (gitignored)
│   ├── AGENTS.md          # Agent configuration
│   ├── SOUL.md            # Personality definition
│   ├── USER.md            # User preferences
│   ├── MEMORY.md          # Long-term memory
│   ├── TOOLS.md           # Tool configuration
│   ├── HEARTBEAT.md       # Periodic tasks
│   └── skills/            # Skill modules
├── pyproject.toml         # Package configuration
└── README.md              # This file
```

## Development

### Testing

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=openclaw_pi
```

### Type Checking

```bash
uv run mypy openclaw_pi/
```

### Linting

```bash
uv run ruff check .
uv run ruff format .
```

## Workspace Configuration

The `workspace/` directory contains user-specific context files:

| File | Purpose |
|------|---------|
| `AGENTS.md` | Agent behavior, conventions, and rules |
| `SOUL.md` | Personality and voice definition |
| `USER.md` | User preferences and context |
| `IDENTITY.md` | Agent identity and self-knowledge |
| `MEMORY.md` | Long-term curated memories |
| `TOOLS.md` | Tool-specific configuration |
| `HEARTBEAT.md` | Periodic task definitions |
| `skills/` | Skill modules for extended capabilities |

**Note:** The `workspace/` directory is gitignored to keep personal context separate from code.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | — | **Required.** Telegram Bot API token |
| `PI_PATH` | `./node_modules/.bin/pi` | Path to Pi executable |
| `WORKSPACE_DIR` | `./workspace` | Path to workspace directory |
| `THREADS_DIR` | `./threads` | Path to thread storage |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `PI_TIMEOUT` | `300` | Pi subprocess timeout (seconds) |
| `LLM_PROVIDER` | `zai` | LLM provider (zai, moonshot, etc.) |
| `LLM_API_KEY` | — | API key for LLM provider |
| `LLM_MODEL` | — | Model identifier |
| `MAX_THREADS` | `50` | Maximum concurrent threads |

## License

MIT License — see [LICENSE](LICENSE) for details.

## Acknowledgments

- [Pi](https://github.com/mariozechner/pi) by Mario Zechner — The underlying coding agent
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) — Telegram Bot API wrapper
