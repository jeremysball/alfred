"""Tests for template management and auto-creation."""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from src.templates import TemplateManager


class TestTemplateManagerInit:
    """Test TemplateManager initialization and directory resolution."""

    def test_init_with_workspace_dir(self, tmp_path: Path) -> None:
        """TemplateManager stores workspace directory."""
        manager = TemplateManager(tmp_path)
        assert manager.workspace_dir == tmp_path

    def test_resolve_template_dir_workspace_priority(self, tmp_path: Path) -> None:
        """Workspace templates directory takes priority."""
        # Create workspace/templates directory
        workspace_templates = tmp_path / "templates"
        workspace_templates.mkdir()
        (workspace_templates / "test.md").write_text("workspace template")

        manager = TemplateManager(tmp_path)
        assert manager.template_dir == workspace_templates

    def test_resolve_template_dir_fallback_dev(self, tmp_path: Path) -> None:
        """Fallback to bundled templates in development."""
        # No workspace/templates, should find development templates
        manager = TemplateManager(tmp_path)
        # In dev environment, should find src/../templates
        assert manager.template_dir is not None
        assert manager.template_dir.exists()

    def test_template_dir_not_found(self, tmp_path: Path) -> None:
        """Handle missing template directory gracefully."""
        # Patch to simulate no templates found
        with patch.object(TemplateManager, '_resolve_template_dir', return_value=None):
            manager = TemplateManager(tmp_path)
            assert manager._template_dir is None
            with pytest.raises(FileNotFoundError, match="No template directory available"):
                _ = manager.template_dir


class TestTemplateExistenceChecks:
    """Test template and target existence checks."""

    def test_template_exists_true(self, tmp_path: Path) -> None:
        """template_exists returns True for existing template."""
        manager = TemplateManager(tmp_path)
        # SYSTEM.md should exist in bundled templates
        assert manager.template_exists("SYSTEM.md") is True

    def test_template_exists_false(self, tmp_path: Path) -> None:
        """template_exists returns False for missing template."""
        manager = TemplateManager(tmp_path)
        assert manager.template_exists("NONEXISTENT.md") is False

    def test_target_exists_true(self, tmp_path: Path) -> None:
        """target_exists returns True for existing file in workspace."""
        manager = TemplateManager(tmp_path)
        (tmp_path / "USER.md").write_text("test")
        assert manager.target_exists("USER.md") is True

    def test_target_exists_false(self, tmp_path: Path) -> None:
        """target_exists returns False for missing file in workspace."""
        manager = TemplateManager(tmp_path)
        assert manager.target_exists("MISSING.md") is False


class TestTemplateLoading:
    """Test template loading functionality."""

    def test_load_existing_template(self, tmp_path: Path) -> None:
        """Load template content from file."""
        manager = TemplateManager(tmp_path)
        content = manager.load_template("SYSTEM.md")
        assert content is not None
        assert "# System" in content
        assert "Memory Architecture" in content

    def test_load_missing_template(self, tmp_path: Path) -> None:
        """Return None for missing template with warning."""
        manager = TemplateManager(tmp_path)
        content = manager.load_template("NONEXISTENT.md")
        assert content is None

    def test_load_agents_template_content(self, tmp_path: Path) -> None:
        """AGENTS.md uses placeholders for atomic sections."""
        manager = TemplateManager(tmp_path)
        content = manager.load_template("AGENTS.md")
        assert content is not None
        # AGENTS.md should contain placeholders, not inline content
        assert "{{prompts/agents/memory-system.md}}" in content
        assert "{{prompts/agents/rules-index.md}}" in content
        # Content is now in atomic files
        design_content = manager.load_template("prompts/agents/design-questions.md")
        assert design_content is not None
        assert design_content.startswith("## ")
        rules_content = manager.load_template("prompts/agents/rules-index.md")
        assert rules_content is not None
        assert rules_content.startswith("## ")
        # Rules should have numbered sections
        assert "### 0." in rules_content
        assert "### 1." in rules_content


class TestVariableSubstitution:
    """Test template variable substitution."""

    def test_substitute_default_variables(self, tmp_path: Path) -> None:
        """Substitute default date variables."""
        manager = TemplateManager(tmp_path)
        content = "Date: {current_date}, Year: {current_year}"
        result = manager.substitute_variables(content)
        assert "{current_date}" not in result
        assert "{current_year}" not in result
        # Should have actual date values
        assert "Date:" in result
        assert "Year:" in result

    def test_substitute_custom_variables(self, tmp_path: Path) -> None:
        """Substitute custom variables."""
        manager = TemplateManager(tmp_path)
        content = "Hello {name}, welcome to {place}"
        result = manager.substitute_variables(content, {"name": "Alice", "place": "Wonderland"})
        assert result == "Hello Alice, welcome to Wonderland"

    def test_substitute_missing_variable_logs_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Missing variables log warning and leave placeholder."""
        manager = TemplateManager(tmp_path)
        content = "Hello {undefined_var}"
        with caplog.at_level(logging.WARNING):
            result = manager.substitute_variables(content)
        assert "undefined_var" in result  # Placeholder preserved
        assert "Missing template variable" in caplog.text


class TestCreateFromTemplate:
    """Test creating files from templates."""

    def test_create_new_file(self, tmp_path: Path) -> None:
        """Create file from template when target doesn't exist."""
        manager = TemplateManager(tmp_path)
        target = manager.create_from_template("SYSTEM.md")
        assert target is not None
        assert target.exists()
        assert target.name == "SYSTEM.md"
        content = target.read_text()
        assert "# System" in content

    def test_skip_existing_file(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Skip creation if file exists and overwrite=False."""
        manager = TemplateManager(tmp_path)
        existing = tmp_path / "SYSTEM.md"
        existing.write_text("existing content")

        with caplog.at_level(logging.DEBUG):
            target = manager.create_from_template("SYSTEM.md", overwrite=False)

        assert target == existing
        assert existing.read_text() == "existing content"  # Unchanged
        assert "already exists, skipping" in caplog.text

    def test_overwrite_existing_file(self, tmp_path: Path) -> None:
        """Overwrite existing file when overwrite=True."""
        manager = TemplateManager(tmp_path)
        existing = tmp_path / "SYSTEM.md"
        existing.write_text("old content")

        target = manager.create_from_template("SYSTEM.md", overwrite=True)

        assert target == existing
        content = existing.read_text()
        assert "old content" not in content
        assert "# System" in content

    def test_create_missing_template_returns_none(self, tmp_path: Path) -> None:
        """Return None if template doesn't exist."""
        manager = TemplateManager(tmp_path)
        target = manager.create_from_template("NONEXISTENT.md")
        assert target is None


class TestEnsureExists:
    """Test ensure_exists functionality."""

    def test_ensure_exists_creates_missing(self, tmp_path: Path) -> None:
        """Create file if it doesn't exist."""
        manager = TemplateManager(tmp_path)
        target = manager.ensure_exists("SYSTEM.md")
        assert target is not None
        assert target.exists()

    def test_ensure_exists_returns_existing(self, tmp_path: Path) -> None:
        """Return path if file already exists."""
        manager = TemplateManager(tmp_path)
        existing = tmp_path / "SYSTEM.md"
        existing.write_text("custom")

        target = manager.ensure_exists("SYSTEM.md")
        assert target == existing
        assert target.read_text() == "custom"  # Unchanged

    def test_ensure_exists_skips_unknown_templates(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Don't auto-create templates not in AUTO_CREATE_TEMPLATES."""
        manager = TemplateManager(tmp_path)
        with caplog.at_level(logging.DEBUG):
            target = manager.ensure_exists("UNKNOWN.md")
        assert target is None
        assert "Not auto-creating unknown template" in caplog.text


class TestAutoCreateTemplates:
    """Test AUTO_CREATE_TEMPLATES configuration."""

    def test_tools_md_not_in_auto_create(self, tmp_path: Path) -> None:
        """TOOLS.md is phased out and not auto-created."""
        manager = TemplateManager(tmp_path)
        assert "TOOLS.md" not in manager.AUTO_CREATE_TEMPLATES
        assert "SYSTEM.md" in manager.AUTO_CREATE_TEMPLATES
        assert "AGENTS.md" in manager.AUTO_CREATE_TEMPLATES
        assert "SOUL.md" in manager.AUTO_CREATE_TEMPLATES
        assert "USER.md" in manager.AUTO_CREATE_TEMPLATES

    def test_ensure_all_exist_creates_expected_files(self, tmp_path: Path) -> None:
        """ensure_all_exist creates only AUTO_CREATE_TEMPLATES files."""
        manager = TemplateManager(tmp_path)
        result = manager.ensure_all_exist()

        # Should create all expected files
        assert "SYSTEM.md" in result
        assert "AGENTS.md" in result
        assert "SOUL.md" in result
        assert "USER.md" in result

        # Should NOT create TOOLS.md
        assert "TOOLS.md" not in result
        assert not (tmp_path / "TOOLS.md").exists()

        # All created files should exist
        for name, path in result.items():
            assert path.exists(), f"{name} should exist"


class TestPromptsDirectory:
    """Test prompts folder handling."""

    def test_ensure_prompts_exist_creates_directory(self, tmp_path: Path) -> None:
        """Create prompts directory from templates."""
        manager = TemplateManager(tmp_path)
        prompts_dir = manager.ensure_prompts_exist()
        assert prompts_dir is not None
        assert prompts_dir.exists()
        assert prompts_dir.name == "prompts"

    def test_ensure_prompts_exist_copies_files(self, tmp_path: Path) -> None:
        """Copy prompt files from templates to workspace."""
        manager = TemplateManager(tmp_path)
        prompts_dir = manager.ensure_prompts_exist()

        # Should have copied files from templates/prompts/
        template_prompts = manager.template_dir / "prompts"
        if template_prompts.exists():
            for source_file in template_prompts.glob("*.md"):
                target_file = prompts_dir / source_file.name
                assert target_file.exists(), f"Should copy {source_file.name}"

    def test_ensure_prompts_exist_skips_existing(self, tmp_path: Path) -> None:
        """Don't overwrite existing prompt files."""
        manager = TemplateManager(tmp_path)
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        existing = prompts_dir / "test.md"
        existing.write_text("custom content")

        manager.ensure_prompts_exist()
        assert existing.read_text() == "custom content"

    def test_ensure_prompts_exist_no_source(self, tmp_path: Path) -> None:
        """Handle missing source prompts directory."""
        # Create manager with workspace that has no templates/prompts
        workspace_templates = tmp_path / "templates"
        workspace_templates.mkdir()
        (workspace_templates / "SYSTEM.md").write_text("test")

        manager = TemplateManager(tmp_path)
        result = manager.ensure_prompts_exist()
        assert result is None


class TestTemplateContentValidation:
    """Validate template content matches PRD specification."""

    def test_system_md_has_memory_architecture(self, tmp_path: Path) -> None:
        """SYSTEM.md contains memory architecture section."""
        manager = TemplateManager(tmp_path)
        content = manager.load_template("SYSTEM.md")
        assert content is not None
        assert "# System" in content
        assert "Memory Architecture" in content
        assert "Files (USER.md, SOUL.md, SYSTEM.md, AGENTS.md)" in content
        assert "Memories (remember tool)" in content
        assert "Session Archive (search_sessions)" in content
        assert "Decision Framework" in content

    def test_system_md_is_valid(self, tmp_path: Path) -> None:
        """SYSTEM.md exists and has valid structure."""
        manager = TemplateManager(tmp_path)
        content = manager.load_template("SYSTEM.md")
        assert content is not None
        assert content.startswith("# ")
        # Should have section headings
        assert "## " in content
        # Should mention tools (without being too specific about names)
        assert "(" in content and ")" in content  # Function references

    def test_agents_md_is_minimal(self, tmp_path: Path) -> None:
        """AGENTS.md uses placeholders for all content sections."""
        manager = TemplateManager(tmp_path)
        content = manager.load_template("AGENTS.md")
        assert content is not None
        # AGENTS.md should only contain header and placeholders
        assert "{{prompts/agents/memory-system.md}}" in content
        assert "{{prompts/agents/rules-index.md}}" in content
        # Should not have inline section content anymore (should use placeholders)
        # Count lines - minimal file should be mostly placeholders (< 25 lines)
        lines = [line for line in content.strip().split("\n") if line.strip()]
        assert len(lines) < 25, "AGENTS.md should be minimal (placeholders only)"
        # Content is now in atomic files
        beta_content = manager.load_template("prompts/agents/beta-notice.md")
        assert beta_content is not None
        assert beta_content.startswith("## ")


class TestListOperations:
    """Test listing templates and missing files."""

    def test_list_templates_returns_available(self, tmp_path: Path) -> None:
        """list_templates returns available template names."""
        manager = TemplateManager(tmp_path)
        templates = manager.list_templates()
        assert "SYSTEM.md" in templates
        assert "AGENTS.md" in templates
        assert all(t.endswith(".md") for t in templates)

    def test_list_missing_returns_only_missing(self, tmp_path: Path) -> None:
        """list_missing returns only templates not in workspace."""
        manager = TemplateManager(tmp_path)
        # Create some files
        (tmp_path / "SYSTEM.md").write_text("test")
        (tmp_path / "AGENTS.md").write_text("test")

        missing = manager.list_missing()
        assert "SYSTEM.md" not in missing
        assert "AGENTS.md" not in missing
        assert "SOUL.md" in missing
        assert "USER.md" in missing

    def test_list_missing_excludes_tools_md(self, tmp_path: Path) -> None:
        """TOOLS.md not in list_missing since not auto-created."""
        manager = TemplateManager(tmp_path)
        missing = manager.list_missing()
        assert "TOOLS.md" not in missing


class TestIntegrationWithPlaceholders:
    """Test template system integrates with placeholder resolution."""

    def test_loaded_templates_can_resolve_placeholders(self, tmp_path: Path) -> None:
        """Templates loaded by TemplateManager work with placeholders."""
        from src.placeholders import resolve_file_includes

        manager = TemplateManager(tmp_path)
        # Ensure prompts exist for include resolution
        manager.ensure_prompts_exist()

        # Load a template
        content = manager.load_template("SOUL.md")
        if content and "{{" in content:
            # If template has placeholders, they should be resolvable
            resolved = resolve_file_includes(content, tmp_path)
            # Should either resolve or have HTML comments for missing includes
            assert "{{" not in resolved or "<!-- missing:" in resolved
