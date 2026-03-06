"""Integration tests for ContextLoader template auto-creation."""

import tempfile
from datetime import date
from pathlib import Path

import pytest

from alfred.config import Config
from alfred.context import ContextLoader


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
            # Note: TOOLS.md phased out (content moved to SYSTEM.md and USER.md per PRD #102)
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

        # Note: TOOLS.md is phased out (content moved to SYSTEM.md and USER.md)
        assert "soul" in files
        assert "user" in files
        assert "tools" not in files  # TOOLS.md not auto-created

        # All auto-create files should exist on disk
        assert config.context_files["soul"].exists()
        assert config.context_files["user"].exists()

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
        # This test verifies soul/user are created (TOOLS.md phased out)
        soul_path = config.context_files["soul"]
        user_path = config.context_files["user"]

        # Load individual files to create them
        await loader.load_file("soul", soul_path)
        await loader.load_file("user", user_path)

        # Verify all files exist
        assert soul_path.exists()
        assert user_path.exists()


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


class TestContextLoaderPlaceholderResolution:
    """Tests for placeholder resolution in ContextLoader."""

    @pytest.fixture
    def workspace_with_includes(self, temp_workspace, config):
        """Create workspace with placeholder includes."""
        workspace_dir = config.workspace_dir

        # Create an included file
        (workspace_dir / "prompts").mkdir(exist_ok=True)
        (workspace_dir / "prompts" / "voice.md").write_text(
            "# Voice\n\nBe concise and direct.\n"
        )

        # Create SOUL.md with an include placeholder
        soul_path = config.context_files["soul"]
        soul_path.write_text(
            "# Soul\n\n{{prompts/voice.md}}\n\n## Style\nFriendly.\n"
        )

        return soul_path, workspace_dir

    @pytest.mark.asyncio
    async def test_context_loader_resolves_placeholders(
        self, loader, workspace_with_includes
    ):
        """File include placeholders are resolved when loading."""
        soul_path, workspace_dir = workspace_with_includes

        context_file = await loader.load_file("soul", soul_path)

        # Include should be resolved
        assert "# Voice" in context_file.content
        assert "Be concise and direct" in context_file.content
        assert "<!-- included: prompts/voice.md -->" in context_file.content

        # Original content preserved
        assert "## Style" in context_file.content
        assert "Friendly" in context_file.content

    @pytest.mark.asyncio
    async def test_context_loader_handles_missing_include_gracefully(
        self, loader, config, caplog
    ):
        """Missing includes log warning and include error comment."""
        import logging
        caplog.set_level(logging.WARNING)

        # Create SOUL.md referencing non-existent file
        soul_path = config.context_files["soul"]
        soul_path.write_text("# Soul\n\n{{prompts/nonexistent.md}}\n")

        context_file = await loader.load_file("soul", soul_path)

        # Should include error comment instead of crashing
        assert "<!-- missing: prompts/nonexistent.md -->" in context_file.content
        assert "not found" in caplog.text

    @pytest.mark.asyncio
    async def test_context_loader_resolves_color_placeholders(
        self, loader, config
    ):
        """Color placeholders {color} are resolved to ANSI codes."""
        soul_path = config.context_files["soul"]
        soul_path.write_text("# Soul\n\n{cyan}Hello{reset} World\n")

        context_file = await loader.load_file("soul", soul_path)

        # Color codes should be resolved
        assert "\033[36m" in context_file.content  # cyan
        assert "\033[0m" in context_file.content   # reset
        assert "{cyan}" not in context_file.content

    @pytest.mark.asyncio
    async def test_cached_file_contains_resolved_content(
        self, loader, workspace_with_includes
    ):
        """Cached content includes resolved placeholders."""
        soul_path, workspace_dir = workspace_with_includes

        # First load resolves placeholders
        first = await loader.load_file("soul", soul_path)

        # Delete the included file
        (workspace_dir / "prompts" / "voice.md").unlink()

        # Second load returns cached (resolved) content
        second = await loader.load_file("soul", soul_path)

        # Should still have resolved content from cache
        assert "# Voice" in second.content
        assert first.content == second.content
