"""Tests for JSONL to FAISS migration."""

import json
import pytest
from datetime import datetime
from pathlib import Path

from src.memory.migrate import migrate_jsonl_to_faiss
from src.memory.faiss_store import FAISSMemoryStore
from src.embeddings.bge_provider import BGEProvider


class TestMigration:
    """Test JSONL to FAISS migration."""

    @pytest.fixture
    def jsonl_file(self, tmp_path: Path) -> Path:
        """Create sample JSONL file with memories."""
        memories_file = tmp_path / "memories.jsonl"
        
        entries = [
            {
                "timestamp": "2026-03-01T10:00:00",
                "role": "user",
                "content": "First memory about Python",
                "tags": ["python", "coding"],
                "entry_id": "abc123",
                "permanent": False,
            },
            {
                "timestamp": "2026-03-02T11:00:00",
                "role": "assistant",
                "content": "Second memory about databases",
                "tags": ["database", "sql"],
                "entry_id": "def456",
                "permanent": True,
            },
            {
                "timestamp": "2026-03-03T12:00:00",
                "role": "user",
                "content": "Third memory about testing",
                "tags": ["testing"],
                "entry_id": "ghi789",
                "permanent": False,
            },
        ]
        
        with open(memories_file, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")
        
        return memories_file

    @pytest.mark.asyncio
    async def test_migrate_preserves_all_entries(self, jsonl_file: Path, tmp_path: Path) -> None:
        """Migration should preserve all memory entries."""
        faiss_path = tmp_path / "faiss"
        
        # Run migration
        stats = await migrate_jsonl_to_faiss(
            jsonl_path=jsonl_file,
            faiss_path=faiss_path,
            provider=BGEProvider(),
        )
        
        assert stats["migrated"] == 3
        assert stats["failed"] == 0
        
        # Verify entries exist in FAISS store
        store = FAISSMemoryStore(
            index_path=faiss_path,
            provider=BGEProvider(),
        )
        await store.load()
        
        entries = await store.get_all_entries()
        assert len(entries) == 3

    @pytest.mark.asyncio
    async def test_migrate_preserves_metadata(self, jsonl_file: Path, tmp_path: Path) -> None:
        """Migration should preserve all metadata fields."""
        faiss_path = tmp_path / "faiss"
        
        await migrate_jsonl_to_faiss(
            jsonl_path=jsonl_file,
            faiss_path=faiss_path,
            provider=BGEProvider(),
        )
        
        store = FAISSMemoryStore(
            index_path=faiss_path,
            provider=BGEProvider(),
        )
        await store.load()
        
        # Check first entry
        entry = await store.get_by_id("abc123")
        assert entry is not None
        assert entry.content == "First memory about Python"
        assert "python" in entry.tags
        assert entry.permanent is False
        
        # Check permanent flag
        entry2 = await store.get_by_id("def456")
        assert entry2 is not None
        assert entry2.permanent is True

    @pytest.mark.asyncio
    async def test_migrate_creates_backup(self, jsonl_file: Path, tmp_path: Path) -> None:
        """Migration should create backup of original file."""
        faiss_path = tmp_path / "faiss"
        
        await migrate_jsonl_to_faiss(
            jsonl_path=jsonl_file,
            faiss_path=faiss_path,
            provider=BGEProvider(),
            backup=True,
        )
        
        backup_file = jsonl_file.with_suffix(".jsonl.bak")
        assert backup_file.exists()
        
        # Backup should have same content
        with open(jsonl_file.with_suffix(".jsonl.bak")) as f:
            backup_lines = f.readlines()
        with open(jsonl_file) as f:
            original_lines = f.readlines()
        
        assert backup_lines == original_lines

    @pytest.mark.asyncio
    async def test_migrate_handles_empty_file(self, tmp_path: Path) -> None:
        """Migration should handle empty JSONL file."""
        empty_file = tmp_path / "empty.jsonl"
        empty_file.touch()
        
        faiss_path = tmp_path / "faiss"
        
        stats = await migrate_jsonl_to_faiss(
            jsonl_path=empty_file,
            faiss_path=faiss_path,
            provider=BGEProvider(),
        )
        
        assert stats["migrated"] == 0
        assert stats["failed"] == 0

    @pytest.mark.asyncio
    async def test_migrate_handles_missing_file(self, tmp_path: Path) -> None:
        """Migration should handle non-existent file gracefully."""
        missing_file = tmp_path / "nonexistent.jsonl"
        faiss_path = tmp_path / "faiss"
        
        stats = await migrate_jsonl_to_faiss(
            jsonl_path=missing_file,
            faiss_path=faiss_path,
            provider=BGEProvider(),
        )
        
        assert stats["migrated"] == 0
        assert "error" in stats or stats["failed"] == 0

    @pytest.mark.asyncio
    async def test_migrate_searchable_after_migration(self, jsonl_file: Path, tmp_path: Path) -> None:
        """Migrated entries should be searchable."""
        faiss_path = tmp_path / "faiss"
        
        await migrate_jsonl_to_faiss(
            jsonl_path=jsonl_file,
            faiss_path=faiss_path,
            provider=BGEProvider(),
        )
        
        store = FAISSMemoryStore(
            index_path=faiss_path,
            provider=BGEProvider(),
        )
        await store.load()
        
        # Search for Python content
        results, _, _ = await store.search("python programming", top_k=1)
        
        assert len(results) == 1
        assert "Python" in results[0].content
