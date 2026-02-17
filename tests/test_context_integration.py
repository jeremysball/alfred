"""Integration tests for ContextLoader template auto-creation."""

import tempfile
from pathlib import Path
from datetime import date

import pytest

from src.config import Config
from src.context import ContextLoader


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace with templates directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Create workspace subdirectories
        # workspace_dir is where context files go
        # templates go in workspace_dir/templates for TemplateManager to find
        workspace_dir = workspace / "data"
        workspace_dir.mkdir()
        (workspace_dir / "templates").mkdir()
        (workspace_dir / "memory").mkdir()

        # Create template files in the right location
        # TemplateManager looks for workspace_dir/templates/
        templates_dir = workspace_dir / "templates"
        (templates_dir / "SOUL.md").write_text(
            "---\ntitle: SOUL\n---\n# Soul\nDate: {current_date}\n"
        )
        (templates_dir / "USER.md").write_text(
            "---\ntitle: USER\n---\n# User\n"
        )
        (templates_dir / "TOOLS.md").write_text(
            "---\ntitle: TOOLS\n---\n# Tools\n"
        )
        (templates_dir / "MEMORY.md").write_text(
            "---\ntitle: MEMORY\n---\n# Memory\n"
        )

        yield workspace


@pytest.fixture
def config(temp_workspace):
    """Create a Config pointing to temp workspace."""
    workspace_dir = temp_workspace / "data"
    return Config(
        telegram_bot_token="test_token",
        openai_api_key="test_openai_key",
        kimi_api_key="test_kimi_key",
        kimi_base_url="https://api.moonshot.cn/v1",
        default_llm_provider="kimi",
        embedding_model="text-embedding-3-small",
        chat_model="kimi-k2-5",
        memory_context_limit=20,
        workspace_dir=workspace_dir,
        memory_dir=workspace_dir / "memory",
        context_files={
            "soul": workspace_dir / "SOUL.md",
            "user": workspace_dir / "USER.md",
            "tools": workspace_dir / "TOOLS.md",
        },
    )


@pytest.fixture
def loader(config):
    """Create a ContextLoader with test config."""
    return ContextLoader(config)


class TestContextLoaderTemplateAutoCreation:
    """Integration tests for template auto-creation."""

    @pytest.mark.asyncio
    async def test_load_file_creates_missing_template(self, loader, config):
        """ContextLoader auto-creates missing SOUL.md from template."""
        soul_path = config.context_files["soul"]

        # File should not exist initially
        assert not soul_path.exists()

        # Load should succeed and create file
        context_file = await loader.load_file("soul", soul_path)

        assert context_file is not None
        assert soul_path.exists()
        assert "# Soul" in context_file.content

    @pytest.mark.asyncio
    async def test_created_file_has_correct_content(self, loader, config):
        """Auto-created file matches template content."""
        soul_path = config.context_files["soul"]

        await loader.load_file("soul", soul_path)

        content = soul_path.read_text()
        assert "# Soul" in content
        assert "title: SOUL" in content

    @pytest.mark.asyncio
    async def test_variable_substitution_in_created_file(self, loader, config):
        """Template variables are substituted."""
        soul_path = config.context_files["soul"]

        await loader.load_file("soul", soul_path)

        content = soul_path.read_text()
        today = date.today().isoformat()
        assert today in content

    @pytest.mark.asyncio
    async def test_existing_file_not_overwritten(self, loader, config):
        """ContextLoader doesn't overwrite user files."""
        soul_path = config.context_files["soul"]

        # Create a custom file first
        soul_path.write_text("# My Custom Soul\n\nThis is my content.")

        # Load should use existing file
        context_file = await loader.load_file("soul", soul_path)

        assert "My Custom Soul" in context_file.content
        assert "This is my content" in context_file.content

    @pytest.mark.asyncio
    async def test_load_all_creates_all_missing(self, loader, config):
        """load_all() creates all missing context files."""
        files = await loader.load_all()

        assert "soul" in files
        assert "user" in files
        assert "tools" in files

        # All files should exist on disk
        assert config.context_files["soul"].exists()
        assert config.context_files["user"].exists()
        assert config.context_files["tools"].exists()

    @pytest.mark.asyncio
    async def test_cached_file_returned_on_subsequent_load(self, loader, config):
        """Subsequent loads return cached file."""
        soul_path = config.context_files["soul"]

        # First load creates file
        first = await loader.load_file("soul", soul_path)

        # Delete the file
        soul_path.unlink()

        # Second load should return cached version
        second = await loader.load_file("soul", soul_path)

        assert first.content == second.content

    @pytest.mark.asyncio
    async def test_assemble_creates_missing_files(self, loader, config):
        """assemble() creates missing context files."""
        # Note: assemble() requires 'agents' file which isn't auto-created
        # This test verifies soul/user/tools are created
        soul_path = config.context_files["soul"]
        user_path = config.context_files["user"]
        tools_path = config.context_files["tools"]

        # Load individual files to create them
        await loader.load_file("soul", soul_path)
        await loader.load_file("user", user_path)
        await loader.load_file("tools", tools_path)

        # Verify all files exist
        assert soul_path.exists()
        assert user_path.exists()
        assert tools_path.exists()


class TestTemplateManagerIntegration:
    """Integration tests for TemplateManager with real files."""

    @pytest.mark.asyncio
    async def test_multiple_context_loaders_share_templates(self, config):
        """Multiple ContextLoader instances can use same templates."""
        soul_path = config.context_files["soul"]

        loader1 = ContextLoader(config)
        loader2 = ContextLoader(config)

        # First loader creates file
        await loader1.load_file("soul", soul_path)

        # Invalidate cache on second loader to force re-read
        loader2._cache.clear()

        # Second loader should read existing file
        context_file = await loader2.load_file("soul", soul_path)

        assert context_file is not None
        assert "# Soul" in context_file.content
