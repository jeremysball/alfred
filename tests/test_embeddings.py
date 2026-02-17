"""Tests for embedding client and similarity functions."""

from pathlib import Path

import pytest

from src.embeddings import cosine_similarity


def test_cosine_similarity_identical_vectors():
    """Cosine similarity of identical vectors is 1.0."""
    v = [1.0, 2.0, 3.0]
    assert cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors():
    """Cosine similarity of orthogonal vectors is 0.0."""
    a = [1.0, 0.0, 0.0]
    b = [0.0, 1.0, 0.0]
    assert cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_similarity_opposite_vectors():
    """Cosine similarity of opposite vectors is -1.0."""
    a = [1.0, 2.0, 3.0]
    b = [-1.0, -2.0, -3.0]
    assert cosine_similarity(a, b) == pytest.approx(-1.0)


def test_cosine_similarity_zero_vector():
    """Cosine similarity with zero vector returns 0.0."""
    a = [1.0, 2.0, 3.0]
    b = [0.0, 0.0, 0.0]
    assert cosine_similarity(a, b) == 0.0


@pytest.mark.asyncio
async def test_embedding_client_with_mock(monkeypatch):
    """EmbeddingClient can be initialized with config."""
    from src.config import Config
    from src.embeddings import EmbeddingClient

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")
    monkeypatch.setenv("KIMI_API_KEY", "test")
    monkeypatch.setenv("KIMI_BASE_URL", "https://test.moonshot.cn/v1")

    config = Config(
        telegram_bot_token="test",
        openai_api_key="test_key",
        kimi_api_key="test",
        kimi_base_url="https://test.moonshot.cn/v1",
        default_llm_provider="kimi",
        embedding_model="text-embedding-3-small",
        chat_model="kimi-k2-5",
        memory_context_limit=20,
        workspace_dir=Path("."),
        memory_dir=Path("./memory"),
        context_files={},
    )

    client = EmbeddingClient(config)
    assert client.model == config.embedding_model
