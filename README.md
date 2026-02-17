# Alfred - The Rememberer

![Memory Moth Banner](docs/assets/memory-moth-banner.png)

Alfred is a persistent memory-augmented LLM assistant. He remembers conversations across sessions and builds a rich understanding of his users over time.

## What Alfred Does

- **Remembers everything**: Every conversation, preference, and detail persists
- **Learns continuously**: Alfred improves his understanding with each interaction
- **Adapts to you**: His personality and responses match your communication style
- **Recalls context**: He brings relevant past conversations into current chats automatically

## Quick Start

### For Users

1. **Install**
   ```bash
   pip install alfred
   ```

2. **Configure**
   ```bash
   export TELEGRAM_BOT_TOKEN=your_token
   export KIMI_API_KEY=your_key
   export OPENAI_API_KEY=your_key
   ```

3. **Run**
   ```bash
   alfred
   ```

### For Developers

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd alfred
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Install pre-commit hooks**
   ```bash
   uv run pre-commit install
   ```

5. **Run tests**
   ```bash
   uv run pytest
   ```

### Using Docker (Full Environment)

The project includes a complete Docker setup with Tailscale networking.

1. **Create directories**
   ```bash
   mkdir -p workspace home
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with API keys and Git config
   ```

3. **Start services**
   ```bash
   docker-compose up -d
   ```

4. **Access the container**
   ```bash
   docker-compose exec alfred bash
   # Inside container:
   alfred
   ```

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed Docker configuration.

## Development

### Code Quality

- **Type checking**: `uv run mypy src/`
- **Linting**: `uv run ruff check src/`
- **Formatting**: `uv run ruff format src/`
- **Tests**: `uv run pytest`

All checks run automatically on commit via pre-commit hooks.

## Template System

Alfred uses templates to auto-create context files on first run. These files define Alfred's personality, user preferences, and environment configuration.

### Available Templates

| Template | Purpose | Location |
|----------|---------|----------|
| **SOUL.md** | Alfred's personality, values, and voice | Core context |
| **USER.md** | User profile, preferences, and context | Core context |
| **TOOLS.md** | LLM preferences and environment notes | Configuration |
| **MEMORY.md** | Curated long-term knowledge | Persistent memory |

### How It Works

1. **Bundled in Docker**: Templates are included at `/app/templates/`
2. **Auto-created**: Missing files are created from templates on startup
3. **User-owned**: Once created, files belong to you — templates won't overwrite

```
/app/templates/     → Template files (read-only, bundled)
/workspace/data/    → Your files (auto-created from templates)
```

### Customizing Templates

After first run, edit files directly in your data directory:

```bash
# Edit Alfred's personality
vim data/SOUL.md

# Add your preferences
vim data/USER.md

# Configure LLM settings
vim data/TOOLS.md
```

**Your customizations persist** — templates only create missing files.

### Template Variables

Templates support variable substitution:

| Variable | Description | Example |
|----------|-------------|---------|
| `{current_date}` | Today's date | `2026-02-17` |
| `{current_year}` | Current year | `2026` |

### Troubleshooting

**Q: File not auto-created?**
- Check template exists in `/app/templates/`
- Verify `workspace_dir` in `config.json` is correct

**Q: Want to reset to defaults?**
- Delete the file and restart Alfred
- Template will recreate on next startup

**Q: Changes not appearing?**
- Context files are cached (60s TTL by default)
- Restart Alfred to reload immediately

## License

MIT License - See LICENSE for details.
