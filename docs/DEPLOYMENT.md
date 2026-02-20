# Deployment Guide

## Overview

This guide covers deploying Alfred to various environments.

## Local Development

### Prerequisites

- Python 3.12+
- uv (Python package manager)
- Git

### Setup

```bash
# Clone repository
git clone https://github.com/jeremysball/alfred.git
cd alfred

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run tests
uv run pytest

# Start application (CLI mode)
uv run alfred

# Start application (Telegram mode)
uv run alfred --telegram
```

## Environment Configuration

### Required Environment Variables

Create `.env` file:

```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# OpenAI (for embeddings)
OPENAI_API_KEY=your_openai_key

# Kimi (primary LLM)
KIMI_API_KEY=your_kimi_key
KIMI_BASE_URL=https://api.kimi.com/coding/v1
```

### Application Configuration

`config.json` (committed to repo):

```json
{
  "default_llm_provider": "kimi",
  "chat_model": "kimi-k2-5",
  "embedding_model": "text-embedding-3-small",
  "memory_context_limit": 20,
  "workspace_dir": "data",
  "memory_dir": "data/memory",
  "context_files": {
    "agents": "data/AGENTS.md",
    "soul": "data/SOUL.md",
    "user": "data/USER.md",
    "tools": "data/TOOLS.md"
  }
}
```

## Production Deployment

### Docker (Recommended)

The project includes a multi-stage `Dockerfile` that builds a complete development environment.

**Build and run:**

```bash
# Build the image
docker build -t alfred:latest .

# Run with environment file
docker run -d \
  --name alfred \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  alfred:latest
```

**Dockerfile Overview:**

The Dockerfile creates a comprehensive Arch Linux-based environment with:

- **Base:** Arch Linux with multilib support
- **Languages:** Python 3, Node.js 22, Bun
- **Tools:** Git, Neovim (v0.11+), GitHub CLI, uv
- **Browsers:** Playwright (Chromium, Firefox, WebKit)
- **Package Managers:** Homebrew, npm, pnpm, yarn
- **Editor:** LazyVim pre-configured

See `Dockerfile` for complete details.

### Docker Compose (Full Environment)

The project includes a `docker-compose.yml` that sets up Alfred with Tailscale networking.

**Prerequisites:**

1. Create workspace and home directories:
```bash
mkdir -p workspace home
```

2. Set environment variables in `.env`:
```bash
# Required for git commits
GITHUB_TOKEN=your_github_token
GIT_NAME=Your Name
GIT_EMAIL=your@email.com
GIT_GPG_KEY=your_gpg_key_id
GIT_GPG_SIGN=true  # or false

# Required for Alfred
TELEGRAM_BOT_TOKEN=...
KIMI_API_KEY=...
OPENAI_API_KEY=...
```

3. Configure UID/GID (optional, defaults to 1000):
```bash
export UID=$(id -u)
export GID=$(id -g)
```

**Run:**

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f alfred

# Stop services
docker-compose down
```

**Services:**

| Service | Purpose |
|---------|---------|
| `alfred` | Main application container with full dev environment |
| `tailscale` | VPN networking for secure remote access |

**Volumes:**

| Volume | Mount | Purpose |
|--------|-------|---------|
| `workspace` | `./workspace` | Project files and repositories |
| `home` | `./home` | Persistent home directory (Neovim config, cache) |
| `tailscale` | `./volumes/tailscale` | Tailscale state |

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alfred
spec:
  replicas: 1
  selector:
    matchLabels:
      app: alfred
  template:
    metadata:
      labels:
        app: alfred
    spec:
      containers:
      - name: alfred
        image: alfred:latest
        envFrom:
        - secretRef:
            name: alfred-secrets
        volumeMounts:
        - name: config
          mountPath: /app/config.json
          subPath: config.json
        - name: data
          mountPath: /app/data
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: config
        configMap:
          name: alfred-config
      - name: data
        persistentVolumeClaim:
          claimName: alfred-data
```

## Release Process

### Version Numbering

Follows [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH`
- Version is managed via `hatch-vcs` from git tags

### Release Checklist

Before releasing:

- [ ] All tests pass (`uv run pytest`)
- [ ] Type checks pass (`uv run mypy src/`)
- [ ] Linting passes (`uv run ruff check src/`)
- [ ] Documentation updated

### Creating a Release

```bash
# 1. Commit changes
git add .
git commit -m "chore(release): prepare for v0.2.0"

# 2. Create tag
git tag -a v0.2.0 -m "Release version 0.2.0"

# 3. Push
git push origin main
git push origin v0.2.0

# 4. Build distribution
uv build

# 5. Publish to PyPI (trusted publishing configured)
uv publish
```

### Automated Releases

Using GitHub Actions with PyPI trusted publishing:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      id-token: write  # Required for trusted publishing
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install uv
        run: pip install uv
      
      - name: Build
        run: uv build
      
      - name: Publish to PyPI
        run: uv publish
```

## Monitoring

### Logging

Configure logging level via CLI:

```bash
# Debug logging
alfred --debug debug

# Info logging
alfred --debug info

# Default: warnings only
alfred
```

## Troubleshooting

### Common Issues

**Bot not responding:**
```bash
# Check logs
docker logs alfred

# Verify token
curl -s "https://api.telegram.org/bot<TOKEN>/getMe"
```

**Rate limiting:**
```bash
# Wait and retry - Alfred has built-in exponential backoff
```

**Memory issues:**
```bash
# Check memory directory
ls -la data/memory/

# View memory count
wc -l data/memory/memories.jsonl
```

### Debug Mode

```bash
# Enable debug logging
alfred --debug debug

# Or in Docker
docker run -e DEBUG=debug alfred:latest
```

## Security Considerations

1. **Never commit `.env` files**
2. **Use secrets management** in production (Kubernetes secrets, AWS Secrets Manager)
3. **Rotate API keys** regularly
4. **Limit bot permissions** in Telegram
5. **Enable audit logging** for sensitive operations

## Rollback

If a release has issues:

```bash
# Revert to previous version
git revert HEAD
git push origin main

# Or redeploy previous Docker image
docker pull alfred:0.1.0
docker stop alfred
docker run -d --name alfred alfred:0.1.0
```

---

## Related Documentation

- [Architecture](ARCHITECTURE.md) — System design
- [API Reference](API.md) — Module documentation
- [Roadmap](ROADMAP.md) — Development progress
