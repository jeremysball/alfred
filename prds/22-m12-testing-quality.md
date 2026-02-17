# PRD: M12 - Testing & Quality

## Overview

**Issue**: #22  
**Parent**: #10 (Alfred - The Rememberer)  
**Depends On**: #21 (M11: Learning)  
**Status**: Planning  
**Priority**: High  
**Created**: 2026-02-16

Create comprehensive test suite with pytest, mypy in strict mode, unit tests with mocks/golden vectors, and integration tests with real API calls.

---

## Problem Statement

Alfred needs reliable testing. Fast unit tests with mocks. Slow integration tests with real APIs. Strict type checking. Golden vectors for embedding tests to avoid costs.

---

## Solution

Create testing infrastructure:
1. Unit tests with mocks for speed
2. Integration tests with real APIs
3. Golden vectors for deterministic embedding tests
4. mypy strict mode enforcement
5. ruff for linting and formatting
6. Pre-commit hooks for quality

---

## Acceptance Criteria

- [ ] Unit tests for all core modules
- [ ] Integration tests for API-dependent modules
- [ ] Golden vector fixtures for embeddings
- [ ] mypy strict mode passes
- [ ] ruff formatting and linting passes
- [ ] Pre-commit hooks configured
- [ ] 80%+ code coverage

---

## File Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_config.py           # Config tests
├── test_context.py          # Context loader tests
├── test_embeddings.py       # Embedding tests (golden vectors)
├── test_memory.py           # Memory store tests
├── test_search.py           # Vector search tests
├── test_bot.py              # Bot handler tests (mocked)
├── test_llm.py              # LLM provider tests
├── test_personality.py      # Personality tests
├── test_capabilities.py     # Capabilities tests
├── test_compaction.py       # Compaction tests
├── test_distillation.py     # Distillation tests
├── test_learning.py         # Learning system tests
└── integration/
    ├── __init__.py
    ├── test_openai.py       # Real OpenAI API tests
    ├── test_kimi.py         # Real Kimi API tests
    └── test_end_to_end.py   # Full conversation tests
```

---

## conftest.py (Shared Fixtures)

```python
import pytest
import numpy as np
from pathlib import Path
from src.config import Config


@pytest.fixture
def mock_config(tmp_path):
    """Create config with temp directories."""
    return Config(
        telegram_bot_token="test_token",
        openai_api_key="test_openai_key",
        kimi_api_key="test_kimi_key",
        kimi_base_url="https://api.moonshot.cn/v1",
        memory_dir=tmp_path / "memory",
    )


@pytest.fixture
def golden_vector():
    """Return deterministic embedding vector for testing."""
    # 1536-dimensional vector (OpenAI embedding size)
    np.random.seed(42)
    vec = np.random.randn(1536)
    return (vec / np.linalg.norm(vec)).tolist()


@pytest.fixture
def golden_vectors_batch():
    """Return batch of deterministic vectors."""
    np.random.seed(42)
    vectors = []
    for i in range(10):
        np.random.seed(42 + i)
        vec = np.random.randn(1536)
        vectors.append((vec / np.linalg.norm(vec)).tolist())
    return vectors


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI embedding response."""
    class MockResponse:
        def __init__(self):
            self.data = [MockEmbeddingData()]
    
    class MockEmbeddingData:
        def __init__(self):
            np.random.seed(42)
            vec = np.random.randn(1536)
            self.embedding = (vec / np.linalg.norm(vec)).tolist()
    
    return MockResponse()


@pytest.fixture
def temp_memory_dir(tmp_path):
    """Create temporary memory directory."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    return memory_dir


@pytest.fixture
def sample_agents_md():
    """Sample AGENTS.md content."""
    return """# Agent Behavior Rules

## Core Principles
1. Always ask before editing files
2. Be concise
"""


@pytest.fixture
def sample_soul_md():
    """Sample SOUL.md content."""
    return """# Alfred

## Personality
You are Alfred, a helpful assistant.

## Traits
- Warm
- Concise
"""


@pytest.fixture
def sample_user_md():
    """Sample USER.md content."""
    return """# User Profile

## Background
Software developer

## Preferences
- Response style: concise
"""
```

---

## Unit Test Example (test_embeddings.py)

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.embeddings import EmbeddingClient


@pytest.mark.asyncio
async def test_embed_uses_openai(mock_config, golden_vector):
    client = EmbeddingClient(mock_config)
    
    # Mock OpenAI client
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=golden_vector)]
    
    client.client = MagicMock()
    client.client.embeddings.create = AsyncMock(return_value=mock_response)
    
    result = await client.embed("test text")
    
    assert result == golden_vector
    assert len(result) == 1536


@pytest.mark.asyncio
async def test_embed_batch_uses_openai(mock_config, golden_vectors_batch):
    client = EmbeddingClient(mock_config)
    
    # Mock batch response
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=vec) for vec in golden_vectors_batch[:3]
    ]
    
    client.client = MagicMock()
    client.client.embeddings.create = AsyncMock(return_value=mock_response)
    
    texts = ["text1", "text2", "text3"]
    results = await client.embed_batch(texts)
    
    assert len(results) == 3
    assert all(len(vec) == 1536 for vec in results)
```

---

## Integration Test Example (integration/test_openai.py)

```python
import pytest
from src.embeddings import EmbeddingClient
from src.config import Config
import os


@pytest.fixture
def real_config():
    """Config with real API keys."""
    return Config(
        telegram_bot_token="test",
        openai_api_key=os.environ["OPENAI_API_KEY"],
        kimi_api_key="test",
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_openai_embedding(real_config):
    """Test with real OpenAI API."""
    client = EmbeddingClient(real_config)
    
    result = await client.embed("This is a test sentence.")
    
    assert len(result) == 1536
    assert all(isinstance(x, float) for x in result)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_openai_embedding_similarity(real_config):
    """Test that similar texts have similar embeddings."""
    client = EmbeddingClient(real_config)
    
    vec1 = await client.embed("I love Python programming")
    vec2 = await client.embed("Python is my favorite language")
    vec3 = await client.embed("The weather is nice today")
    
    # Calculate similarities
    import numpy as np
    
    def cosine(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    sim_similar = cosine(vec1, vec2)
    sim_different = cosine(vec1, vec3)
    
    assert sim_similar > sim_different
```

---

## pytest Configuration

```toml
# In pyproject.toml [tool.pytest.ini_options]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--strict-config",
    "--verbose",
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-report=html:htmlcov",
    "--cov-fail-under=80",
]
markers = [
    "integration: marks tests that use real APIs (slow, expensive)",
    "slow: marks tests that are slow but don't use APIs",
]
```

---

## Running Tests

```bash
# Run unit tests only (fast, no API calls)
uv run pytest -m "not integration"

# Run integration tests (slow, uses real APIs)
uv run pytest -m integration

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_embeddings.py -v
```

---

## Type Checking

```bash
# Run mypy strict
uv run mypy src/ --strict

# Check specific file
uv run mypy src/embeddings.py --strict
```

---

## Linting and Formatting

```bash
# Check formatting
uv run ruff check src/

# Auto-fix issues
uv run ruff check src/ --fix

# Format code
uv run ruff format src/
```

---

## Pre-commit Hooks

```yaml
# .pre-commit-config.yaml

repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.2.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: local
    hooks:
      - id: mypy
        name: mypy
        entry: uv run mypy src/ --strict
        language: system
        types: [python]
        pass_filenames: false

      - id: pytest-unit
        name: pytest-unit
        entry: uv run pytest -m "not integration" -x
        language: system
        types: [python]
        pass_filenames: false
        stages: [commit]
```

---

## CI/CD (GitHub Actions)

```yaml
# .github/workflows/test.yml

name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        run: pip install uv
      
      - name: Setup Python
        run: uv venv
      
      - name: Install dependencies
        run: uv sync
      
      - name: Run linting
        run: uv run ruff check src/
      
      - name: Run type checking
        run: uv run mypy src/ --strict
      
      - name: Run unit tests
        run: uv run pytest -m "not integration"

  integration:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        run: pip install uv
      
      - name: Setup Python
        run: uv venv
      
      - name: Install dependencies
        run: uv sync
      
      - name: Run integration tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          KIMI_API_KEY: ${{ secrets.KIMI_API_KEY }}
        run: uv run pytest -m integration
```

---

## Success Criteria

- [ ] Unit tests cover all modules
- [ ] Integration tests for OpenAI and Kimi
- [ ] Golden vectors used for embedding tests
- [ ] mypy strict mode passes on all files
- [ ] ruff formatting and linting passes
- [ ] Pre-commit hooks run successfully
- [ ] Code coverage exceeds 80%
- [ ] CI/CD pipeline configured
