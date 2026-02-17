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

## License

MIT License - See LICENSE for details.
