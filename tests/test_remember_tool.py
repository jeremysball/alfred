"""Tests for the remember tool."""

import pytest
from datetime import datetime

from src.tools.remember import RememberTool
from src.tools import register_builtin_tools, get_registry, clear_registry
from src.memory import MemoryStore
from src.types import MemoryEntry


class MockEmbedder:
    """Mock embedder for testing."""

    def __init__(self, dimension: int = 1536):
        self.dimension = dimension

    async def embed(self, text: str) -> list[float]:
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        vector = []
        for i in range(self.dimension):
            val = ((hash_val + i * 31) % 2000 - 1000) / 1000.0
            vector.append(val)
        return vector

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]


@pytest.fixture
def mock_config(tmp_path, monkeypatch):
    from src.config import Config

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("KIMI_API_KEY", "test")
    monkeypatch.setenv("KIMI_BASE_URL", "https://test.moonshot.cn/v1")

    return Config(
        telegram_bot_token="test",
        openai_api_key="test",
        kimi_api_key="test",
        kimi_base_url="https://test.moonshot.cn/v1",
        default_llm_provider="kimi",
        embedding_model="text-embedding-3-small",
        chat_model="kimi-k2-5",
        memory_context_limit=20,
        workspace_dir=tmp_path,
        memory_dir=tmp_path / "memory",
        context_files={},
    )


@pytest.fixture
def mock_embedder():
    return MockEmbedder()


@pytest.mark.asyncio
async def test_remember_tool_saves_memory(mock_config, mock_embedder):
    """Remember tool saves a memory to the store."""
    clear_registry()
    
    memory_store = MemoryStore(mock_config, mock_embedder)
    await memory_store.clear()
    
    # Register tool with memory store
    register_builtin_tools(memory_store=memory_store)
    tool = get_registry().get("remember")
    
    assert tool is not None
    assert tool._memory_store is not None
    
    # Execute the tool
    result_chunks = []
    async for chunk in tool.execute_stream(
        content="User name is Jaz",
        importance=0.9,
        tags="identity,name"
    ):
        result_chunks.append(chunk)
    
    result = "".join(result_chunks)
    
    # Verify result
    assert "Remembered" in result
    assert "User name is Jaz" in result
    assert "identity" in result
    assert "name" in result
    
    # Verify memory was saved
    memories = await memory_store.get_all_entries()
    assert len(memories) == 1
    
    mem = memories[0]
    assert mem.content == "User name is Jaz"
    assert mem.importance == 0.9
    assert "identity" in mem.tags
    assert "name" in mem.tags
    assert mem.embedding is not None
    assert len(mem.embedding) == 1536


@pytest.mark.asyncio
async def test_remember_tool_without_tags(mock_config, mock_embedder):
    """Remember tool works without optional tags."""
    clear_registry()
    
    memory_store = MemoryStore(mock_config, mock_embedder)
    await memory_store.clear()
    
    register_builtin_tools(memory_store=memory_store)
    tool = get_registry().get("remember")
    
    async for chunk in tool.execute_stream(
        content="User prefers dark mode",
        importance=0.7
    ):
        pass  # Just consume
    
    memories = await memory_store.get_all_entries()
    assert len(memories) == 1
    assert memories[0].tags == []


@pytest.mark.asyncio
async def test_remember_tool_uses_default_importance(mock_config, mock_embedder):
    """Remember tool uses default importance of 0.5."""
    clear_registry()
    
    memory_store = MemoryStore(mock_config, mock_embedder)
    await memory_store.clear()
    
    register_builtin_tools(memory_store=memory_store)
    tool = get_registry().get("remember")
    
    async for chunk in tool.execute_stream(content="User likes coffee"):
        pass
    
    memories = await memory_store.get_all_entries()
    assert len(memories) == 1
    assert memories[0].importance == 0.5


@pytest.mark.asyncio
async def test_remember_tool_error_without_memory_store(mock_config, mock_embedder):
    """Remember tool returns error if memory store not set."""
    tool = RememberTool(memory_store=None)
    
    result_chunks = []
    async for chunk in tool.execute_stream(content="Test"):
        result_chunks.append(chunk)
    
    result = "".join(result_chunks)
    assert "Error" in result
    assert "not initialized" in result


@pytest.mark.asyncio
async def test_remember_tool_content_truncation(mock_config, mock_embedder):
    """Remember tool truncates long content in response."""
    clear_registry()
    
    memory_store = MemoryStore(mock_config, mock_embedder)
    await memory_store.clear()
    
    register_builtin_tools(memory_store=memory_store)
    tool = get_registry().get("remember")
    
    long_content = "A" * 200
    
    result_chunks = []
    async for chunk in tool.execute_stream(content=long_content):
        result_chunks.append(chunk)
    
    result = "".join(result_chunks)
    assert "..." in result  # Should be truncated in response
    
    # But full content should be saved
    memories = await memory_store.get_all_entries()
    assert memories[0].content == long_content
