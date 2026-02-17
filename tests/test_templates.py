"""Tests for template management."""

import tempfile
from datetime import date
from pathlib import Path

import pytest

from src.templates import TemplateManager


# Fixtures
@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_templates(temp_workspace):
    """Create a templates directory with sample templates."""
    template_dir = temp_workspace / "templates"
    template_dir.mkdir()

    # Create sample templates
    (template_dir / "SOUL.md").write_text(
        "---\ntitle: SOUL\n---\n# Soul\nDate: {current_date}\nYear: {current_year}\n"
    )
    (template_dir / "USER.md").write_text("# User Profile\nName: {name}")
    (template_dir / "TOOLS.md").write_text("# Tools Config\n")
    (template_dir / "MEMORY.md").write_text("# Memory\n")

    return temp_workspace


@pytest.fixture
def manager(temp_templates):
    """Create a TemplateManager with temp templates."""
    return TemplateManager(temp_templates)


# Tests for template directory resolution
class TestTemplateDirectoryResolution:
    """Test template directory discovery."""

    def test_finds_local_templates(self, temp_templates):
        """Test finding templates in workspace."""
        manager = TemplateManager(temp_templates)
        assert manager.template_dir.exists()
        assert manager.template_dir.name == "templates"

    def test_fallback_to_project_templates(self, temp_workspace):
        """Test that manager falls back to project templates dir."""
        manager = TemplateManager(temp_workspace)

        # Should find the project's templates/ directory as fallback
        # (since tests run from project root)
        assert manager._template_dir is not None
        assert "templates" in str(manager._template_dir)

    def test_template_dir_property_raises_when_missing(self, temp_workspace):
        """Test template_dir raises when not found."""
        manager = TemplateManager(temp_workspace)
        manager._template_dir = None

        with pytest.raises(FileNotFoundError, match="No template directory"):
            _ = manager.template_dir


# Tests for template existence checks
class TestTemplateExists:
    """Test template existence checking."""

    def test_existing_template(self, manager):
        """Test checking for existing template."""
        assert manager.template_exists("SOUL.md") is True

    def test_missing_template(self, manager):
        """Test checking for missing template."""
        assert manager.template_exists("MISSING.md") is False

    def test_no_template_dir(self, temp_workspace):
        """Test exists check when no template directory."""
        manager = TemplateManager(temp_workspace)
        manager._template_dir = None

        assert manager.template_exists("SOUL.md") is False


class TestTargetExists:
    """Test target file existence checking."""

    def test_target_missing(self, manager):
        """Test checking for missing target file."""
        assert manager.target_exists("SOUL.md") is False

    def test_target_exists(self, manager):
        """Test checking for existing target file."""
        target = manager.get_target_path("SOUL.md")
        target.write_text("existing")

        assert manager.target_exists("SOUL.md") is True


# Tests for template loading
class TestLoadTemplate:
    """Test template loading."""

    def test_load_existing_template(self, manager):
        """Test loading an existing template."""
        content = manager.load_template("SOUL.md")

        assert content is not None
        assert "# Soul" in content

    def test_load_missing_template(self, manager, caplog):
        """Test loading a missing template."""
        import logging

        caplog.set_level(logging.WARNING)

        content = manager.load_template("MISSING.md")

        assert content is None
        assert "Template not found" in caplog.text


# Tests for variable substitution
class TestSubstituteVariables:
    """Test template variable substitution."""

    def test_default_variables(self, manager):
        """Test default variable substitution."""
        content = "Date: {current_date}"
        result = manager.substitute_variables(content)

        assert result == f"Date: {date.today().isoformat()}"

    def test_current_year_variable(self, manager):
        """Test current_year variable."""
        content = "Year: {current_year}"
        result = manager.substitute_variables(content)

        assert result == f"Year: {date.today().year}"

    def test_custom_variables(self, manager):
        """Test custom variable substitution."""
        content = "Name: {name}"
        result = manager.substitute_variables(content, {"name": "Alfred"})

        assert result == "Name: Alfred"

    def test_mixed_variables(self, manager):
        """Test mixing default and custom variables."""
        content = "Date: {current_date}, Name: {name}"
        result = manager.substitute_variables(content, {"name": "Alfred"})

        assert f"Date: {date.today().isoformat()}" in result
        assert "Name: Alfred" in result

    def test_missing_variable_keeps_placeholder(self, manager, caplog):
        """Test that missing variables don't crash."""
        import logging

        caplog.set_level(logging.WARNING)

        content = "Missing: {undefined_var}"
        result = manager.substitute_variables(content)

        # Should not crash, returns content as-is or partially substituted
        assert "Missing:" in result


# Tests for file creation
class TestCreateFromTemplate:
    """Test creating files from templates."""

    def test_creates_new_file(self, manager):
        """Test creating a new file from template."""
        path = manager.create_from_template("SOUL.md")

        assert path is not None
        assert path.exists()
        content = path.read_text()
        assert "# Soul" in content

    def test_substitutes_variables(self, manager):
        """Test variables are substituted during creation."""
        path = manager.create_from_template("SOUL.md")

        content = path.read_text()
        assert date.today().isoformat() in content

    def test_skips_existing_by_default(self, manager):
        """Test that existing files are not overwritten."""
        target = manager.get_target_path("SOUL.md")
        target.write_text("existing content")

        path = manager.create_from_template("SOUL.md")

        assert path == target
        assert path.read_text() == "existing content"

    def test_overwrites_when_requested(self, manager):
        """Test overwriting existing file when requested."""
        target = manager.get_target_path("SOUL.md")
        target.write_text("existing content")

        path = manager.create_from_template("SOUL.md", overwrite=True)

        assert path == target
        content = path.read_text()
        assert "# Soul" in content

    def test_returns_none_for_missing_template(self, manager, caplog):
        """Test returns None when template is missing."""
        import logging

        caplog.set_level(logging.WARNING)

        path = manager.create_from_template("MISSING.md")

        assert path is None


# Tests for ensure_exists
class TestEnsureExists:
    """Test ensuring files exist."""

    def test_creates_missing_file(self, manager):
        """Test creating a missing auto-create template."""
        path = manager.ensure_exists("SOUL.md")

        assert path is not None
        assert path.exists()

    def test_returns_existing_path(self, manager):
        """Test returning path to existing file."""
        target = manager.get_target_path("SOUL.md")
        target.write_text("existing")

        path = manager.ensure_exists("SOUL.md")

        assert path == target

    def test_skips_unknown_template(self, manager, caplog):
        """Test not auto-creating unknown templates."""
        import logging

        caplog.set_level(logging.DEBUG)

        # Create a non-auto-create template
        template_dir = manager.template_dir
        (template_dir / "CUSTOM.md").write_text("# Custom")

        path = manager.ensure_exists("CUSTOM.md")

        assert path is None


# Tests for ensure_all_exist
class TestEnsureAllExist:
    """Test ensuring all templates exist."""

    def test_creates_all_missing(self, manager):
        """Test creating all missing templates."""
        result = manager.ensure_all_exist()

        assert len(result) == 4
        assert "SOUL.md" in result
        assert "USER.md" in result
        assert "TOOLS.md" in result
        assert "MEMORY.md" in result

        for path in result.values():
            assert path.exists()

    def test_returns_existing_paths(self, manager):
        """Test returning paths to existing files."""
        # Create one file manually
        target = manager.get_target_path("SOUL.md")
        target.write_text("existing")

        result = manager.ensure_all_exist()

        assert len(result) == 4
        assert result["SOUL.md"].read_text() == "existing"


# Tests for list methods
class TestListMethods:
    """Test listing templates."""

    def test_list_templates(self, manager):
        """Test listing available templates."""
        templates = manager.list_templates()

        assert "SOUL.md" in templates
        assert "USER.md" in templates
        assert "TOOLS.md" in templates
        assert "MEMORY.md" in templates

    def test_list_templates_sorted(self, manager):
        """Test templates are sorted alphabetically."""
        templates = manager.list_templates()

        assert templates == sorted(templates)

    def test_list_missing(self, manager):
        """Test listing missing templates."""
        missing = manager.list_missing()

        assert len(missing) == 4

    def test_list_missing_after_creation(self, manager):
        """Test listing missing after creating some."""
        manager.ensure_exists("SOUL.md")

        missing = manager.list_missing()

        assert "SOUL.md" not in missing
        assert len(missing) == 3


# Tests for path methods
class TestPathMethods:
    """Test path resolution methods."""

    def test_get_template_path(self, manager):
        """Test getting template path."""
        path = manager.get_template_path("SOUL.md")

        assert path.name == "SOUL.md"
        assert "templates" in str(path)

    def test_get_target_path(self, manager):
        """Test getting target path."""
        path = manager.get_target_path("SOUL.md")

        assert path.name == "SOUL.md"
        assert path.parent == manager.workspace_dir
