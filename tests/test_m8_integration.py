"""M8 Integration & Testing - End-to-end validation for PRD #102.

Tests the complete flow: file loading → placeholder resolution → memory usage
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from src.config import Config
from src.context import ContextLoader
from src.templates import TemplateManager


@pytest.fixture
def test_config(tmp_path: Path, monkeypatch):
    """Create a test Config with mocked environment variables."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("KIMI_API_KEY", "test")
    monkeypatch.setenv("KIMI_BASE_URL", "https://test.moonshot.cn/v1")

    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir(exist_ok=True)

    return Config(
        telegram_bot_token="test",
        openai_api_key="test",
        kimi_api_key="test",
        kimi_base_url="https://test.moonshot.cn/v1",
        default_llm_provider="kimi",
        embedding_model="text-embedding-3-small",
        chat_model="kimi-k2-5",
        workspace_dir=workspace_dir,
        memory_dir=tmp_path / "memory",
        context_files={},
    )


class TestEndToEndContextLoading:
    """End-to-end test: file loading → placeholder resolution → assembled context."""

    @pytest.mark.asyncio
    async def test_full_context_assembly_with_placeholders(
        self, tmp_path: Path, test_config: Config
    ) -> None:
        """Complete flow: all context files load with placeholders resolved."""
        # Setup workspace with full template structure
        workspace_dir = test_config.workspace_dir

        manager = TemplateManager(tmp_path)
        template_dir = manager.template_dir

        # Copy all templates to workspace
        for template_file in ["SYSTEM.md", "AGENTS.md", "SOUL.md", "USER.md"]:
            content = manager.load_template(template_file)
            if content:
                (workspace_dir / template_file).write_text(content)

        # Copy prompts directory
        prompts_src = template_dir / "prompts"
        prompts_dst = workspace_dir / "prompts"
        if prompts_src.exists():
            import shutil
            shutil.copytree(prompts_src, prompts_dst, dirs_exist_ok=True)

        # Load through ContextLoader using test config
        test_config.workspace_dir = workspace_dir
        test_config.context_files = {
            "system": workspace_dir / "SYSTEM.md",
            "agents": workspace_dir / "AGENTS.md",
            "soul": workspace_dir / "SOUL.md",
            "user": workspace_dir / "USER.md",
        }
        loader = ContextLoader(test_config)

        # Load all context files
        files = await loader.load_all()

        # Verify all files loaded
        assert "system" in files
        assert "agents" in files
        assert "soul" in files
        assert "user" in files

        # Verify placeholders were resolved (no {{prompts/agents/...}} left)
        for name, file in files.items():
            assert "{{prompts/agents/" not in file.content, (
                f"{name} has unresolved placeholders"
            )

        # Verify AGENTS.md content is fully resolved
        agents_content = files["agents"].content
        assert "## Beta Product Notice" in agents_content
        assert "## Pre-Flight Check" in agents_content
        assert "## Test-Driven Development" in agents_content
        assert "## Rule Index" in agents_content

    @pytest.mark.asyncio
    async def test_context_assembly_for_llm_prompt(
        self, tmp_path: Path, test_config: Config
    ) -> None:
        """Assembled context is ready for LLM prompt injection."""
        # Setup minimal workspace
        workspace_dir = test_config.workspace_dir

        manager = TemplateManager(tmp_path)

        # Create minimal context files
        (workspace_dir / "SYSTEM.md").write_text("# System\nMemory architecture")
        (workspace_dir / "SOUL.md").write_text("# Soul\nPersonality here")
        (workspace_dir / "USER.md").write_text("# User\nPreferences here")

        # Create AGENTS.md with placeholders
        agents_template = manager.load_template("AGENTS.md")
        (workspace_dir / "AGENTS.md").write_text(agents_template)

        # Copy prompts
        template_dir = manager.template_dir
        prompts_src = template_dir / "prompts"
        prompts_dst = workspace_dir / "prompts"
        if prompts_src.exists():
            import shutil
            shutil.copytree(prompts_src, prompts_dst, dirs_exist_ok=True)

        # Assemble context using test config
        test_config.workspace_dir = workspace_dir
        test_config.context_files = {
            "system": workspace_dir / "SYSTEM.md",
            "agents": workspace_dir / "AGENTS.md",
            "soul": workspace_dir / "SOUL.md",
            "user": workspace_dir / "USER.md",
        }
        loader = ContextLoader(test_config)
        assembled = await loader.assemble()

        # Verify assembled context structure
        assert assembled.system_prompt is not None
        assert len(assembled.system_prompt) > 1000  # Should be substantial

        # Verify sections are present
        assert "# SYSTEM" in assembled.system_prompt
        assert "# AGENTS" in assembled.system_prompt
        assert "# SOUL" in assembled.system_prompt
        assert "# USER" in assembled.system_prompt

        # Verify placeholders resolved in final prompt
        assert "{{prompts/agents/" not in assembled.system_prompt

    @pytest.mark.asyncio
    async def test_nested_placeholder_resolution(self, tmp_path: Path) -> None:
        """Nested placeholders (A includes B includes C) resolve correctly."""
        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        # Create nested structure
        prompts_dir = workspace_dir / "prompts"
        prompts_dir.mkdir()

        (prompts_dir / "level3.md").write_text("Level 3 content")
        (prompts_dir / "level2.md").write_text("{{prompts/level3.md}}\nLevel 2 content")
        (prompts_dir / "level1.md").write_text("{{prompts/level2.md}}\nLevel 1 content")

        # Main file includes level1
        (workspace_dir / "SYSTEM.md").write_text("# System\n{{prompts/level1.md}}")
        (workspace_dir / "AGENTS.md").write_text("# Agents")
        (workspace_dir / "SOUL.md").write_text("# Soul")
        (workspace_dir / "USER.md").write_text("# User")

        # Load and verify nesting works
        from src.config import Config as RealConfig
        config = RealConfig(
            telegram_bot_token="test",
            openai_api_key="test",
            kimi_api_key="test",
            kimi_base_url="https://test.moonshot.cn/v1",
            default_llm_provider="kimi",
            embedding_model="text-embedding-3-small",
            chat_model="kimi-k2-5",
            workspace_dir=workspace_dir,
            memory_dir=workspace_dir / "memory",
            context_files={},
        )
        loader = ContextLoader(config)

        system_file = await loader.load_file("system", workspace_dir / "SYSTEM.md")

        # All levels should be resolved
        assert "Level 3 content" in system_file.content
        assert "Level 2 content" in system_file.content
        assert "Level 1 content" in system_file.content


class TestOldModelReferencesRemoved:
    """Verify no references to old three-tier model remain."""

    def test_memory_schema_uses_simplified_model(self, tmp_path: Path) -> None:
        """MemoryEntry uses simplified schema (no tier field)."""
        from src.memory import MemoryEntry
        from datetime import datetime

        # Create memory - should not have "tier" field
        memory = MemoryEntry(
            content="Test memory",
            timestamp=datetime.now(),
            role="user",
            embedding=[0.1] * 384,
        )

        # Should have permanent flag (new model)
        assert hasattr(memory, "permanent")

        # Should NOT have tier field (old model)
        assert not hasattr(memory, "tier")


class TestPerformanceWithManyPlaceholders:
    """Performance tests for placeholder resolution."""

    @pytest.mark.asyncio
    async def test_many_placeholders_performance(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Resolution completes quickly even with many placeholders."""
        import time

        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
        monkeypatch.setenv("OPENAI_API_KEY", "test")
        monkeypatch.setenv("KIMI_API_KEY", "test")
        monkeypatch.setenv("KIMI_BASE_URL", "https://test.moonshot.cn/v1")

        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        # Create many small prompt files
        prompts_dir = workspace_dir / "prompts" / "agents"
        prompts_dir.mkdir(parents=True)

        for i in range(20):
            (prompts_dir / f"section{i}.md").write_text(
                f"## Section {i}\nContent here\n"
            )

        # Create AGENTS.md with many placeholders
        placeholders = "\n".join(
            [f"{{{{prompts/agents/section{i}.md}}}}" for i in range(20)]
        )
        (workspace_dir / "AGENTS.md").write_text(f"# Agents\n{placeholders}")

        (workspace_dir / "SYSTEM.md").write_text("# System\nTest")
        (workspace_dir / "SOUL.md").write_text("# Soul\nTest")
        (workspace_dir / "USER.md").write_text("# User\nTest")

        # Measure resolution time
        config = Config(
            telegram_bot_token="test",
            openai_api_key="test",
            kimi_api_key="test",
            kimi_base_url="https://test.moonshot.cn/v1",
            default_llm_provider="kimi",
            embedding_model="text-embedding-3-small",
            chat_model="kimi-k2-5",
            workspace_dir=workspace_dir,
            memory_dir=workspace_dir / "memory",
            context_files={},
        )
        loader = ContextLoader(config)

        start = time.time()
        agents_file = await loader.load_file("agents", workspace_dir / "AGENTS.md")
        elapsed = time.time() - start

        # Should complete in under 1 second for 20 placeholders
        assert elapsed < 1.0, f"Resolution too slow: {elapsed:.2f}s"

        # All should be resolved
        assert agents_file.content.count("## Section") == 20

    @pytest.mark.asyncio
    async def test_large_prompt_size(self, tmp_path: Path, monkeypatch) -> None:
        """System handles large resolved prompts efficiently."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
        monkeypatch.setenv("OPENAI_API_KEY", "test")
        monkeypatch.setenv("KIMI_API_KEY", "test")
        monkeypatch.setenv("KIMI_BASE_URL", "https://test.moonshot.cn/v1")

        workspace_dir = tmp_path / "workspace"
        workspace_dir.mkdir()

        # Create large content file
        prompts_dir = workspace_dir / "prompts"
        prompts_dir.mkdir()

        large_content = "Lorem ipsum dolor sit amet.\n" * 1000  # ~40KB
        (prompts_dir / "large.md").write_text(large_content)

        # Include it multiple times
        (workspace_dir / "AGENTS.md").write_text(
            "# Agents\n{{prompts/large.md}}\n{{prompts/large.md}}"
        )
        (workspace_dir / "SYSTEM.md").write_text("# System")
        (workspace_dir / "SOUL.md").write_text("# Soul")
        (workspace_dir / "USER.md").write_text("# User")

        config = Config(
            telegram_bot_token="test",
            openai_api_key="test",
            kimi_api_key="test",
            kimi_base_url="https://test.moonshot.cn/v1",
            default_llm_provider="kimi",
            embedding_model="text-embedding-3-small",
            chat_model="kimi-k2-5",
            workspace_dir=workspace_dir,
            memory_dir=workspace_dir / "memory",
            context_files={},
        )
        loader = ContextLoader(config)

        agents_file = await loader.load_file("agents", workspace_dir / "AGENTS.md")

        # Should handle ~80KB resolved content
        assert len(agents_file.content) > 50000


class TestMemorySystemIntegration:
    """Integration tests for memory system components."""

    def test_memory_has_required_fields(self) -> None:
        """MemoryEntry has required fields for simplified model."""
        from datetime import datetime
        from src.memory import MemoryEntry

        memory = MemoryEntry(
            content="Test memory",
            timestamp=datetime.now(),
            role="user",
            embedding=[0.1] * 384,
        )

        # Should have permanent flag (simplified model)
        assert hasattr(memory, "permanent")
        assert memory.permanent is False  # Default

        # Should have entry_id
        assert hasattr(memory, "entry_id")
        assert memory.entry_id is not None  # Auto-generated

        # Should NOT have tier field (old three-tier model)
        assert not hasattr(memory, "tier")

    def test_permanent_flag_exists(self) -> None:
        """MemoryEntry has permanent flag field."""
        from datetime import datetime
        from src.memory import MemoryEntry

        memory = MemoryEntry(
            content="Test memory",
            timestamp=datetime.now(),
            role="user",
            embedding=[0.1] * 384,
            permanent=True,
        )

        assert memory.permanent is True
        assert hasattr(memory, "permanent")

    def test_search_sessions_tool_exists(self) -> None:
        """search_sessions tool module exists and has correct class."""
        from src.tools.search_sessions import SearchSessionsTool

        # Verify the class exists and has the right name
        assert SearchSessionsTool.name == "search_sessions"
        assert SearchSessionsTool.description is not None
