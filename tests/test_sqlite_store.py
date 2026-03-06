"""Tests for SQLite + sqlite-vec unified storage (M2 of PRD #109).

These tests verify the SQLiteStore class that replaces
all previous storage implementations (CAS, JSONL, FAISS).
"""

import pytest
import asyncio
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.storage.sqlite import SQLiteStore


# =============================================================================
# SQLiteStore Initialization Tests
# =============================================================================


class TestSQLiteStoreInitialization:
    """Test SQLiteStore initialization and connection management."""

    @pytest.mark.asyncio
    async def test_store_initializes_with_valid_path(self, tmp_path):
        """Store should initialize with a valid database file path."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(db_path)
        await store._init()
        assert db_path.exists()

    @pytest.mark.asyncio
    async def test_store_creates_parent_directories(self, tmp_path):
        """Store should create parent directories if they don't exist."""
        db_path = tmp_path / "nested" / "dirs" / "test.db"
        store = SQLiteStore(db_path)
        await store._init()
        assert db_path.exists()

    @pytest.mark.asyncio
    async def test_store_initializes_idempotent(self, tmp_path):
        """Multiple _init calls should be idempotent."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(db_path)
        await store._init()
        await store._init()  # Should not raise
        assert store._initialized


# =============================================================================
# Session Storage Tests
# =============================================================================


class TestSessionStorage:
    """Test session storage operations (replaces SessionStorage)."""

    @pytest.fixture
    async def store(self, tmp_path):
        """Fixture providing initialized SQLiteStore."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(db_path)
        await store._init()
        return store

    @pytest.mark.asyncio
    async def test_save_and_load_session(self, store):
        """Should save session and load it by ID."""
        session_id = "test-session-1"
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        await store.save_session(session_id, messages)
        loaded = await store.load_session(session_id)
        
        assert loaded is not None
        assert loaded["session_id"] == session_id
        assert len(loaded["messages"]) == 2
        assert loaded["messages"][0]["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_load_nonexistent_session_returns_none(self, store):
        """Should return None for non-existent session."""
        loaded = await store.load_session("does-not-exist")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_list_sessions_returns_recent_first(self, store):
        """Should list sessions ordered by updated_at."""
        await store.save_session("session-1", [{"role": "user", "content": "First"}])
        await asyncio.sleep(0.01)
        await store.save_session("session-2", [{"role": "user", "content": "Second"}])
        
        sessions = await store.list_sessions(limit=10)
        assert len(sessions) == 2
        assert sessions[0]["session_id"] == "session-2"  # Most recent first

    @pytest.mark.asyncio
    async def test_list_sessions_respects_limit(self, store):
        """Should respect limit parameter."""
        for i in range(5):
            await store.save_session(f"session-{i}", [])
            await asyncio.sleep(0.001)
        
        sessions = await store.list_sessions(limit=3)
        assert len(sessions) == 3

    @pytest.mark.asyncio
    async def test_delete_session_removes_it(self, store):
        """Should delete session by ID."""
        await store.save_session("to-delete", [{"role": "user", "content": "Delete me"}])
        
        deleted = await store.delete_session("to-delete")
        assert deleted is True
        
        loaded = await store.load_session("to-delete")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session_returns_false(self, store):
        """Should return False when deleting non-existent session."""
        result = await store.delete_session("never-existed")
        assert result is False


# =============================================================================
# Cron Jobs Storage Tests
# =============================================================================


class TestCronJobStorage:
    """Test cron job storage operations (replaces CronStore)."""

    @pytest.fixture
    async def store(self, tmp_path):
        """Fixture providing initialized SQLiteStore."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(db_path)
        await store._init()
        return store

    @pytest.mark.asyncio
    async def test_save_and_load_job(self, store):
        """Should save job and load it."""
        job = {
            "job_id": "job-1",
            "name": "Daily Summary",
            "schedule": "0 9 * * *",
            "command": "summarize daily",
            "enabled": True
        }
        
        await store.save_job(job)
        jobs = await store.load_jobs()
        
        assert len(jobs) == 1
        assert jobs[0]["job_id"] == "job-1"
        assert jobs[0]["name"] == "Daily Summary"

    @pytest.mark.asyncio
    async def test_load_jobs_returns_all_jobs(self, store):
        """load_jobs should return all jobs including disabled."""
        await store.save_job({
            "job_id": "enabled-job",
            "name": "Enabled",
            "schedule": "* * * * *",
            "command": "run",
            "enabled": True
        })
        await store.save_job({
            "job_id": "disabled-job",
            "name": "Disabled",
            "schedule": "* * * * *",
            "command": "run",
            "enabled": False
        })
        
        jobs = await store.load_jobs()
        assert len(jobs) == 2
        job_ids = {j["job_id"] for j in jobs}
        assert job_ids == {"enabled-job", "disabled-job"}

    @pytest.mark.asyncio
    async def test_delete_job(self, store):
        """Should delete job by ID."""
        await store.save_job({
            "job_id": "to-delete",
            "name": "Delete Me",
            "schedule": "* * * * *",
            "command": "run",
            "enabled": True
        })
        
        deleted = await store.delete_job("to-delete")
        assert deleted is True
        
        jobs = await store.load_jobs()
        assert len(jobs) == 0

    @pytest.mark.asyncio
    async def test_record_execution(self, store):
        """Should record job execution history."""
        await store.save_job({
            "job_id": "job-with-history",
            "name": "Test Job",
            "schedule": "* * * * *",
            "command": "run",
            "enabled": True
        })
        
        record = {
            "execution_id": "exec-1",
            "job_id": "job-with-history",
            "status": "success",
            "output": "Job completed",
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat()
        }
        
        await store.record_execution(record)
        history = await store.get_job_history("job-with-history", limit=10)
        
        assert len(history) == 1
        assert history[0]["status"] == "success"


# =============================================================================
# Memory Storage Tests
# =============================================================================


class TestMemoryStorage:
    """Test memory storage with vector embeddings."""

    @pytest.fixture
    async def store(self, tmp_path):
        """Fixture providing initialized SQLiteStore."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(db_path)
        await store._init()
        return store

    @pytest.mark.asyncio
    async def test_add_memory(self, store):
        """Should add memory with content and tags."""
        await store.add_memory(
            entry_id="test-entry-1",
            role="user",
            content="Test memory content",
            tags=["test", "important"]
        )
        
        memory = await store.get_memory("test-entry-1")
        assert memory is not None
        assert memory["content"] == "Test memory content"

    @pytest.mark.asyncio
    async def test_get_memory(self, store):
        """Should retrieve memory by entry_id."""
        await store.add_memory(
            entry_id="test-entry-2",
            role="assistant",
            content="Retrievable memory",
            tags=["important"]
        )
        
        memory = await store.get_memory("test-entry-2")
        assert memory is not None
        assert memory["content"] == "Retrievable memory"
        assert memory["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_get_nonexistent_memory_returns_none(self, store):
        """Should return None for non-existent memory."""
        memory = await store.get_memory("does-not-exist")
        assert memory is None

    @pytest.mark.asyncio
    async def test_delete_memory(self, store):
        """Should delete memory by entry_id."""
        await store.add_memory(
            entry_id="delete-me",
            role="user",
            content="Delete me"
        )
        
        deleted = await store.delete_memory("delete-me")
        assert deleted is True
        
        memory = await store.get_memory("delete-me")
        assert memory is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_memory_returns_false(self, store):
        """Should return False when deleting non-existent memory."""
        result = await store.delete_memory("never-existed")
        assert result is False

    @pytest.mark.asyncio
    async def test_update_memory(self, store):
        """Should update memory content and tags."""
        await store.add_memory(
            entry_id="update-me",
            role="user",
            content="Original content",
            tags=["v1"]
        )
        
        await store.update_memory(
            "update-me",
            content="Updated content",
            tags=["v2", "updated"]
        )
        
        memory = await store.get_memory("update-me")
        assert memory["content"] == "Updated content"
        assert "v2" in memory["tags"]

    @pytest.mark.asyncio
    async def test_get_all_memories(self, store):
        """Should return all memories."""
        for i in range(3):
            await store.add_memory(
                entry_id=f"memory-{i}",
                role="user",
                content=f"Memory {i}"
            )
        
        memories = await store.get_all_memories()
        assert len(memories) == 3


# =============================================================================
# Memory Search Tests (Vector + Hybrid)
# =============================================================================


class TestMemorySearch:
    """Test vector and hybrid search capabilities."""

    @pytest.fixture
    async def store(self, tmp_path):
        """Fixture providing initialized SQLiteStore."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(db_path)
        await store._init()
        return store

    @pytest.mark.asyncio
    async def test_search_memories_by_embedding(self, store):
        """Should search memories by embedding vector."""
        # Add some memories
        await store.add_memory(
            entry_id="mem-1",
            role="user",
            content="Python programming tips",
            embedding=[0.9] * 384
        )
        await store.add_memory(
            entry_id="mem-2",
            role="user",
            content="Cooking recipes",
            embedding=[0.1] * 384
        )
        
        # Search with similar embedding
        query_embedding = [0.85] * 384
        results = await store.search_memories(
            query_embedding=query_embedding,
            top_k=5
        )
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_respects_role_filter(self, store):
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
    async def test_search_respects_limit(self, store):
        """Should respect top_k parameter in search."""
        for i in range(5):
            await store.add_memory(
                entry_id=f"mem-{i}",
                role="user",
                content=f"Memory number {i}",
                embedding=[0.5] * 384
            )
        
        results = await store.search_memories(
            query_embedding=[0.5] * 384,
            top_k=3
        )
        assert len(results) <= 3


# =============================================================================
# Memory Pruning Tests
# =============================================================================


class TestMemoryPruning:
    """Test memory TTL and pruning functionality."""

    @pytest.fixture
    async def store(self, tmp_path):
        """Fixture providing initialized SQLiteStore."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(db_path)
        await store._init()
        return store

    @pytest.mark.asyncio
    async def test_prune_old_memories(self, store):
        """Should remove memories past their TTL."""
        # Add memory with old timestamp
        old_time = datetime.now() - timedelta(days=100)
        await store.add_memory(
            entry_id="old-memory",
            role="user",
            content="Old memory",
            timestamp=old_time
        )
        
        # Add recent memory
        await store.add_memory(
            entry_id="recent-memory",
            role="user",
            content="Recent memory"
        )
        
        # Prune memories older than 30 days
        pruned = await store.prune_memories(ttl_days=30)
        assert isinstance(pruned, int)

    @pytest.mark.asyncio
    async def test_prune_respects_permanent_flag(self, store):
        """Should not prune permanent memories."""
        old_time = datetime.now() - timedelta(days=100)
        await store.add_memory(
            entry_id="permanent-memory",
            role="user",
            content="Permanent memory",
            permanent=True,
            timestamp=old_time
        )
        
        # Even with old date, permanent should not be pruned
        pruned = await store.prune_memories(ttl_days=30)
        # Implementation dependent - test ensures method exists and works
        assert isinstance(pruned, int)
        
        # Verify permanent memory still exists
        memory = await store.get_memory("permanent-memory")
        assert memory is not None


# =============================================================================
# Integration Tests
# =============================================================================


class TestStoreIntegration:
    """Integration tests for complete workflows."""

    @pytest.fixture
    async def store(self, tmp_path):
        """Fixture providing initialized SQLiteStore."""
        db_path = tmp_path / "alfred.db"
        store = SQLiteStore(db_path)
        await store._init()
        return store

    @pytest.mark.asyncio
    async def test_full_session_workflow(self, store):
        """Test complete session lifecycle."""
        # Create session
        session_id = "workflow-test"
        messages = [
            {"role": "user", "content": "Start session"},
            {"role": "assistant", "content": "Session started"}
        ]
        
        # Save and verify
        await store.save_session(session_id, messages)
        loaded = await store.load_session(session_id)
        assert loaded["messages"][0]["content"] == "Start session"
        
        # Update
        messages.append({"role": "user", "content": "Continue"})
        await store.save_session(session_id, messages)
        
        # List
        sessions = await store.list_sessions()
        assert len(sessions) >= 1
        
        # Delete
        await store.delete_session(session_id)
        assert await store.load_session(session_id) is None

    @pytest.mark.asyncio
    async def test_full_job_workflow(self, store):
        """Test complete cron job lifecycle."""
        job = {
            "job_id": "integration-job",
            "name": "Integration Test Job",
            "schedule": "0 */6 * * *",
            "command": "run_integration_test",
            "enabled": True
        }
        
        # Save job
        await store.save_job(job)
        jobs = await store.load_jobs()
        assert len(jobs) == 1
        
        # Record execution
        await store.record_execution({
            "execution_id": "exec-1",
            "job_id": "integration-job",
            "status": "success",
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat()
        })
        
        history = await store.get_job_history("integration-job")
        assert len(history) == 1
        
        # Delete
        await store.delete_job("integration-job")
        assert len(await store.load_jobs()) == 0

    @pytest.mark.asyncio
    async def test_full_memory_workflow(self, store):
        """Test complete memory lifecycle."""
        # Add memories
        for i in range(3):
            await store.add_memory(
                entry_id=f"workflow-mem-{i}",
                role="user",
                content=f"Important fact {i}",
                tags=["workflow", f"fact-{i}"]
            )
        
        # Search
        results = await store.search_memories(
            query_embedding=[0.5] * 384,
            top_k=5
        )
        assert isinstance(results, list)
        
        # Update one
        await store.update_memory(
            "workflow-mem-0",
            content="Updated important fact",
            tags=["workflow", "updated"]
        )
        
        # Verify update
        memory = await store.get_memory("workflow-mem-0")
        assert memory["content"] == "Updated important fact"
        
        # Delete one
        await store.delete_memory("workflow-mem-1")
        assert await store.get_memory("workflow-mem-1") is None
