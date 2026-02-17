# PRD: M1 - Project Setup

## Overview

**Issue**: #11  
**Parent**: #10 (Alfred - The Rememberer)  
**Status**: Planning  
**Priority**: High  
**Created**: 2026-02-16

Set up project infrastructure with uv, mypy, ruff, pytest, and pre-commit hooks. Import assets from jeremysball/alfred repository.

---

## Problem Statement

Alfred needs a solid Python foundation with modern tooling: type safety (mypy), code quality (ruff), testing (pytest), and git hooks (pre-commit). We also need to extract banner/logo assets from the existing repository.

---

## Solution

Create a clean Python project with:
- `uv` for package management
- `mypy` in strict mode
- `ruff` for linting and formatting
- `pytest` for testing
- `pre-commit` hooks
- Assets from existing repo

---

## Acceptance Criteria

- [ ] `pyproject.toml` with all dependencies
- [ ] `uv.lock` generated
- [ ] `src/` directory (flat, not `src/alfred/`)
- [ ] `tests/` directory
- [ ] `docs/assets/` with banner and logo from existing repo
- [ ] `.env.example` file
- [ ] `README.md` skeleton
- [ ] Pre-commit hooks for ruff and pytest
- [ ] All configs in `pyproject.toml` (no setup.cfg, no setup.py)
- [ ] `.gitignore` for Python projects

---

## File Structure

```
alfred/
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── README.md
├── pyproject.toml
├── uv.lock
├── docs/
│   └── assets/
│       ├── memory-moth-banner.png
│       ├── memory-moth-logo.png
│       └── kimi-k25-pfp.png
├── src/
│   └── __init__.py
└── tests/
    └── __init__.py
```

---

## pyproject.toml

```toml
[project]
name = "alfred"
version = "0.1.0"
description = "The Rememberer - A persistent memory-augmented LLM assistant"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "python-telegram-bot>=21.0",
    "openai>=1.0",
    "numpy>=1.24",
    "pydantic>=2.0",
    "python-dotenv>=1.0",
    "aiofiles>=23.0",
    "tiktoken>=0.5",
    "aiohttp>=3.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=4.0",
    "mypy>=1.8",
    "ruff>=0.2",
    "pre-commit>=3.6",
    "respx>=0.21",
    "pytest-mock>=3.12",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
target-version = "py312"
line-length = 100
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]
ignore = []

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
show_error_codes = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "--cov=src --cov-report=term-missing"

[tool.coverage.run]
source = ["src"]
omit = ["*/tests/*"]

[tool.hatch.build.targets.wheel]
packages = ["src"]
```

---

## .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.2.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: uv run pytest -x
        language: system
        types: [python]
        pass_filenames: false
        always_run: false
```

---

## .env.example

```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here

# OpenAI (for embeddings)
OPENAI_API_KEY=your_openai_key_here

# Kimi (primary LLM)
KIMI_API_KEY=your_kimi_key_here
KIMI_BASE_URL=https://api.moonshot.cn/v1

# Optional
DEFAULT_LLM_PROVIDER=kimi
EMBEDDING_MODEL=text-embedding-3-small
CHAT_MODEL=kimi-k2-5
MEMORY_CONTEXT_LIMIT=20
```

---

## Asset Import

From `github.com/jeremysball/alfred`, copy:
- `docs/assets/memory-moth-banner.png`
- `docs/assets/memory-moth-logo.png`
- `docs/assets/kimi-k25-pfp.png` (optional)

Do not copy any code. Start fresh.

---

## Git Repository Setup

After creating files:

```bash
# Remove old commits and start fresh
git checkout --orphan main-new
git add -A
git commit -m "feat(m1): initialize project structure

- Add pyproject.toml with uv, mypy, ruff, pytest
- Setup pre-commit hooks for ruff and pytest
- Import assets from existing repo
- Add .env.example and README skeleton"
git branch -D main
git branch -m main
```

---

## Success Criteria

- [ ] `uv sync` runs without errors
- [ ] `uv run python -c "import src"` succeeds
- [ ] `uv run ruff check src/` passes
- [ ] `uv run mypy src/` passes
- [ ] `uv run pytest` runs (no tests yet, but command works)
- [ ] `pre-commit install` works
- [ ] Assets display correctly
