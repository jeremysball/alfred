"""Tests for embedding providers and memory retrieval."""
import pytest
import numpy as np
from openclaw_pi.embeddings import (
    SimpleEmbeddingProvider,
    MemoryRetriever,
)


@pytest.mark.asyncio
async def test_simple_embedding_provider_embed():
    """Test simple embedding provider returns vector."""
    provider = SimpleEmbeddingProvider()
    
    embedding = await provider.embed("test text")
    
    assert isinstance(embedding, list)
    assert len(embedding) == 384  # Default dimension
    assert all(isinstance(x, (int, float)) for x in embedding)


@pytest.mark.asyncio
async def test_simple_embedding_provider_consistency():
    """Test same text produces same embedding."""
    provider = SimpleEmbeddingProvider()
    
    emb1 = await provider.embed("hello world")
    emb2 = await provider.embed("hello world")
    
    assert emb1 == emb2


@pytest.mark.asyncio
async def test_simple_embedding_provider_different_texts():
    """Test different texts produce different embeddings."""
    provider = SimpleEmbeddingProvider()
    
    emb1 = await provider.embed("hello world")
    emb2 = await provider.embed("goodbye world")
    
    assert emb1 != emb2


@pytest.mark.asyncio
async def test_simple_embedding_provider_batch():
    """Test batch embedding."""
    provider = SimpleEmbeddingProvider()
    texts = ["text one", "text two", "text three"]
    
    embeddings = await provider.embed_batch(texts)
    
    assert len(embeddings) == 3
    assert all(len(e) == 384 for e in embeddings)


@pytest.mark.asyncio
async def test_memory_retriever_add_document():
    """Test adding single document."""
    provider = SimpleEmbeddingProvider()
    retriever = MemoryRetriever(provider)
    
    await retriever.add_document("test document", metadata={"source": "test"})
    
    assert len(retriever._documents) == 1
    assert retriever._documents[0] == "test document"
    assert retriever._metadata[0]["source"] == "test"


@pytest.mark.asyncio
async def test_memory_retriever_add_documents():
    """Test adding multiple documents."""
    provider = SimpleEmbeddingProvider()
    retriever = MemoryRetriever(provider)
    
    texts = ["doc one", "doc two", "doc three"]
    await retriever.add_documents(texts)
    
    assert len(retriever._documents) == 3


@pytest.mark.asyncio
async def test_memory_retriever_search():
    """Test semantic search returns results."""
    provider = SimpleEmbeddingProvider()
    retriever = MemoryRetriever(provider)
    
    # Add documents
    await retriever.add_document("Python is a programming language")
    await retriever.add_document("JavaScript runs in browsers")
    await retriever.add_document("Python is great for data science")
    
    # Search
    results = await retriever.search("python programming", top_k=2)
    
    assert len(results) == 2
    assert all("score" in r for r in results)
    assert all("text" in r for r in results)
    # Python docs should score higher
    assert "Python" in results[0]["text"] or "Python" in results[1]["text"]


@pytest.mark.asyncio
async def test_memory_retriever_search_empty():
    """Test search with no documents returns empty."""
    provider = SimpleEmbeddingProvider()
    retriever = MemoryRetriever(provider)
    
    results = await retriever.search("query")
    
    assert results == []


@pytest.mark.asyncio
async def test_memory_retriever_clear():
    """Test clearing documents."""
    provider = SimpleEmbeddingProvider()
    retriever = MemoryRetriever(provider)
    
    await retriever.add_document("test")
    retriever.clear()
    
    assert len(retriever._documents) == 0
    assert len(retriever._embeddings) == 0


@pytest.mark.asyncio
async def test_memory_retriever_metadata_preserved():
    """Test metadata is returned with search results."""
    provider = SimpleEmbeddingProvider()
    retriever = MemoryRetriever(provider)
    
    await retriever.add_document(
        "important note",
        metadata={"date": "2026-02-15", "priority": "high"}
    )
    
    results = await retriever.search("note")
    
    assert len(results) == 1
    assert results[0]["metadata"]["date"] == "2026-02-15"
    assert results[0]["metadata"]["priority"] == "high"


def test_cosine_similarity_identical():
    """Test cosine similarity of identical vectors is 1."""
    provider = SimpleEmbeddingProvider()
    retriever = MemoryRetriever(provider)
    
    vec = [1.0, 2.0, 3.0]
    similarity = retriever._cosine_similarity(vec, vec)
    
    assert abs(similarity - 1.0) < 0.001


def test_cosine_similarity_orthogonal():
    """Test cosine similarity of orthogonal vectors is 0."""
    provider = SimpleEmbeddingProvider()
    retriever = MemoryRetriever(provider)
    
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [0.0, 1.0, 0.0]
    similarity = retriever._cosine_similarity(vec1, vec2)
    
    assert abs(similarity) < 0.001


def test_cosine_similarity_opposite():
    """Test cosine similarity of opposite vectors is -1."""
    provider = SimpleEmbeddingProvider()
    retriever = MemoryRetriever(provider)
    
    vec1 = [1.0, 2.0, 3.0]
    vec2 = [-1.0, -2.0, -3.0]
    similarity = retriever._cosine_similarity(vec1, vec2)
    
    assert abs(similarity - (-1.0)) < 0.001


@pytest.mark.asyncio
async def test_memory_retriever_top_k_limits():
    """Test top_k parameter limits results."""
    provider = SimpleEmbeddingProvider()
    retriever = MemoryRetriever(provider)
    
    # Add 5 documents
    for i in range(5):
        await retriever.add_document(f"document {i}")
    
    # Search with top_k=2
    results = await retriever.search("document", top_k=2)
    
    assert len(results) == 2


@pytest.mark.skipif(
    not False,  # Skip by default - requires OPENAI_API_KEY
    reason="Requires OpenAI API key"
)
@pytest.mark.asyncio
async def test_openai_embedding_provider():
    """Test OpenAI embedding provider (requires API key)."""
    import os
    from openclaw_pi.embeddings import OpenAIEmbeddingProvider
    
    provider = OpenAIEmbeddingProvider(api_key=os.getenv("OPENAI_API_KEY"))
    
    embedding = await provider.embed("test text")
    
    assert isinstance(embedding, list)
    assert len(embedding) == 1536  # text-embedding-3-small dimension
