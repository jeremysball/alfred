"""Tests for memory system."""
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from alfred.memory import MemoryCompactor, MemoryManager


@pytest.mark.asyncio
async def test_memory_manager_creates_directories(tmp_path: Path):
    """Test that MemoryManager creates required directories."""
    manager = MemoryManager(tmp_path)

    assert (tmp_path / "memory").exists()
    assert (tmp_path / "notes").exists()


@pytest.mark.asyncio
async def test_get_daily_memory_path(tmp_path: Path):
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


@pytest.mark.asyncio
async def test_get_recent_memories(tmp_path: Path):
    """Test getting recent memory files."""
    manager = MemoryManager(tmp_path)

    # Create memory files for today and yesterday
    today = manager.get_daily_memory_path()
    today.write_text("# Today\n")

    yesterday = manager.get_daily_memory_path(datetime.now() - timedelta(days=1))
    yesterday.write_text("# Yesterday\n")

    recent = manager.get_recent_memories(days=2)

    assert len(recent) == 2
    assert today in recent
    assert yesterday in recent


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

    result = await compactor.compact(days=7, strategy="summarize")

    assert result["compacted"] == 0
    assert "No memories" in result["message"]


@pytest.mark.asyncio
async def test_memory_compactor_summarize(tmp_path: Path):
    """Test summarize compaction strategy."""
    manager = MemoryManager(tmp_path)
    compactor = MemoryCompactor(manager)

    # Create a daily memory with key decisions
    await manager.append_to_daily("Made important decision X", section="Key Decisions")
    await manager.append_to_daily("Regular note", section="Notes")

    result = await compactor.compact(days=1, strategy="summarize")

    assert result["compacted"] == 1
    assert result["strategy"] == "summarize"


@pytest.mark.asyncio
async def test_memory_compactor_extract_decisions(tmp_path: Path):
    """Test extract decisions strategy."""
    manager = MemoryManager(tmp_path)
    compactor = MemoryCompactor(manager)

    # Create memory with decisions and actions
    await manager.append_to_daily("Decided to use Python", section="Key Decisions")
    await manager.append_to_daily("- [ ] Follow up on X", section="Action Items")

    result = await compactor.compact(days=1, strategy="extract_key_decisions")

    assert result["compacted"] == 1
    assert "Key Decisions" in result["result"]
    assert "Action Items" in result["result"]


@pytest.mark.asyncio
async def test_memory_compactor_archive(tmp_path: Path):
    """Test archive strategy moves files."""
    manager = MemoryManager(tmp_path)
    compactor = MemoryCompactor(manager)

    # Create yesterday's memory (not today's)
    yesterday = datetime.now() - timedelta(days=1)
    yesterday_path = manager.get_daily_memory_path(yesterday)
    yesterday_path.write_text("# Yesterday\n")

    result = await compactor.compact(days=2, strategy="archive")

    # File should be moved to archive
    archive_dir = tmp_path / "memory" / "archive"
    assert archive_dir.exists()
    assert len(list(archive_dir.glob("*.md"))) == 1
    assert not yesterday_path.exists()  # Moved from original


@pytest.mark.asyncio
async def test_memory_compactor_unknown_strategy(tmp_path: Path):
    """Test compaction with unknown strategy raises error."""
    manager = MemoryManager(tmp_path)
    compactor = MemoryCompactor(manager)

    # Create a memory file so there's something to compact
    await manager.append_to_daily("Test note")

    with pytest.raises(ValueError, match="Unknown strategy"):
        await compactor.compact(days=1, strategy="unknown")
