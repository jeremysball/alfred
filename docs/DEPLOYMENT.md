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
git clone <repository-url>
cd alfred

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Configure application
cp config.example.json config.json
# Edit config.json as needed

# Run tests
uv run pytest

# Start application
uv run python -m alfred
```

## Environment Configuration

### Required Environment Variables

Create `.env` file:

```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# OpenAI
OPENAI_API_KEY=your_openai_key

# Kimi (Moonshot AI)
KIMI_API_KEY=your_kimi_key
KIMI_BASE_URL=https://api.moonshot.cn/v1
```

### Application Configuration

Create `config.json`:

```json
{
  "default_llm_provider": "kimi",
  "chat_model": "kimi-k2-0711-preview",
  "embedding_model": "text-embedding-3-small",
  "memory_context_limit": 10,
  "memory_dir": "./memory",
  "context_files": {
    "agents": "./AGENTS.md",
    "soul": "./SOUL.md",
    "user": "./USER.md",
    "tools": "./TOOLS.md"
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
  -v $(pwd)/memory:/app/memory \
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

# Required for Alfred (see Environment Configuration above)
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

**docker-compose.yml Overview:**

- Runs Alfred in an isolated container with Tailscale networking
- Mounts local `workspace` and `home` directories for persistence
- Configures Git with GPG signing support
- Uses host user's UID/GID for file permission compatibility

See `docker-compose.yml` for complete configuration.

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
        - name: memory
          mountPath: /app/memory
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
      - name: memory
        persistentVolumeClaim:
          claimName: alfred-memory
```

## Release Process

### Version Numbering

Follows [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH`
- Example: `0.1.0`

### Release Checklist

Before releasing:

- [ ] All tests pass (`uv run pytest`)
- [ ] Type checks pass (`uv run mypy src/`)
- [ ] Linting passes (`uv run ruff check src/`)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped in `pyproject.toml`

### Creating a Release

```bash
# 1. Update version in pyproject.toml
# 2. Update CHANGELOG.md
# 3. Commit changes
git add pyproject.toml CHANGELOG.md
git commit -m "chore(release): bump version to 0.2.0"

# 4. Create tag
git tag -a v0.2.0 -m "Release version 0.2.0"

# 5. Push
git push origin main
git push origin v0.2.0

# 6. Build distribution
uv build

# 7. Publish (if public package)
uv publish
```

### Automated Releases

Using GitHub Actions:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
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
      
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/*
          generate_release_notes: true
```

## Monitoring

### Health Check

Future implementation:

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "memory_usage": get_memory_usage(),
        "last_message": get_last_message_time(),
    }
```

### Logging

Configure logging level via environment:

```bash
# Debug logging
LOG_LEVEL=DEBUG uv run python -m alfred

# Production logging
LOG_LEVEL=INFO uv run python -m alfred
```

### Metrics (Future)

Planned metrics:
- Messages per minute
- Response latency
- Error rate
- Memory usage
- Active users

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
# Check Kimi/OpenAI usage
curl -s "https://api.moonshot.cn/v1/usage" \
  -H "Authorization: Bearer $KIMI_API_KEY"
```

**Memory issues:**
```bash
# Check memory directory
ls -la memory/

# Clear cache (restart required)
rm -rf memory/cache/*
```

### Debug Mode

```bash
# Enable debug logging
LOG_LEVEL=DEBUG uv run python -m alfred

# Or in Docker
docker run -e LOG_LEVEL=DEBUG alfred:latest
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
