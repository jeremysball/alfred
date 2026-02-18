"""Integration tests for full memory CRUD workflow.

These tests use real MemoryStore with a test embedder (no API calls).
Verifies the complete memory lifecycle end-to-end.
"""

import shutil
from pathlib import Path

import pytest

from src.embeddings import EmbeddingClient
from src.memory import MemoryStore
from src.tools.forget import ForgetTool
from src.tools.remember import RememberTool
from src.tools.search_memories import SearchMemoriesTool
from src.tools.update_memory import UpdateMemoryTool


class TestEmbedder(EmbeddingClient):
    """Test embedder that returns deterministic embeddings without API calls."""

    def __init__(self):
        self.dimension = 1536

    async def embed(self, text: str) -> list[float]:
        """Return deterministic embedding based on text hash."""
        # Simple hash-based embedding for testing
        hash_val = hash(text) % 10000
        # Create a vector where similar texts have similar embeddings
        base = [0.0] * self.dimension
        # Use first few dimensions to encode text characteristics
        for i, char in enumerate(text[:10]):
            base[i] = (ord(char) % 100) / 100.0
        # Add hash-based variation
        base[10] = hash_val / 10000.0
        # Normalize
        import math
        norm = math.sqrt(sum(x * x for x in base))
        if norm > 0:
            base = [x / norm for x in base]
        return base

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts."""
        return [await self.embed(t) for t in texts]


@pytest.fixture
def temp_memory_dir(tmp_path):
    """Create a temporary directory for memory storage."""
    memory_dir = tmp_path / "test_memory"
    memory_dir.mkdir()
    yield memory_dir
    # Cleanup
    if memory_dir.exists():
        shutil.rmtree(memory_dir)


@pytest.fixture
async def memory_store(temp_memory_dir):
    """Create a real MemoryStore with test embedder."""
    # Create minimal config with all required fields

    class TestConfig:
        def __init__(self, memory_dir):
            self.memory_dir = Path(memory_dir)

    config = TestConfig(temp_memory_dir)
    embedder = TestEmbedder()
    store = MemoryStore(config, embedder)
    return store


@pytest.fixture
def tools(memory_store):
    """Create all memory tools with injected store."""
    remember = RememberTool()
    remember.set_memory_store(memory_store)

    search = SearchMemoriesTool()
    search.set_memory_store(memory_store)

    update = UpdateMemoryTool()
    update.set_memory_store(memory_store)

    forget = ForgetTool()
    forget.set_memory_store(memory_store)

    return {
        "remember": remember,
        "search": search,
        "update": update,
        "forget": forget,
    }


class TestMemoryCrudWorkflow:
    """End-to-end tests for memory CRUD operations."""

    async def test_full_crud_workflow(self, tools):
        """Test complete memory lifecycle: create, search, update, delete."""
        # 1. Create memory
        result = ""
        async for chunk in tools["remember"].execute_stream(
            content="User prefers Python over JavaScript",
        ):
            result += chunk
        assert "Remembered" in result

        # 2. Search for it
        result = ""
        async for chunk in tools["search"].execute_stream(query="Python"):
            result += chunk
        assert "User prefers Python" in result

        # Extract entry_id from search result
        # Format: "- [2026-02-18] User prefers... (92% match, id: abc123)"
        import re
        id_match = re.search(r'id: ([a-f0-9]+)', result)
        assert id_match, f"Could not find entry_id in: {result}"
        entry_id = id_match.group(1)

        # 3. Update via preview
        result = ""
        async for chunk in tools["update"].execute_stream(
            entry_id=entry_id,
            new_content="User prefers Python and Rust",
        ):
            result += chunk
        assert "Found memory to update" in result
        assert "Will update to:" in result
        assert "User prefers Python and Rust" in result

        # 4. Confirm update
        result = ""
        async for chunk in tools["update"].execute_stream(
            entry_id=entry_id,
            new_content="User prefers Python and Rust",
            confirm=True,
        ):
            result += chunk
        assert "Updated" in result

        # 5. Verify update via search by ID
        result = ""
        async for chunk in tools["search"].execute_stream(entry_id=entry_id):
            result += chunk
        assert "User prefers Python and Rust" in result
        assert "JavaScript" not in result

        # 6. Delete - First call requests confirmation (new two-call pattern)
        result = ""
        async for chunk in tools["forget"].execute_stream(memory_id=entry_id):
            result += chunk
        assert "Please confirm" in result
        assert entry_id in result

        # 7. Delete - Second call executes deletion
        result = ""
        async for chunk in tools["forget"].execute_stream(memory_id=entry_id):
            result += chunk
        assert "deleted" in result.lower()

        # 8. Verify deletion
        result = ""
        async for chunk in tools["search"].execute_stream(entry_id=entry_id):
            result += chunk
        assert "No memory found" in result or "not found" in result.lower()

    async def test_semantic_search_finds_relevant_memories(self, tools):
        """Test that semantic search returns relevant results."""
        # Create multiple memories
        memories = [
            ("User loves Python programming", 0.9),
            ("User enjoys hiking on weekends", 0.7),
            ("User's favorite food is pizza", 0.6),
        ]

        for content, _importance in memories:
            async for _ in tools["remember"].execute_stream(
                content=content,
            ):
                pass

        # Search for coding-related memory
        result = ""
        async for chunk in tools["search"].execute_stream(query="coding"):
            result += chunk

        # Should find Python memory first (most relevant)
        assert "Python" in result
        lines = result.strip().split("\n")
        # First result should be Python
        assert "Python" in lines[0] or "Python" in lines[1]

    async def test_update_by_query_finds_correct_memory(self, tools):
        """Test that update finds and updates the right memory."""
        # Create two memories
        async for _ in tools["remember"].execute_stream(
            content="User works at Acme Corp",
        ):
            pass

        async for _ in tools["remember"].execute_stream(
            content="User lives in Portland",
        ):
            pass

        # Get all memories and find work memory
        result = ""
        async for chunk in tools["search"].execute_stream(query="User"):
            result += chunk

        import re
        # Find the entry_id for the work memory
        lines = result.strip().split("\n")
        work_entry_id = None
        portland_entry_id = None
        for line in lines:
            id_match = re.search(r'id: ([a-f0-9]+)', line)
            if id_match and "Acme Corp" in line:
                work_entry_id = id_match.group(1)
            elif id_match and "Portland" in line:
                portland_entry_id = id_match.group(1)

        assert work_entry_id, "Could not find work memory"
        assert portland_entry_id, "Could not find Portland memory"

        # Update work memory using entry_id
        result = ""
        async for chunk in tools["update"].execute_stream(
            entry_id=work_entry_id,
            new_content="User works at TechCorp",
        ):
            result += chunk

        assert "Acme Corp" in result  # Found the work memory

        # Confirm update
        result = ""
        async for chunk in tools["update"].execute_stream(
            entry_id=work_entry_id,
            new_content="User works at TechCorp",
            confirm=True,
        ):
            result += chunk

        assert "Updated" in result

        # Verify work memory changed but location didn't
        result = ""
        async for chunk in tools["search"].execute_stream(entry_id=work_entry_id):
            result += chunk
        assert "TechCorp" in result

        result = ""
        async for chunk in tools["search"].execute_stream(entry_id=portland_entry_id):
            result += chunk
        assert "Portland" in result

    async def test_forget_by_query_finds_candidates(self, tools):
        """Test that forget by query returns candidates without deleting."""
        # Create memories about old project
        async for _ in tools["remember"].execute_stream(
            content="Old project: chatbot idea",
        ):
            pass

        async for _ in tools["remember"].execute_stream(
            content="Old project: mobile app concept",
        ):
            pass

        # Query to find candidates (does not delete)
        result = ""
        async for chunk in tools["forget"].execute_stream(query="old project"):
            result += chunk

        # Should find at least the 2 old project memories
        assert "Found" in result
        assert "chatbot" in result
        assert "mobile app" in result

        # Verify memories still exist (query mode doesn't delete)
        result = ""
        async for chunk in tools["search"].execute_stream(query="chatbot"):
            result += chunk
        assert "chatbot" in result

        # Now delete one memory using the two-call pattern
        import re
        id_match = re.search(r'id: ([a-f0-9]+)', result)
        assert id_match, "Could not find entry_id"
        entry_id = id_match.group(1)

        # First call - mark for deletion
        result = ""
        async for chunk in tools["forget"].execute_stream(memory_id=entry_id):
            result += chunk
        assert "Please confirm" in result

        # Second call - execute deletion
        result = ""
        async for chunk in tools["forget"].execute_stream(memory_id=entry_id):
            result += chunk
        assert "deleted" in result.lower()

    async def test_no_changes_without_confirmation(self, tools):
        """Test that preview mode doesn't modify anything."""
        # Create a memory
        async for _ in tools["remember"].execute_stream(
            content="Test memory content",
        ):
            pass

        # Try update without confirm
        result = ""
        async for chunk in tools["update"].execute_stream(
            search_query="test",
            new_content="Modified content",
        ):
            result += chunk

        # Should show preview, not update
        assert "Will update to:" in result

        # Verify memory unchanged
        result = ""
        async for chunk in tools["search"].execute_stream(query="test"):
            result += chunk
        assert "Test memory content" in result
        assert "Modified content" not in result

        # Query forget mode (does not delete)
        result = ""
        async for chunk in tools["forget"].execute_stream(query="test"):
            result += chunk

        assert "To delete a memory" in result

        # Verify memory still exists
        result = ""
        async for chunk in tools["search"].execute_stream(query="test"):
            result += chunk
        assert "Test memory content" in result
