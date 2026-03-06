"""Tests for EmbeddingProvider abstraction and implementations."""

import pytest

from alfred.config import Config


# Check if sentence-transformers is available
try:
    import sentence_transformers  # noqa: F401
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class TestEmbeddingProviderABC:
    """Test the EmbeddingProvider abstract base class."""

    def test_cannot_instantiate_directly(self) -> None:
        """EmbeddingProvider should not be instantiable directly."""
        from alfred.embeddings.provider import EmbeddingProvider

        with pytest.raises(TypeError):
            EmbeddingProvider()  # type: ignore


@pytest.mark.skipif(
    not SENTENCE_TRANSFORMERS_AVAILABLE,
    reason="sentence-transformers not installed"
)
class TestBGEProvider:
    """Test BGE local embedding provider (requires sentence-transformers)."""

    @pytest.fixture
    def provider(self) -> "BGEProvider":
        """Create BGEProvider instance."""
        from alfred.embeddings.bge_provider import BGEProvider

        return BGEProvider()

    def test_dimension_is_768(self, provider: "BGEProvider") -> None:
        """BGE-base produces 768-dimensional embeddings."""
        assert provider.dimension == 768

    @pytest.mark.asyncio
    async def test_embed_returns_correct_dimension(self, provider: "BGEProvider") -> None:
        """Single embed should return 768 floats."""
        embedding = await provider.embed("Hello, world!")

        assert len(embedding) == 768
        assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_embed_batch_returns_correct_dimensions(self, provider: "BGEProvider") -> None:
        """Batch embed should return list of 768-float lists."""
        texts = ["Hello", "World", "Test"]
        embeddings = await provider.embed_batch(texts)

        assert len(embeddings) == 3
        for emb in embeddings:
            assert len(emb) == 768

    @pytest.mark.asyncio
    async def test_similar_texts_have_high_similarity(self, provider: "BGEProvider") -> None:
        """Similar texts should produce similar embeddings."""
        from alfred.embeddings import cosine_similarity

        emb1 = await provider.embed("The cat sat on the mat")
        emb2 = await provider.embed("A cat is sitting on a mat")
        emb3 = await provider.embed("Quantum computing uses qubits")

        sim_similar = cosine_similarity(emb1, emb2)
        sim_different = cosine_similarity(emb1, emb3)

        # Similar texts should have higher similarity
        assert sim_similar > sim_different
        assert sim_similar > 0.7  # Reasonably high for similar content

    @pytest.mark.asyncio
    async def test_empty_text_returns_embedding(self, provider: "BGEProvider") -> None:
        """Empty string should still return valid embedding."""
        embedding = await provider.embed("")

        assert len(embedding) == 768
        # Empty string embedding should be different from random text
        random_emb = await provider.embed("xyz123random")
        from alfred.embeddings import cosine_similarity

        sim = cosine_similarity(embedding, random_emb)
        # They shouldn't be identical
        assert sim < 0.99


@pytest.mark.skipif(
    not SENTENCE_TRANSFORMERS_AVAILABLE,
    reason="sentence-transformers not installed"
)
class TestBGEProviderSingleton:
    """Test that BGE model is loaded as singleton."""

    def test_get_model_returns_same_instance(self) -> None:
        """Multiple calls should return same model instance."""
        from alfred.embeddings.bge_provider import get_model

        model1 = get_model()
        model2 = get_model()

        assert model1 is model2

    def test_provider_uses_singleton(self) -> None:
        """Provider should use singleton model."""
        from alfred.embeddings.bge_provider import BGEProvider, get_model

        provider = BGEProvider()
        # Access internal model reference
        model = get_model()

        # Provider should be using the same model
        assert provider._model is model


class TestOpenAIProvider:
    """Test OpenAI embedding provider (refactored from existing code)."""

    @pytest.fixture
    def provider(self, mock_config: Config) -> "OpenAIProvider":
        """Create OpenAIProvider instance with mock config."""
        from alfred.embeddings.openai_provider import OpenAIProvider

        return OpenAIProvider(mock_config)

    def test_dimension_is_1536(self, provider: "OpenAIProvider") -> None:
        """OpenAI text-embedding-3-small produces 1536-dimensional embeddings."""
        assert provider.dimension == 1536


class TestProviderFactory:
    """Test provider factory function."""

    def test_create_local_provider(self, mock_config: Config) -> None:
        """Should create BGEProvider when provider='local'."""
        from alfred.embeddings import create_provider
        from alfred.embeddings.bge_provider import BGEProvider

        # Modify config to use local
        mock_config.embedding_provider = "local"

        provider = create_provider(mock_config)

        assert isinstance(provider, BGEProvider)
        assert provider.dimension == 768

    def test_create_openai_provider(self, mock_config: Config) -> None:
        """Should create OpenAIProvider when provider='openai'."""
        from alfred.embeddings import create_provider
        from alfred.embeddings.openai_provider import OpenAIProvider

        mock_config.embedding_provider = "openai"

        provider = create_provider(mock_config)

        assert isinstance(provider, OpenAIProvider)
        assert provider.dimension == 1536

    def test_default_is_openai(self) -> None:
        """Should default to OpenAI if provider not specified."""
        from alfred.embeddings import create_provider
        from alfred.embeddings.openai_provider import OpenAIProvider

        # Create mock config without embedding_provider
        class MockConfigMinimal:
            openai_api_key = "test-key"
            embedding_model = "text-embedding-3-small"
            # No embedding_provider attribute

        provider = create_provider(MockConfigMinimal())  # type: ignore

        assert isinstance(provider, OpenAIProvider)


# Fixtures
@pytest.fixture
def mock_config() -> Config:
    """Create mock config for testing."""
    from pathlib import Path

    class MockConfig:
        openai_api_key = "test-key"
        embedding_model = "text-embedding-3-small"
        embedding_provider = "openai"
        local_embedding_model = "bge-base"

    return MockConfig()  # type: ignore
