"""Tests for memory system."""
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from alfred.memory import MemoryCompactor, MemoryManager


@pytest.mark.asyncio
async def test_memory_manager_creates_directories(tmp_path: Path):
    """Test that MemoryManager creates required directories."""
    _ = MemoryManager(tmp_path)

    assert (tmp_path / "memory").exists()
    assert (tmp_path / "notes").exists()


def test_get_daily_memory_path(tmp_path: Path):
    """Test daily memory path generation."""
    manager = MemoryManager(tmp_path)

    date = datetime(2026, 2, 15)
    path = manager.get_daily_memory_path(date)

    assert path.name == "2026-02-15.md"
    assert path.parent.name == "memory"


@pytest.mark.asyncio
async def test_append_to_daily_creates_file(tmp_path: Path):
    """Test appending to daily memory creates file."""
    manager = MemoryManager(tmp_path)

    await manager.append_to_daily("Test note", section="Notes")

    path = manager.get_daily_memory_path()
    assert path.exists()

    content = path.read_text()
    assert "# " in content
    assert "## Notes" in content
    assert "Test note" in content


@pytest.mark.asyncio
async def test_append_to_daily_appends(tmp_path: Path):
    """Test appending multiple notes."""
    manager = MemoryManager(tmp_path)

    await manager.append_to_daily("First note")
    await manager.append_to_daily("Second note")

    path = manager.get_daily_memory_path()
    content = path.read_text()

    assert "First note" in content
    assert "Second note" in content


def test_get_all_memories(tmp_path: Path):
    """Test getting all memory files except today."""
    manager = MemoryManager(tmp_path)

    today = manager.get_daily_memory_path()
    today.write_text("# Today\n")

    yesterday = manager.get_daily_memory_path(datetime.now() - timedelta(days=1))
    yesterday.write_text("# Yesterday\n")

    all_memories = manager.get_all_memories()

    assert len(all_memories) == 1
    assert yesterday in all_memories
    assert today not in all_memories


@pytest.mark.asyncio
async def test_read_memory_md_exists(tmp_path: Path):
    """Test reading MEMORY.md when it exists."""
    manager = MemoryManager(tmp_path)

    memory_path = tmp_path / "MEMORY.md"
    memory_path.write_text("# Memory\nTest content")

    content = await manager.read_memory_md()

    assert content is not None
    assert "Test content" in content


@pytest.mark.asyncio
async def test_read_memory_md_not_exists(tmp_path: Path):
    """Test reading MEMORY.md when it doesn't exist."""
    manager = MemoryManager(tmp_path)

    content = await manager.read_memory_md()

    assert content is None


@pytest.mark.asyncio
async def test_update_memory_md(tmp_path: Path):
    """Test updating MEMORY.md."""
    manager = MemoryManager(tmp_path)

    await manager.update_memory_md("# Updated Memory\nNew content")

    memory_path = tmp_path / "MEMORY.md"
    assert memory_path.exists()
    assert "Updated Memory" in memory_path.read_text()


@pytest.mark.asyncio
async def test_memory_compactor_no_memories(tmp_path: Path):
    """Test compaction when no memories exist."""
    manager = MemoryManager(tmp_path)
    compactor = MemoryCompactor(manager)

    result = await compactor.compact()

    assert result["compacted"] == 0
    assert "flushed" in result


@pytest.mark.asyncio
async def test_memory_compactor_with_pending(tmp_path: Path):
    """Test compaction flushes pending memories."""
    manager = MemoryManager(tmp_path)
    compactor = MemoryCompactor(manager)

    await compactor.append_pending("Pending note 1", section="Notes")
    await compactor.append_pending("Pending note 2", section="Decisions")

    yesterday = datetime.now() - timedelta(days=1)
    yesterday_path = manager.get_daily_memory_path(yesterday)
    yesterday_path.write_text("# Yesterday\n\n## Notes\n\n- Old note\n")

    result = await compactor.compact()

    assert result["compacted"] == 1
    assert result["flushed"] == 2
    assert result["archived"] == 1


@pytest.mark.asyncio
async def test_memory_compactor_archives_files(tmp_path: Path):
    """Test that compaction archives processed files."""
    manager = MemoryManager(tmp_path)
    compactor = MemoryCompactor(manager)

    yesterday = datetime.now() - timedelta(days=1)
    yesterday_path = manager.get_daily_memory_path(yesterday)
    yesterday_path.write_text("# Yesterday\n")

    await compactor.compact()

    archive_dir = tmp_path / "memory" / "archive"
    assert archive_dir.exists()
    assert len(list(archive_dir.glob("*.md"))) == 1
    assert not yesterday_path.exists()


@pytest.mark.asyncio
async def test_memory_compactor_fallback_without_api_key(tmp_path: Path):
    """Test compaction falls back when no API key."""
    manager = MemoryManager(tmp_path)
    compactor = MemoryCompactor(
        manager,
        llm_provider="zai",
        llm_api_key="",
        llm_model=""
    )

    yesterday = datetime.now() - timedelta(days=1)
    yesterday_path = manager.get_daily_memory_path(yesterday)
    yesterday_path.write_text("# Yesterday\n\n## Notes\n\n- Test note\n")

    result = await compactor.compact()

    assert result["compacted"] == 1

    memory_md = tmp_path / "MEMORY.md"
    assert memory_md.exists()
    content = memory_md.read_text()
    assert "Generated without LLM" in content or "Test note" in content
