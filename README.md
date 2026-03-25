# Alfred

<p align="center">
  <img src="docs/assets/memory-moth-banner.png" alt="Alfred - The Rememberer" width="100%">
</p>

<p align="center">
  <strong>Alfred remembers so you don't have to</strong>
</p>

<p align="center">
  <a href="https://github.com/jeremysball/alfred/actions/workflows/ci.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/jeremysball/alfred/ci.yml?branch=main&label=tests&style=flat-square" alt="Tests">
  </a>
  <a href="https://github.com/jeremysball/alfred/releases">
    <img src="https://img.shields.io/github/v/release/jeremysball/alfred?style=flat-square" alt="Version">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square" alt="License">
  </a>
  <a href="https://pypi.org/project/alfred-assistant/">
    <img src="https://img.shields.io/pypi/v/alfred-assistant?style=flat-square" alt="PyPI">
  </a>
</p>

---

Alfred is a persistent memory system for LLMs. He stores your conversations locally, searches them semantically, and injects relevant context into prompts automatically. Chat via Telegram or CLI.

## Quick Start

```bash
pip install alfred-assistant

# Set up environment
export TELEGRAM_BOT_TOKEN=your_token
export OPENAI_API_KEY=your_key
export KIMI_API_KEY=your_key
export KIMI_BASE_URL=https://api.kimi.com/coding/v1

# Start chatting
alfred
```

On first run, Alfred creates default context files in `data/` from built-in templates.

## What It Does

LLMs forget everything when you close the chat. Alfred solves this by:

1. **Remembering** what matters — Alfred uses the `remember` tool to store important facts (90-day TTL, permanent option)
2. **Searching** semantically — Find relevant memories via `search_memories`
3. **Recalling** conversations — Search full session history via `search_sessions`
4. **Context** across conversations — Session history maintains multi-turn dialogue

**Three storage mechanisms:** Files (always loaded, durable), Memories (curated, 90-day TTL), and Session Archive (automatic, searchable). See [docs/ROADMAP.md](docs/ROADMAP.md) for architecture details.

All local. No cloud. Your data stays in files you control.

## Features

- **Persistent Memory** — JSONL files with OpenAI embeddings
- **Semantic Search** — Find relevant context instantly
- **Web Interface** — Modern browser-based chat with real-time streaming
- **Telegram Bot** — Chat anywhere
- **CLI** — Terminal interface with streaming
- **Scheduled Jobs** — "Remind me every morning at 8am"
- **File Tools** — Read, write, edit, bash execution
- **Human Approval** — Jobs require approval before running
- **Auto-Setup** — Templates copy to `data/` on first run

## CLI Commands

```bash
alfred                   # Start interactive chat
alfred --telegram        # Run as Telegram bot
alfred --log info        # Enable Alfred/core info logging
alfred webui             # Start web interface
alfred webui --log debug # Enable Web UI-specific debug logging
alfred cron list         # List scheduled jobs
alfred cron submit       # Submit a new job
alfred memory migrate    # Convert JSONL memories to FAISS
alfred memory status     # Show memory store info
```

## Web Interface

Alfred includes a modern web-based interface as an alternative to the terminal UI. The Web UI provides the same persistent memory and streaming responses through a browser-based chat experience.

### Starting the Web UI

```bash
# Start Web UI with defaults (localhost:8080)
alfred webui

# Custom port
alfred webui --port 3000

# Custom host (0.0.0.0 for LAN access)
alfred webui --host 0.0.0.0 --port 8080

# Auto-open browser
alfred webui --open
```

### Logging

The root `--log` flag and the Web UI `--log` flag are separate.

```bash
# Alfred/core logging only
alfred --log debug webui

# Web UI logging only
alfred webui --log debug

# Enable both
alfred --log debug webui --log debug
```

**Important:** root options go before the subcommand, and Web UI options go after `webui`.

When logging is enabled, console output uses surface prefixes such as `[core]`, `[webui-server]`, `[webui-client]`, `[llm]`, `[tools]`, and `[storage]` so live streams are easy to scan. In a TTY those prefixes are colorized; in non-TTY output and log files they stay plain, and file logs include `surface=...` fields so they stay grep-friendly.

### Web UI Features

- **Real-time streaming** — Watch responses appear token-by-token
- **Persistent sessions** — Conversations survive page refreshes
- **Session management** — Create, list, and resume sessions with `/new`, `/sessions`, `/resume`
- **Markdown rendering** — Full markdown support with syntax highlighting
- **Reasoning display** — Collapsible reasoning blocks for supported models
- **Tool call visualization** — Expandable tool execution details
- **Status bar** — Live token counts and model information
- **Toast notifications** — Success, error, and info messages
- **Dark/light themes** — Automatic system preference detection
- **Keyboard shortcuts** — `Ctrl+Enter` to send, `Escape` to cancel

### Web UI Architecture

The Web UI is built with modern web technologies:

- **Backend:** FastAPI with WebSocket support
- **Frontend:** Vanilla JavaScript with Web Components
- **Styling:** CSS custom properties for theming
- **Communication:** WebSocket protocol with JSON messages

See [docs/websocket-protocol.md](docs/websocket-protocol.md) for the complete WebSocket protocol specification.

## Data Storage

```
data/
├── memory/
│   └── memories.jsonl      # Curated facts Alfred remembers (90-day TTL)
├── sessions/               # Full conversation archive (searchable)
│   └── {session_id}/
│       ├── messages.jsonl
│       └── summary.json
├── cron.jsonl              # Scheduled jobs
├── cron_history.jsonl      # Job execution history
├── cron_logs.jsonl         # Job output logs
├── SYSTEM.md               # Memory system architecture + cron capabilities
├── AGENTS.md               # Minimal behavior rules (references prompts/)
├── USER.md                 # User preferences (may reference prompts/)
├── SOUL.md                 # Alfred's personality (may reference prompts/)
└── prompts/                # Modular prompt components
    ├── communication-style.md
    ├── voice.md
    └── memory-guidance.md
```

**Modular Prompts:** Files can include other files using `{{prompts/file.md}}` placeholders. This keeps core files minimal while allowing rich, reusable prompt components.

## Configuration

Environment variables (required):

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token |
| `KIMI_API_KEY` | Kimi API key |
| `KIMI_BASE_URL` | Kimi API endpoint |

Optional:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | Required when using OpenAI embeddings; not needed for local BGE |
| `DEFAULT_LLM_PROVIDER` | `kimi` | LLM provider |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model (ignored when using local) |
| `CHAT_MODEL` | `kimi-k2-5` | Chat model |
| `MEMORY_CONTEXT_LIMIT` | `20` | Max memories in context |

**System requirements for local embeddings (BGE):** ~4 GB RAM, ~2 GB disk (model download on first use).

For TOML-based configuration (`~/.config/alfred/config.toml`), see [docs/EMBEDDINGS.md](docs/EMBEDDINGS.md).

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — System design and components
- [API Reference](docs/API.md) — Module documentation
- [Deployment](docs/DEPLOYMENT.md) — Production setup
- [Cron Jobs](docs/cron-jobs.md) — Scheduled tasks
- [Embeddings and FAISS](docs/EMBEDDINGS.md) — Local embeddings, migration, performance tuning
- [Memory System](docs/MEMORY.md) — Three-layer memory architecture
- [Self-Model & Introspection](docs/self-model.md) — Alfred's internal self-awareness and `/context` command
- [Template Sync and Conflict Recovery](docs/template-sync.md) — Conflict-recovery reference for template drift and manual repair
- [WebSocket Protocol](docs/websocket-protocol.md) — Web UI real-time communication spec
- [Roadmap](docs/ROADMAP.md) — Development progress

## Contributing

### Development Setup

1. **Clone and install dependencies:**
   ```bash
   git clone https://github.com/jeremysball/alfred.git
   cd alfred
   uv sync
   ```

2. **Install git hooks:**
   ```bash
   git config core.hooksPath .githooks
   ```

3. **Run quality checks:**
   ```bash
   uv run ruff check src/
   uv run ruff format src/
   uv run mypy src/
   uv run pytest
   ```

### Terminal Tool Development

The terminal tool (`.pi/extensions/terminal.ts`) enables E2E testing of Alfred's TUI. To use it:

1. **Install VHS:**
   ```bash
   # Requires Go
   go install github.com/charmbracelet/vhs@latest
   
   # Add to PATH (if not already)
   export PATH="$PATH:$(go env GOPATH)/bin"
   ```

2. **Install ttyd and ffmpeg** (VHS dependencies):
   ```bash
   # Arch Linux
   sudo pacman -S ttyd ffmpeg
   
   # macOS
   brew install ttyd ffmpeg
   
   # Ubuntu/Debian
   sudo apt install ttyd ffmpeg
   ```

3. **Set environment for containers:**
   ```bash
   export VHS_NO_SANDBOX=true
   ```

4. **Test the extension:**
   ```bash
   pi --no-session -e .pi/extensions/terminal.ts -p "test terminal tool"
   ```

## Community

- [GitHub Discussions](https://github.com/jeremysball/alfred/discussions)
- [GitHub Issues](https://github.com/jeremysball/alfred/issues)

## License

MIT

---

<p align="center">Made with ❤️ and 🧠</p>
