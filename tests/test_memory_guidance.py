"""Tests for memory guidance prompt integration."""

import pytest

from src.placeholders import resolve_file_includes
from src.templates import TemplateManager


class TestMemoryGuidancePrompt:
    """Test memory-system.md prompt content and integration."""

    def test_memory_system_prompt_exists(self, tmp_path):
        """memory-system.md template exists in prompts/agents/."""
        manager = TemplateManager(tmp_path)
        template_path = (
            manager.template_dir / "prompts" / "agents" / "memory-system.md"
        )
        assert template_path.exists()

    def test_memory_system_prompt_has_decision_framework(self, tmp_path):
        """Prompt includes decision framework table."""
        manager = TemplateManager(tmp_path)
        content = (
            manager.template_dir / "prompts" / "agents" / "memory-system.md"
        ).read_text()

        assert "| Information Type |" in content
        assert "| Store In |" in content
        assert "| Example |" in content
        assert "USER.md" in content
        assert "remember()" in content
        assert "search_sessions" in content

    def test_memory_system_prompt_has_ttl_explanation(self, tmp_path):
        """Prompt includes TTL behavior explanation."""
        manager = TemplateManager(tmp_path)
        content = (
            manager.template_dir / "prompts" / "agents" / "memory-system.md"
        ).read_text()

        assert "90 days" in content
        assert "permanent" in content.lower() or "permanent=True" in content
        assert "expire" in content.lower()

    def test_memory_system_prompt_has_tool_reference(self, tmp_path):
        """Prompt includes tool reference section."""
        manager = TemplateManager(tmp_path)
        content = (
            manager.template_dir / "prompts" / "agents" / "memory-system.md"
        ).read_text()

        assert "remember(content" in content
        assert "search_memories" in content
        assert "search_sessions" in content

    def test_memory_system_prompt_has_examples(self, tmp_path):
        """Prompt includes concrete examples for model."""
        manager = TemplateManager(tmp_path)
        content = (
            manager.template_dir / "prompts" / "agents" / "memory-system.md"
        ).read_text()

        assert "Examples for files:" in content
        assert "Examples for memories:" in content
        assert "→ USER.md" in content or "→ SOUL.md" in content


class TestAgentsMdPlaceholder:
    """Test AGENTS.md includes memory guidance placeholder."""

    def test_agents_md_has_placeholder(self, tmp_path):
        """AGENTS.md references memory-system.md via placeholder."""
        manager = TemplateManager(tmp_path)
        content = manager.load_template("AGENTS.md")

        assert "{{prompts/agents/memory-system.md}}" in content

    def test_agents_md_placeholder_resolves(self, tmp_path):
        """Placeholder resolves to memory guidance content."""
        manager = TemplateManager(tmp_path)
        manager.ensure_prompts_exist()

        content = manager.load_template("AGENTS.md")
        resolved = resolve_file_includes(content, tmp_path)

        assert "<!-- included: prompts/agents/memory-system.md -->" in resolved
        assert "## Memory System" in resolved
        assert "### 1. FILES" in resolved
        assert "### 2. MEMORIES" in resolved
        assert "### 3. SESSION ARCHIVE" in resolved


class TestMemoryGuidanceInContext:
    """Test memory guidance appears in assembled context."""

    @pytest.mark.asyncio
    async def test_memory_guidance_in_system_prompt(self, tmp_path):
        """Memory guidance appears in assembled system prompt."""
        from src.config import Config
        from src.context import ContextLoader

        # Setup workspace with templates
        manager = TemplateManager(tmp_path)
        manager.ensure_prompts_exist()
        manager.ensure_all_exist()

        # Verify AGENTS.md has the placeholder
        agents_content = (tmp_path / "AGENTS.md").read_text()
        assert "{{prompts/agents/memory-system.md}}" in agents_content

        # Create config
        config = Config(
            telegram_bot_token="test",
            openai_api_key="test",
            kimi_api_key="test",
            kimi_base_url="https://test.com",
            default_llm_provider="kimi",
            embedding_model="test",
            chat_model="test",
            workspace_dir=tmp_path,
            memory_dir=tmp_path / "memory",
            context_files={
                "system": tmp_path / "SYSTEM.md",
                "agents": tmp_path / "AGENTS.md",
                "soul": tmp_path / "SOUL.md",
                "user": tmp_path / "USER.md",
            },
        )

        # Load and assemble context
        loader = ContextLoader(config)
        assembled = await loader.assemble()

        # Debug output
        print("AGENTS content from assembled.agents:")
        print(assembled.agents[:500])
        print("\nSystem prompt (AGENTS section):")
        agents_section = assembled.system_prompt.find("# AGENTS")
        print(assembled.system_prompt[agents_section:agents_section + 1000])

        # Verify memory guidance is in system prompt
        assert "## Memory System" in assembled.system_prompt, "Memory System section not found"
        assert "Decision Framework" in assembled.system_prompt, "Decision Framework not found"
        assert "90 days" in assembled.system_prompt, "TTL explanation not found"

    @pytest.mark.asyncio
    async def test_memory_guidance_placement(self, tmp_path):
        """Memory guidance appears early in system prompt (via AGENTS.md)."""
        from src.config import Config
        from src.context import ContextLoader

        manager = TemplateManager(tmp_path)
        manager.ensure_prompts_exist()
        manager.ensure_all_exist()

        config = Config(
            telegram_bot_token="test",
            openai_api_key="test",
            kimi_api_key="test",
            kimi_base_url="https://test.com",
            default_llm_provider="kimi",
            embedding_model="test",
            chat_model="test",
            workspace_dir=tmp_path,
            memory_dir=tmp_path / "memory",
            context_files={
                "system": tmp_path / "SYSTEM.md",
                "agents": tmp_path / "AGENTS.md",
                "soul": tmp_path / "SOUL.md",
                "user": tmp_path / "USER.md",
            },
        )

        loader = ContextLoader(config)
        assembled = await loader.assemble()

        # Memory guidance should be in AGENTS section (after SYSTEM, before SOUL)
        agents_pos = assembled.system_prompt.find("# AGENTS")
        memory_pos = assembled.system_prompt.find("## Memory System")
        soul_pos = assembled.system_prompt.find("# SOUL")

        assert agents_pos != -1
        assert memory_pos != -1
        assert soul_pos != -1

        # Memory guidance should be in AGENTS section (after # AGENTS header)
        assert agents_pos < memory_pos < soul_pos


class TestPromptsDirectoryStructure:
    """Test prompts directory structure supports M2 and M6."""

    def test_prompts_agents_subdir_exists(self, tmp_path):
        """prompts/agents/ subdirectory structure exists."""
        manager = TemplateManager(tmp_path)
        manager.ensure_prompts_exist()

        agents_dir = tmp_path / "prompts" / "agents"
        assert agents_dir.exists()
        assert agents_dir.is_dir()

    def test_agents_subdirectory_copied_recursively(self, tmp_path):
        """Subdirectories under prompts/ are copied recursively."""
        manager = TemplateManager(tmp_path)
        result = manager.ensure_prompts_exist()

        # Should copy memory-system.md from prompts/agents/
        memory_file = result / "agents" / "memory-system.md"
        assert memory_file.exists()

    def test_existing_prompts_not_overwritten(self, tmp_path):
        """Existing prompt files are not overwritten."""
        manager = TemplateManager(tmp_path)

        # First call creates files
        manager.ensure_prompts_exist()

        # Modify a file
        memory_file = tmp_path / "prompts" / "agents" / "memory-system.md"
        original_content = memory_file.read_text()
        memory_file.write_text("MODIFIED")

        # Second call should not overwrite
        manager.ensure_prompts_exist()
        assert memory_file.read_text() == "MODIFIED"
