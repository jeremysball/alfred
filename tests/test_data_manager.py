"""Tests for XDG directory initialization and management."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from alfred.data_manager import (
    APP_NAME,
    get_config_dir,
    get_data_dir,
    get_memory_dir,
    get_workspace_dir,
    init_xdg_directories,
)


class TestXDGDirectoryPaths:
    """Test XDG directory path functions."""

    def test_get_config_dir_uses_xdg_config_home(self):
        """get_config_dir respects XDG_CONFIG_HOME."""
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": "/test/config"}):
            result = get_config_dir()
            assert result == Path("/test/config") / APP_NAME

    def test_get_config_dir_defaults_to_dot_config(self):
        """get_config_dir defaults to ~/.config/alfred."""
        with patch.dict(os.environ, {}, clear=True), patch.object(Path, "home", return_value=Path("/home/test")):
            result = get_config_dir()
            assert result == Path("/home/test/.config") / APP_NAME

    def test_get_data_dir_uses_xdg_data_home(self):
        """get_data_dir respects XDG_DATA_HOME."""
        with patch.dict(os.environ, {"XDG_DATA_HOME": "/test/data"}):
            result = get_data_dir()
            assert result == Path("/test/data") / APP_NAME

    def test_get_data_dir_defaults_to_dot_local_share(self):
        """get_data_dir defaults to ~/.local/share/alfred."""
        with patch.dict(os.environ, {}, clear=True), patch.object(Path, "home", return_value=Path("/home/test")):
            result = get_data_dir()
            assert result == Path("/home/test/.local/share") / APP_NAME

    def test_get_workspace_dir_in_data_dir(self):
        """get_workspace_dir returns workspace in data dir."""
        with patch("alfred.data_manager.get_data_dir", return_value=Path("/test/data")):
            result = get_workspace_dir()
            assert result == Path("/test/data/workspace")

    def test_get_memory_dir_in_data_dir(self):
        """get_memory_dir returns memory in data dir."""
        with patch("alfred.data_manager.get_data_dir", return_value=Path("/test/data")):
            result = get_memory_dir()
            assert result == Path("/test/data/memory")

    def test_get_config_toml_path_uses_xdg_config_home(self):
        """get_config_toml_path respects XDG_CONFIG_HOME."""
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": "/test/config"}):
            from alfred.data_manager import get_config_toml_path

            result = get_config_toml_path()
            assert result == Path("/test/config") / APP_NAME / "config.toml"

    def test_get_config_toml_path_defaults_to_dot_config(self):
        """get_config_toml_path defaults to ~/.config/alfred/config.toml."""
        with patch.dict(os.environ, {}, clear=True), patch.object(Path, "home", return_value=Path("/home/test")):
            from alfred.data_manager import get_config_toml_path

            result = get_config_toml_path()
            assert result == Path("/home/test/.config") / APP_NAME / "config.toml"


class TestXDGDirectoryInit:
    """Test XDG directory initialization."""

    @pytest.fixture
    def xdg_dirs(self, tmp_path):
        """Provide temporary XDG directories."""
        config_dir = tmp_path / "config" / APP_NAME
        data_dir = tmp_path / "data" / APP_NAME

        with (
            patch("alfred.data_manager.get_config_dir", return_value=config_dir),
            patch("alfred.data_manager.get_data_dir", return_value=data_dir),
        ):
            yield config_dir, data_dir

    @pytest.fixture
    def bundled_files(self, tmp_path):
        """Create mock bundled templates."""
        bundled_templates = tmp_path / "bundled_templates"
        bundled_templates.mkdir()
        (bundled_templates / "SOUL.md").write_text("# Soul Template")
        (bundled_templates / "USER.md").write_text("# User Template")
        (bundled_templates / "config.toml").write_text(
            '[provider]\\ndefault = "kimi"\\n\\n[memory]\\nbudget = 32000\\n'
        )

        with patch("alfred.data_manager.BUNDLED_TEMPLATES", bundled_templates):
            yield bundled_templates

    def test_creates_config_directory(self, xdg_dirs, bundled_files):
        """Config directory created if missing."""
        config_dir, _ = xdg_dirs
        assert not config_dir.exists()

        init_xdg_directories()

        assert config_dir.exists()
        assert config_dir.is_dir()

    def test_creates_data_directory(self, xdg_dirs, bundled_files):
        """Data directory created if missing."""
        _, data_dir = xdg_dirs
        assert not data_dir.exists()

        init_xdg_directories()

        assert data_dir.exists()
        assert data_dir.is_dir()

    def test_creates_workspace_directory(self, xdg_dirs, bundled_files):
        """Workspace subdirectory created."""
        _, data_dir = xdg_dirs

        init_xdg_directories()

        workspace_dir = data_dir / "workspace"
        assert workspace_dir.exists()
        assert workspace_dir.is_dir()

    def test_creates_memory_directory(self, xdg_dirs, bundled_files):
        """Memory subdirectory created."""
        _, data_dir = xdg_dirs

        init_xdg_directories()

        memory_dir = data_dir / "memory"
        assert memory_dir.exists()
        assert memory_dir.is_dir()

    def test_copies_templates_as_workspace_files(self, xdg_dirs, bundled_files):
        """Templates copied as data files to workspace (not templates folder)."""
        init_xdg_directories()

        _, data_dir = xdg_dirs
        workspace_dir = data_dir / "workspace"

        # Templates should be in workspace as data files
        assert (workspace_dir / "SOUL.md").exists()
        assert (workspace_dir / "USER.md").exists()

        # Should NOT have a templates subdir
        assert not (data_dir / "templates").exists()

    def test_template_content_in_workspace(self, xdg_dirs, bundled_files):
        """Template content preserved when copied to workspace."""
        init_xdg_directories()

        _, data_dir = xdg_dirs
        soul_file = data_dir / "workspace" / "SOUL.md"

        content = soul_file.read_text()
        assert content == "# Soul Template"

    def test_does_not_overwrite_existing_workspace_files(self, xdg_dirs, bundled_files):
        """Existing workspace files are not overwritten."""
        _, data_dir = xdg_dirs
        workspace_dir = data_dir / "workspace"
        workspace_dir.mkdir(parents=True)
        (workspace_dir / "SOUL.md").write_text("# Custom Soul")

        init_xdg_directories()

        content = (workspace_dir / "SOUL.md").read_text()
        assert content == "# Custom Soul"

    def test_copies_config_toml_if_missing(self, xdg_dirs, bundled_files):
        """Config.toml copied from templates if missing."""
        init_xdg_directories()

        config_dir, _ = xdg_dirs
        config_toml_path = config_dir / "config.toml"
        assert config_toml_path.exists()

        content = config_toml_path.read_text()
        assert "[provider]" in content
        assert "[memory]" in content

    def test_does_not_overwrite_existing_config_toml(self, xdg_dirs, bundled_files):
        """Existing config.toml is not overwritten."""
        config_dir, _ = xdg_dirs
        config_dir.mkdir(parents=True)
        existing_config = config_dir / "config.toml"
        existing_config.write_text("[custom]\\nvalue = 123")

        init_xdg_directories()

        content = existing_config.read_text()
        assert "value = 123" in content

    def test_handles_missing_bundled_templates(self, xdg_dirs):
        """Handles missing bundled templates gracefully."""
        with patch("alfred.data_manager.BUNDLED_TEMPLATES", Path("/nonexistent")):
            init_xdg_directories()  # Should not raise

            _, data_dir = xdg_dirs
            assert data_dir.exists()


class TestIntegration:
    """Integration tests with actual file system."""

    def test_full_init_sequence(self, tmp_path):
        """Complete initialization sequence works."""
        # Set up XDG dirs in temp
        config_dir = tmp_path / ".config" / APP_NAME
        data_dir = tmp_path / ".local" / "share" / APP_NAME

        with (
            patch("alfred.data_manager.get_config_dir", return_value=config_dir),
            patch("alfred.data_manager.get_data_dir", return_value=data_dir),
            patch("alfred.data_manager.BUNDLED_TEMPLATES", Path("/nonexistent")),
        ):
            # Before init
            assert not config_dir.exists()
            assert not data_dir.exists()

            # Init
            init_xdg_directories()

            # After init
            assert config_dir.exists()
            assert data_dir.exists()
            assert (data_dir / "workspace").exists()
            assert (data_dir / "memory").exists()
