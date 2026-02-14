# OpenClaw Dispatcher

Python dispatcher for OpenClaw Pi with Telegram thread support, streaming responses, and first-class sub-agents.

## Quick Start

```bash
# 1. Install
pip install -e .

# 2. Configure
cp .env.example .env
# Edit .env with your TELEGRAM_BOT_TOKEN and LLM_API_KEY

# 3. Run
python -m dispatcher.main
```

## Architecture

```
Telegram → Dispatcher → pi subprocess → LLM Provider (ZAI/Moonshot)
                           ↓
                     Sub-agents (isolated)
```

- **Single Python process** — asyncio event loop
- **Telegram threads** — Same agent, different conversation contexts
- **Streaming + typing indicator** — Real-time response updates
- **Sub-agents** — Isolated workspaces for parallel tasks
- **Fault isolation** — Timeouts on all pi calls, never blocks

## Configuration

```bash
# .env
TELEGRAM_BOT_TOKEN=xxx

# LLM Provider (passed to pi)
LLM_PROVIDER=zai          # zai or moonshot
LLM_API_KEY=xxx
LLM_MODEL=                # optional override

# Paths
WORKSPACE_DIR=./workspace
THREADS_DIR=./threads

# Limits
PI_TIMEOUT=300
MAX_THREADS=50
```

## Commands

| Command | Description |
|---------|-------------|
| `/status` | Show active threads |
| `/threads` | List all stored threads |
| `/kill <id>` | Kill a thread's pi process |
| `/cleanup` | Kill all processes |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check dispatcher/
```

## Status

- [x] Project structure (pyproject.toml)
- [x] Configuration (pydantic-settings)
- [x] Thread model + JSON storage
- [x] Pi agent manager with LLM config
- [x] Dispatcher core with commands
- [x] Telegram bot with streaming + typing
- [x] Sub-agent support
- [x] Integration tests
- [ ] Memory search (semantic/grep)
- [ ] Sub-agent result reporting
- [ ] Model cycling support
