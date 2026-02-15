"""Tests for memory compactor with LLM integration."""

import pytest

from alfred.memory import MemoryCompactor, MemoryManager


@pytest.fixture
def memory_manager(tmp_path):
    """Create a memory manager with temp directory."""
    return MemoryManager(tmp_path)


@pytest.mark.asyncio
async def test_memory_compactor_flush_pending(memory_manager):
    """Test that pending memories are flushed before compaction."""
    compactor = MemoryCompactor(memory_manager)

    # Add some pending memories
    await compactor.append_pending("Test memory 1", "Key Decisions")
    await compactor.append_pending("Test memory 2", "Notes")

    # Flush them
    count = await compactor._flush_pending()

    assert count == 2
    assert len(compactor._pending_memories) == 0

    # Verify they were written
    daily = memory_manager.get_daily_memory_path()
    assert daily.exists()
    content = daily.read_text()
    assert "Test memory 1" in content
    assert "Test memory 2" in content


@pytest.mark.asyncio
async def test_memory_compactor_get_all_memories(memory_manager):
    """Test getting all memories excludes today."""
    compactor = MemoryCompactor(memory_manager)

    # Create some memory files
    yesterday = memory_manager.memory_dir / "2026-02-14.md"
    yesterday.write_text("# Yesterday\n")

    old = memory_manager.memory_dir / "2026-02-10.md"
    old.write_text("# Old\n")

    memories = memory_manager.get_all_memories()

    # Should get both (today won't match)
    assert len(memories) == 2


@pytest.mark.asyncio
async def test_memory_compactor_archive_files(memory_manager):
    """Test archiving memory files."""
    compactor = MemoryCompactor(memory_manager)

    # Create test files
    file1 = memory_manager.memory_dir / "2026-02-14.md"
    file1.write_text("# Test\n")
    file2 = memory_manager.memory_dir / "2026-02-13.md"
    file2.write_text("# Test 2\n")

    archived = await compactor._archive_files([file1, file2])

    assert archived == 2
    assert not file1.exists()
    assert not file2.exists()
    assert (memory_manager.memory_dir / "archive" / "2026-02-14.md").exists()


@pytest.mark.asyncio
async def test_memory_compactor_compact_no_memories(memory_manager):
    """Test compacting when no memories exist."""
    compactor = MemoryCompactor(memory_manager)

    result = await compactor.compact()

    assert result["compacted"] == 0
    assert result["flushed"] == 0


@pytest.mark.asyncio
async def test_memory_compactor_compact_with_pending(memory_manager):
    """Test compacting flushes pending memories."""
    compactor = MemoryCompactor(memory_manager)

    # Add pending
    await compactor.append_pending("Pending memory")

    # Create some old memory files
    old_file = memory_manager.memory_dir / "2026-02-14.md"
    old_file.write_text("# 2026-02-14\n\nOld memory content\n")

    result = await compactor.compact()

    assert result["compacted"] == 1
    assert result["flushed"] == 1  # Pending memory was flushed
    assert result["archived"] == 1


@pytest.mark.asyncio
async def test_memory_compactor_custom_prompt(memory_manager):
    """Test that custom prompt is passed to LLM."""
    compactor = MemoryCompactor(memory_manager)

    custom_prompt = "Focus only on technical decisions"

    # Create a test file
    old_file = memory_manager.memory_dir / "2026-02-14.md"
    old_file.write_text("# 2026-02-14\n\nTest content\n")

    # Mock the LLM call to capture the prompt
    called_with_prompt = None

    async def mock_call(memories, prompt):
        nonlocal called_with_prompt
        called_with_prompt = prompt
        return "# Compacted\n\nTest summary"

    compactor._call_compaction_llm = mock_call

    await compactor.compact(custom_prompt=custom_prompt)

    assert called_with_prompt == custom_prompt


@pytest.mark.asyncio
async def test_memory_compactor_llm_fallback_without_api_key(memory_manager):
    """Test fallback when no API key provided."""
    compactor = MemoryCompactor(memory_manager, llm_api_key="")

    # Create test file
    old_file = memory_manager.memory_dir / "2026-02-14.md"
    old_file.write_text("# 2026-02-14\n\nTest content that is longer than 2000 chars " * 50)

    result = await compactor.compact()

    assert result["compacted"] == 1

    # Check MEMORY.md was created with fallback content
    memory_md = memory_manager.workspace_dir / "MEMORY.md"
    assert memory_md.exists()
    content = memory_md.read_text()
    assert "Generated without LLM" in content
