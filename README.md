# Alfred

<p align="center">
  <img src="docs/assets/memory-moth-banner.png" alt="Alfred - AI coding assistant with persistent memory">
</p>

<p align="center">
  <strong>AI coding assistant with persistent memory</strong>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#commands">Commands</a> •
  <a href="#how-it-works">How It Works</a> •
  <a href="#development">Development</a>
</p>

---

## Quick Start (Docker)

**Recommended.** No local dependencies needed.

```bash
git clone <url> && cd alfred
cp .env.example .env
# Edit .env with your TELEGRAM_BOT_TOKEN and LLM_API_KEY
docker compose up -d
```

That's it. Alfred is running.

## Quick Start (Local)

If you prefer running locally:

```bash
# Install Pi (the underlying AI agent)
npm install -g @mariozechner/pi-coding-agent

# Clone and setup
git clone <url> && cd alfred
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Copy templates and configure
cp -r templates/* workspace/
cp .env.example .env
# Edit .env with your tokens

# Run
alfred
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Begin conversation |
| `/status` | System health & stats |
| `/threads` | List active conversations |
| `/compact [prompt]` | Summarize current thread context |
| `/subagent <task>` | Spawn background agent |
| `/tokens` | Token usage statistics |
| `/verbose` | Toggle debug logging |

## How It Works

### Persistent Context

Alfred loads context files on **every message**:

- `AGENTS.md` — Behavior rules
- `SOUL.md` — Personality  
- `USER.md` — Your preferences
- `TOOLS.md` — Local tool configs
- `SKILLS/*` — Available skills

### Memory System

- **Daily capture**: `memory/2026-02-16.md`
- **Long-term**: `MEMORY.md` (curated)
- **Thread isolation**: Each Telegram thread = separate context

### Thread Compaction

Long conversations get expensive. Use `/compact` to summarize:

```
User: /compact
Alfred: ✅ Compacted thread
   42 messages → summary
   ~75% size reduction
```

Optional custom prompt: `/compact Focus on API decisions`

---

## Power Users

### Custom Skills

Add skills to `workspace/skills/`:

```
skills/
├── writing-concisely/
│   ├── SKILL.md
│   └── reference-material.md
└── my-custom-skill/
    └── SKILL.md
```

Skills auto-load on startup. [See skill examples →](docs/SKILLS.md)

### Subagents

Delegate long tasks:

```
/subagent Review all Python files for type hints, 
report which files need updates
```

Runs in background. Results posted when complete.

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | — | From [@BotFather](https://t.me/botfather) |
| `LLM_API_KEY` | — | Your AI provider key |
| `LLM_PROVIDER` | `zai` | `zai`, `openai`, `moonshot` |
| `LLM_MODEL` | — | Model ID (e.g., `gpt-4`) |
| `OPENAI_API_KEY` | — | Enables semantic memory search |
| `WORKSPACE_DIR` | `./workspace` | Context files location |
| `THREADS_DIR` | `./threads` | Conversation storage |

---

## Development

[Architecture Overview →](docs/ARCHITECTURE.md)

[API Reference →](docs/API.md)

### Setup

```bash
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Testing

```bash
pytest tests/ -v
```

### Linting

```bash
ruff check .
ruff format .
mypy alfred/
```

### Project Structure

```
alfred/
├── alfred/           # Core package
│   ├── dispatcher.py # Message routing
│   ├── pi_manager.py # AI subprocess
│   ├── telegram_bot.py
│   └── ...
├── tests/
├── workspace/        # Runtime context (gitignored)
├── templates/        # Starter context files
└── docs/
```

---

## License

MIT
