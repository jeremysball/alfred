"""Tests for SYSTEM.md integration - M1 of unified memory system."""

import tempfile
from pathlib import Path

import pytest

from alfred.config import Config
from alfred.context import ContextLoader
from alfred.templates import TemplateManager


# Fixtures
@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_templates_with_system(temp_workspace):
    """Create a templates directory with SYSTEM.md and other templates."""
    template_dir = temp_workspace / "templates"
    template_dir.mkdir()

    # Create all required templates including SYSTEM.md
    (template_dir / "SYSTEM.md").write_text(
        "# System\n\n## Memory Architecture\n\nThree storage mechanisms.\n\n## Cron Job Capabilities\n\nWhen writing cron jobs...\n"
    )
    (template_dir / "AGENTS.md").write_text(
        "# Agent Behavior Rules\n\n1. Permission First\n2. Conventional Commits\n3. Simple Correctness\n"
    )
    (template_dir / "SOUL.md").write_text("# Soul\n")
    (template_dir / "USER.md").write_text("# User Profile\n")
    (template_dir / "TOOLS.md").write_text("# Tools Config\n")

    return temp_workspace


@pytest.fixture
def manager(temp_templates_with_system):
    """Create a TemplateManager with temp templates."""
    return TemplateManager(temp_templates_with_system)


class TestSystemMdInAutoCreateTemplates:
    """Test that SYSTEM.md is in AUTO_CREATE_TEMPLATES."""

    def test_system_md_in_auto_create_templates(self):
        """SYSTEM.md should be in AUTO_CREATE_TEMPLATES."""
        assert "SYSTEM.md" in TemplateManager.AUTO_CREATE_TEMPLATES

    def test_agents_md_in_auto_create_templates(self):
        """AGENTS.md should be in AUTO_CREATE_TEMPLATES."""
        assert "AGENTS.md" in TemplateManager.AUTO_CREATE_TEMPLATES

    def test_auto_create_count(self):
        """Should have 4 auto-create templates (TOOLS.md phased out)."""
        assert len(TemplateManager.AUTO_CREATE_TEMPLATES) == 4
        # Verify TOOLS.md is not in auto-create (phased out per PRD)
        assert "TOOLS.md" not in TemplateManager.AUTO_CREATE_TEMPLATES


class TestSystemMdTemplateExists:
    """Test SYSTEM.md template existence."""

    def test_system_template_exists(self, manager):
        """Test checking for SYSTEM.md template."""
        assert manager.template_exists("SYSTEM.md") is True

    def test_agents_template_exists(self, manager):
        """Test checking for AGENTS.md template."""
        assert manager.template_exists("AGENTS.md") is True


class TestSystemMdCreation:
    """Test creating SYSTEM.md from template."""

    def test_creates_system_md(self, manager):
        """Test creating SYSTEM.md from template."""
        path = manager.create_from_template("SYSTEM.md")

        assert path is not None
        assert path.exists()
        assert path.name == "SYSTEM.md"
        content = path.read_text()
        assert "# System" in content
        assert "Memory Architecture" in content

    def test_creates_agents_md(self, manager):
        """Test creating AGENTS.md from template."""
        path = manager.create_from_template("AGENTS.md")

        assert path is not None
        assert path.exists()
        assert path.name == "AGENTS.md"
        content = path.read_text()
        assert "# Agent Behavior Rules" in content
        assert "Permission First" in content

    def test_ensure_all_creates_system_and_agents(self, manager):
        """Test ensure_all_exist creates SYSTEM.md and AGENTS.md."""
        result = manager.ensure_all_exist()

        assert "SYSTEM.md" in result
        assert "AGENTS.md" in result
        assert result["SYSTEM.md"].exists()
        assert result["AGENTS.md"].exists()


class TestContextLoaderWithSystemMd:
    """Test ContextLoader with SYSTEM.md support."""

    @pytest.fixture
    def config_with_system(self, temp_templates_with_system):
        """Create a Config with SYSTEM.md in context_files."""
        workspace_dir = temp_templates_with_system
        return Config(
            telegram_bot_token="test_token",
            openai_api_key="test_openai_key",
            kimi_api_key="test_kimi_key",
            kimi_base_url="https://api.moonshot.cn/v1",
            default_llm_provider="kimi",
            embedding_model="text-embedding-3-small",
            chat_model="kimi-k2-5",
            workspace_dir=workspace_dir,
            memory_dir=workspace_dir / "memory",
            context_files={
                "system": workspace_dir / "SYSTEM.md",
                "agents": workspace_dir / "AGENTS.md",
                "soul": workspace_dir / "SOUL.md",
                "user": workspace_dir / "USER.md",
                # Note: TOOLS.md phased out (content moved to SYSTEM.md and USER.md)
            },
        )

    @pytest.fixture
    def loader_with_system(self, config_with_system):
        """Create a ContextLoader with SYSTEM.md support."""
        return ContextLoader(config_with_system)

    @pytest.mark.asyncio
    async def test_load_system_file(self, loader_with_system, config_with_system):
        """ContextLoader can load SYSTEM.md."""
        system_path = config_with_system.context_files["system"]

        context_file = await loader_with_system.load_file("system", system_path)

        assert context_file is not None
        assert "# System" in context_file.content
        assert "Memory Architecture" in context_file.content

    @pytest.mark.asyncio
    async def test_load_agents_file(self, loader_with_system, config_with_system):
        """ContextLoader can load AGENTS.md."""
        agents_path = config_with_system.context_files["agents"]

        context_file = await loader_with_system.load_file("agents", agents_path)

        assert context_file is not None
        assert "# Agent Behavior Rules" in context_file.content

    @pytest.mark.asyncio
    async def test_assemble_includes_system(self, loader_with_system, config_with_system):
        """Assembled context includes SYSTEM.md content."""
        # Load all files first
        for name, path in config_with_system.context_files.items():
            await loader_with_system.load_file(name, path)

        assembled = await loader_with_system.assemble()

        # SYSTEM.md should be in the system prompt
        assert "# SYSTEM" in assembled.system_prompt
        assert "Memory Architecture" in assembled.system_prompt

    @pytest.mark.asyncio
    async def test_system_appears_before_agents(self, loader_with_system, config_with_system):
        """SYSTEM.md appears before AGENTS.md in assembled prompt."""
        # Load all files
        for name, path in config_with_system.context_files.items():
            await loader_with_system.load_file(name, path)

        assembled = await loader_with_system.assemble()

        # Find positions
        system_pos = assembled.system_prompt.find("# SYSTEM")
        agents_pos = assembled.system_prompt.find("# AGENTS")

        assert system_pos != -1, "SYSTEM section not found"
        assert agents_pos != -1, "AGENTS section not found"
        assert system_pos < agents_pos, "SYSTEM should appear before AGENTS"


class TestSystemMdContent:
    """Test SYSTEM.md content requirements."""

    def test_system_md_has_memory_architecture(self, manager):
        """SYSTEM.md should contain memory architecture section."""
        content = manager.load_template("SYSTEM.md")

        assert content is not None
        assert "Memory Architecture" in content or "memory architecture" in content.lower()

    def test_system_md_has_cron_capabilities(self, manager):
        """SYSTEM.md should contain cron capabilities section."""
        content = manager.load_template("SYSTEM.md")

        assert content is not None
        assert "Cron Job Capabilities" in content or "cron" in content.lower()

    def test_agents_md_is_minimal(self, manager):
        """AGENTS.md should be minimal (no three-tier memory docs)."""
        content = manager.load_template("AGENTS.md")

        assert content is not None
        # Should NOT contain detailed three-tier memory documentation
        assert "three-tier" not in content.lower()
        assert "Tier 1" not in content
        assert "Tier 2" not in content
        assert "Tier 3" not in content

    def test_agents_md_has_core_rules(self, manager):
        """AGENTS.md should have core behavior rules."""
        content = manager.load_template("AGENTS.md")

        assert content is not None
        assert "Permission First" in content
        assert "Conventional Commits" in content
        assert "Simple Correctness" in content or "simple" in content.lower()

    def test_agents_md_no_operational_details(self, manager):
        """AGENTS.md should NOT contain operational details."""
        content = manager.load_template("AGENTS.md")

        assert content is not None
        # Should NOT contain uv run dotenv instructions
        assert "uv run dotenv" not in content
        # Should NOT contain XDG path details
        assert "XDG" not in content
        assert "~/.local/share" not in content
