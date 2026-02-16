"""Integration tests with real LLM calls.

These tests make actual API calls and cost money.
Run with: pytest tests/test_llm_integration.py -v --run-integration
Requires: LLM_API_KEY env var set
"""
import os

import pytest

from alfred.memory import MemoryCompactor, MemoryManager

pytestmark = [
    pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION_TESTS"),
        reason="Set RUN_INTEGRATION_TESTS=1 to run (costs money)"
    ),
    pytest.mark.skipif(
        not os.getenv("LLM_API_KEY"),
        reason="LLM_API_KEY not set"
    ),
]


@pytest.fixture
def memory_manager(tmp_path):
    """Create a memory manager with temp directory."""
    return MemoryManager(tmp_path)


@pytest.mark.asyncio
async def test_real_zai_compaction(memory_manager):
    """Test compaction with real Z.AI API call."""
    # Create test memory files
    old_file = memory_manager.memory_dir / "2026-02-14.md"
    old_file.write_text(
        "# 2026-02-14\n\n"
        "## Key Decisions\n"
        "- Decided to use Python for the project\n"
        "- Chose FastAPI over Flask\n\n"
        "## Notes\n"
        "- User prefers concise responses\n"
        "- Project deadline is March 1st\n"
    )

    compactor = MemoryCompactor(
        memory_manager,
        llm_provider="zai",
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_model="glm-4-flash"
    )

    result = await compactor.compact()

    assert result["compacted"] == 1
    assert result["archived"] == 1

    # Check MEMORY.md was created with real LLM output
    memory_md = memory_manager.workspace_dir / "MEMORY.md"
    assert memory_md.exists()
    content = memory_md.read_text()

    # Should contain some summarization (not just raw content)
    assert len(content) > 100
    print(f"\n\n=== Z.AI Compaction Output ===\n{content[:500]}...\n")


@pytest.mark.asyncio
async def test_real_openai_compaction(memory_manager):
    """Test compaction with real OpenAI API call."""
    pytest.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set"
    )

    # Create test memory files
    old_file = memory_manager.memory_dir / "2026-02-14.md"
    old_file.write_text(
        "# 2026-02-14\n\n"
        "## Key Decisions\n"
        "- Decided to use Python for the project\n"
        "- Chose FastAPI over Flask\n\n"
        "## Notes\n"
        "- User prefers concise responses\n"
        "- Project deadline is March 1st\n"
    )

    compactor = MemoryCompactor(
        memory_manager,
        llm_provider="openai",
        llm_api_key=os.getenv("OPENAI_API_KEY"),
        llm_model="gpt-3.5-turbo"
    )

    result = await compactor.compact()

    assert result["compacted"] == 1
    assert result["archived"] == 1

    # Check MEMORY.md was created
    memory_md = memory_manager.workspace_dir / "MEMORY.md"
    assert memory_md.exists()
    content = memory_md.read_text()

    print(f"\n\n=== OpenAI Compaction Output ===\n{content[:500]}...\n")


@pytest.mark.asyncio
async def test_custom_prompt_with_real_llm(memory_manager):
    """Test custom prompt with real LLM."""
    # Create test memory files
    old_file = memory_manager.memory_dir / "2026-02-14.md"
    old_file.write_text(
        "# 2026-02-14\n\n"
        "## Key Decisions\n"
        "- Decided to use Python\n"
        "- Chose PostgreSQL over MySQL\n\n"
        "## Random Thoughts\n"
        "- Had coffee at 3pm\n"
        "- Weather was nice\n"
    )

    compactor = MemoryCompactor(
        memory_manager,
        llm_provider="zai",
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_model="glm-4-flash"
    )

    # Custom prompt focusing only on technical decisions
    custom_prompt = (
        "You are a memory compaction assistant. "
        "Extract ONLY the technical decisions (programming languages, frameworks, databases). "
        "Ignore personal notes like coffee, weather, etc. "
        "Output as a simple bullet list."
    )

    result = await compactor.compact(custom_prompt=custom_prompt)

    assert result["compacted"] == 1

    memory_md = memory_manager.workspace_dir / "MEMORY.md"
    content = memory_md.read_text()

    # Should mention technical stuff
    assert "Python" in content or "PostgreSQL" in content
    print(f"\n\n=== Custom Prompt Output ===\n{content}\n")


@pytest.mark.asyncio
async def test_multiple_files_compaction(memory_manager):
    """Test compacting multiple memory files."""
    # Create multiple memory files
    for i, date in enumerate(["2026-02-10", "2026-02-11", "2026-02-12"]):
        f = memory_manager.memory_dir / f"{date}.md"
        f.write_text(
            f"# {date}\n\n"
            f"## Key Decisions\n"
            f"- Decision {i+1}: Important choice made\n"
            f"- Lesson learned: Something valuable\n\n"
        )

    compactor = MemoryCompactor(
        memory_manager,
        llm_provider="zai",
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_model="glm-4-flash"
    )

    result = await compactor.compact()

    assert result["compacted"] == 3
    assert result["archived"] == 3

    # All files should be archived
    archive_dir = memory_manager.memory_dir / "archive"
    assert len(list(archive_dir.glob("*.md"))) == 3

    print("\n\n=== Multi-File Compaction ===")
    print(f"Compacted {result['compacted']} files")
    memory_md = memory_manager.workspace_dir / "MEMORY.md"
    print(f"Output length: {len(memory_md.read_text())} chars\n")
