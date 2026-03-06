"""Tests for the remember tool."""


import pytest

from alfred.memory.jsonl_store import JSONLMemoryStore as MemoryStore
from alfred.tools import clear_registry, get_registry, register_builtin_tools
from alfred.tools.remember import RememberTool


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
    from alfred.config import Config

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

    memory_store = MemoryStore(config=mock_config, embedder=mock_embedder)
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
    assert "identity" in mem.tags
    assert "name" in mem.tags
    assert mem.embedding is not None
    assert len(mem.embedding) == 1536


@pytest.mark.asyncio
async def test_remember_tool_without_tags(mock_config, mock_embedder):
    """Remember tool works without optional tags."""
    clear_registry()

    memory_store = MemoryStore(config=mock_config, embedder=mock_embedder)
    await memory_store.clear()

    register_builtin_tools(memory_store=memory_store)
    tool = get_registry().get("remember")

    async for _chunk in tool.execute_stream(
        content="User prefers dark mode"
    ):
        pass  # Just consume

    memories = await memory_store.get_all_entries()
    assert len(memories) == 1
    assert memories[0].tags == []


@pytest.mark.asyncio
async def test_remember_tool_uses_default_importance(mock_config, mock_embedder):
    """Importance field removed - test deprecated."""
    pytest.skip("Importance field removed from MemoryEntry")


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

    memory_store = MemoryStore(config=mock_config, embedder=mock_embedder)
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


@pytest.mark.asyncio
async def test_remember_tool_has_permanent_parameter():
    """RememberToolParams has permanent field."""
    from alfred.tools.remember import RememberToolParams

    params = RememberToolParams(content="Test")
    assert hasattr(params, "permanent")
    assert params.permanent is False


@pytest.mark.asyncio
async def test_remember_tool_creates_permanent_entry(mock_config, mock_embedder):
    """Remember tool creates permanent memory when permanent=True."""
    clear_registry()

    memory_store = MemoryStore(config=mock_config, embedder=mock_embedder)
    await memory_store.clear()

    register_builtin_tools(memory_store=memory_store)
    tool = get_registry().get("remember")

    result_chunks = []
    async for chunk in tool.execute_stream(content="Important memory", permanent=True):
        result_chunks.append(chunk)

    result = "".join(result_chunks)
    assert "Remembered" in result

    # Verify memory is permanent
    memories = await memory_store.get_all_entries()
    assert len(memories) == 1
    assert memories[0].permanent is True


@pytest.mark.asyncio
async def test_remember_tool_default_permanent_false(mock_config, mock_embedder):
    """Remember tool defaults to non-permanent memory."""
    clear_registry()

    memory_store = MemoryStore(config=mock_config, embedder=mock_embedder)
    await memory_store.clear()

    register_builtin_tools(memory_store=memory_store)
    tool = get_registry().get("remember")

    result_chunks = []
    async for chunk in tool.execute_stream(content="Regular memory"):
        result_chunks.append(chunk)

    result = "".join(result_chunks)
    assert "Remembered" in result

    # Verify memory is NOT permanent
    memories = await memory_store.get_all_entries()
    assert len(memories) == 1
    assert memories[0].permanent is False
