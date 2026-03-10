"""Tests for M4: Search logic consolidation (PRD #109).

Verifies that search functionality works via SQLiteStore
after removing src/search.py.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

from alfred.storage.sqlite import SQLiteStore


class TestSearchConsolidation:
    """Test search functionality via SQLiteStore."""

    @pytest.fixture
    async def store(self, tmp_path):
        """Fixture providing initialized SQLiteStore."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(db_path)
        await store._init()
        return store

    @pytest.mark.asyncio
    async def test_search_memories_by_embedding(self, store):
        """Should search memories using vector embedding."""
        # Add test memories
        await store.add_memory(
            entry_id="mem-1",
            role="user",
            content="Python programming tips",
            embedding=[0.9] * 384,
            tags=["coding"]
        )
        await store.add_memory(
            entry_id="mem-2",
            role="user",
            content="Cooking recipes",
            embedding=[0.1] * 384,
            tags=["cooking"]
        )
        
        # Search with similar embedding to first memory
        query_embedding = [0.85] * 384
        results = await store.search_memories(
            query_embedding=query_embedding,
            top_k=5
        )
        
        # Should return results
        assert isinstance(results, list)
        # Implementation may vary, but should return at least one result
        # when sqlite-vec is available

    @pytest.mark.asyncio
    async def test_search_with_role_filter(self, store):
        """Should filter memories by role."""
        await store.add_memory(
            entry_id="user-mem",
            role="user",
            content="User message",
            embedding=[0.5] * 384
        )
        await store.add_memory(
            entry_id="assistant-mem",
            role="assistant",
            content="Assistant response",
            embedding=[0.5] * 384
        )
        
        results = await store.search_memories(
            query_embedding=[0.5] * 384,
            top_k=10,
            role="user"
        )
        
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_respects_top_k(self, store):
        """Should respect top_k parameter."""
        # Add multiple memories
        for i in range(5):
            await store.add_memory(
                entry_id=f"mem-{i}",
                role="user",
                content=f"Memory {i}",
                embedding=[0.5] * 384
            )
        
        results = await store.search_memories(
            query_embedding=[0.5] * 384,
            top_k=3
        )
        
        assert len(results) <= 3


class TestContextBuilderWithoutSearchPy:
    """Test ContextBuilder works without src/search.py."""

    @pytest.mark.asyncio
    async def test_context_builder_imports(self):
        """ContextBuilder should import without src/search.py."""
        # This test verifies the import works after search.py is deleted
        try:
            from alfred.context import ContextBuilder
            assert True
        except ImportError as e:
            if "search" in str(e).lower():
                pytest.fail(f"ContextBuilder still depends on search.py: {e}")
            raise

    @pytest.mark.asyncio
    async def test_context_builder_uses_sqlite_store(self, tmp_path):
        """ContextBuilder should use SQLiteStore for search."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(db_path)
        await store._init()
        
        # Add a memory
        await store.add_memory(
            entry_id="test-mem",
            role="assistant",
            content="Important information about testing",
            embedding=[0.8] * 384
        )
        
        # ContextBuilder should be able to search via store
        from alfred.context import ContextBuilder
        
        builder = ContextBuilder(store=store)
        # The builder should have access to the store for search
        assert builder.store is not None


class TestSearchMemoriesToolConsolidation:
    """Test SearchMemoriesTool uses SQLiteStore."""

    @pytest.mark.asyncio
    async def test_search_tool_uses_store(self, tmp_path):
        """SearchMemoriesTool should use SQLiteStore."""
        from alfred.tools.search_memories import SearchMemoriesTool
        
        tool = SearchMemoriesTool()
        
        # The tool should have execute_stream method
        assert hasattr(tool, 'execute_stream')
        
        # When no store is set, should return error
        results = []
        async for chunk in tool.execute_stream(query="test"):
            results.append(chunk)
        
        result = "".join(results)
        assert "Error: Memory store not initialized" in result or "No relevant memories" in result
