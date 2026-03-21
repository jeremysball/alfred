"""Tests for config_update command refactoring."""

from pathlib import Path
from unittest.mock import patch

from alfred.cli.main import (
    _display_footer,
    _display_update_results,
    _get_preserve_set,
    _group_update_results,
)


class TestGetPreserveSet:
    """Tests for _get_preserve_set function."""

    def test_preserve_set_with_force_false(self):
        """Should return default preserve set when force is False."""
        result = _get_preserve_set(force=False)

        assert result == {"USER.md", "SOUL.md", "CUSTOM.md"}

    def test_preserve_set_with_force_true(self):
        """Should return empty set when force is True."""
        result = _get_preserve_set(force=True)

        assert result == set()


class TestGroupUpdateResults:
    """Tests for _group_update_results function."""

    def test_empty_results(self):
        """Should handle empty results dict."""
        results = {}

        groups = _group_update_results(results)

        assert groups["updated"] == []
        assert groups["preserved"] == []
        assert groups["skipped"] == []
        assert groups["errors"] == []
        assert groups["prompts"] is None

    def test_single_updated_file(self):
        """Should group a single updated file."""
        results = {
            "SYSTEM.md": {"status": "updated", "message": "Updated from template"},
        }

        groups = _group_update_results(results)

        assert groups["updated"] == [("SYSTEM.md", "Updated from template")]
        assert groups["preserved"] == []
        assert groups["skipped"] == []
        assert groups["errors"] == []

    def test_mixed_status_results(self):
        """Should correctly group files with different statuses."""
        results = {
            "SYSTEM.md": {"status": "updated", "message": "Updated"},
            "USER.md": {"status": "preserved", "message": "User file"},
            "AGENTS.md": {"status": "skipped", "message": "Up to date"},
            "TOOLS.md": {"status": "error", "message": "Permission denied"},
        }

        groups = _group_update_results(results)

        assert groups["updated"] == [("SYSTEM.md", "Updated")]
        assert groups["preserved"] == [("USER.md", "User file")]
        assert groups["skipped"] == [("AGENTS.md", "Up to date")]
        assert groups["errors"] == [("TOOLS.md", "Permission denied")]

    def test_dry_run_status_treated_as_updated(self):
        """Should treat dry_run status as updated."""
        results = {
            "SYSTEM.md": {"status": "dry_run", "message": "Would update"},
        }

        groups = _group_update_results(results)

        assert groups["updated"] == [("SYSTEM.md", "Would update")]

    def test_prompts_special_case(self):
        """Should handle prompts/ as special case."""
        results = {
            "SYSTEM.md": {"status": "updated", "message": "Updated"},
            "prompts/": {"status": "updated", "message": "5 prompts updated"},
        }

        groups = _group_update_results(results)

        assert groups["updated"] == [("SYSTEM.md", "Updated")]
        assert groups["prompts"] == {"status": "updated", "message": "5 prompts updated"}

    def test_unknown_status_ignored(self):
        """Should ignore files with unknown status."""
        results = {
            "SYSTEM.md": {"status": "unknown", "message": "???"},
        }

        groups = _group_update_results(results)

        assert groups["updated"] == []
        assert groups["preserved"] == []
        assert groups["skipped"] == []
        assert groups["errors"] == []


class TestDisplayUpdateResults:
    """Tests for _display_update_results function."""

    @patch("alfred.cli.main.console")
    def test_dry_run_header(self, mock_console):
        """Should display dry run header when dry_run is True."""
        groups = {
            "updated": [],
            "preserved": [],
            "skipped": [],
            "errors": [],
            "prompts": None,
        }

        _display_update_results(groups, dry_run=True)

        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Dry run" in call for call in calls)

    @patch("alfred.cli.main.console")
    def test_results_header(self, mock_console):
        """Should display results header when dry_run is False."""
        groups = {
            "updated": [],
            "preserved": [],
            "skipped": [],
            "errors": [],
            "prompts": None,
        }

        _display_update_results(groups, dry_run=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Config update results" in call for call in calls)

    @patch("alfred.cli.main.console")
    def test_display_updated_files(self, mock_console):
        """Should display updated files section."""
        groups = {
            "updated": [("SYSTEM.md", "Updated from template")],
            "preserved": [],
            "skipped": [],
            "errors": [],
            "prompts": None,
        }

        _display_update_results(groups, dry_run=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Updated:" in call for call in calls)
        assert any("SYSTEM.md" in call for call in calls)

    @patch("alfred.cli.main.console")
    def test_display_preserved_files(self, mock_console):
        """Should display preserved files section."""
        groups = {
            "updated": [],
            "preserved": [("USER.md", "User file")],
            "skipped": [],
            "errors": [],
            "prompts": None,
        }

        _display_update_results(groups, dry_run=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Preserved" in call for call in calls)
        assert any("USER.md" in call for call in calls)

    @patch("alfred.cli.main.console")
    def test_display_skipped_files(self, mock_console):
        """Should display skipped files section."""
        groups = {
            "updated": [],
            "preserved": [],
            "skipped": [("AGENTS.md", "Up to date")],
            "errors": [],
            "prompts": None,
        }

        _display_update_results(groups, dry_run=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Skipped" in call for call in calls)
        assert any("AGENTS.md" in call for call in calls)

    @patch("alfred.cli.main.console")
    def test_display_errors(self, mock_console):
        """Should display errors section."""
        groups = {
            "updated": [],
            "preserved": [],
            "skipped": [],
            "errors": [("TOOLS.md", "Permission denied")],
            "prompts": None,
        }

        _display_update_results(groups, dry_run=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Errors:" in call for call in calls)
        assert any("TOOLS.md" in call for call in calls)

    @patch("alfred.cli.main.console")
    def test_display_prompts_updated(self, mock_console):
        """Should display prompts with updated status."""
        groups = {
            "updated": [],
            "preserved": [],
            "skipped": [],
            "errors": [],
            "prompts": {"status": "updated", "message": "5 prompts updated"},
        }

        _display_update_results(groups, dry_run=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Prompts:" in call for call in calls)
        assert any("5 prompts updated" in call for call in calls)

    @patch("alfred.cli.main.console")
    def test_display_prompts_skipped(self, mock_console):
        """Should display prompts with skipped status."""
        groups = {
            "updated": [],
            "preserved": [],
            "skipped": [],
            "errors": [],
            "prompts": {"status": "skipped", "message": "No changes"},
        }

        _display_update_results(groups, dry_run=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Prompts:" in call for call in calls)
        assert any("No changes" in call for call in calls)

    @patch("alfred.cli.main.console")
    def test_empty_groups_not_displayed(self, mock_console):
        """Should not display sections with no items."""
        groups = {
            "updated": [("SYSTEM.md", "Updated")],
            "preserved": [],
            "skipped": [],
            "errors": [],
            "prompts": None,
        }

        _display_update_results(groups, dry_run=False)

        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Updated:" in call for call in calls)
        assert not any("Preserved" in call for call in calls)
        assert not any("Skipped" in call for call in calls)
        assert not any("Errors:" in call for call in calls)


class TestDisplayFooter:
    """Tests for _display_footer function."""

    @patch("alfred.cli.main.console")
    def test_display_workspace_path(self, mock_console):
        """Should display workspace directory."""
        workspace_dir = Path("/test/workspace")

        _display_footer(workspace_dir, force=False, preserved=[])

        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("/test/workspace" in call for call in calls)

    @patch("alfred.cli.main.console")
    def test_display_tip_when_preserved_and_not_force(self, mock_console):
        """Should display tip when there are preserved files and force is False."""
        workspace_dir = Path("/test")
        preserved = [("USER.md", "User file")]

        _display_footer(workspace_dir, force=False, preserved=preserved)

        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("--force" in call for call in calls)

    @patch("alfred.cli.main.console")
    def test_no_tip_when_force_true(self, mock_console):
        """Should not display tip when force is True."""
        workspace_dir = Path("/test")
        preserved = [("USER.md", "User file")]

        _display_footer(workspace_dir, force=True, preserved=preserved)

        calls = [str(call) for call in mock_console.print.call_args_list]
        assert not any("--force" in call for call in calls)

    @patch("alfred.cli.main.console")
    def test_no_tip_when_no_preserved(self, mock_console):
        """Should not display tip when no preserved files."""
        workspace_dir = Path("/test")

        _display_footer(workspace_dir, force=False, preserved=[])

        calls = [str(call) for call in mock_console.print.call_args_list]
        assert not any("--force" in call for call in calls)


class TestConfigUpdateIntegration:
    """Integration tests for config_update command."""

    @patch("alfred.cli.main._get_preserve_set")
    @patch("alfred.cli.main._group_update_results")
    @patch("alfred.cli.main._display_update_results")
    @patch("alfred.cli.main._display_footer")
    def test_config_update_workflow(
        self,
        mock_display_footer,
        mock_display_results,
        mock_group_results,
        mock_get_preserve,
    ):
        """Test config_update orchestrates helpers correctly."""
        from alfred.cli.main import config_update

        # Setup mocks
        mock_get_preserve.return_value = {"USER.md", "SOUL.md", "CUSTOM.md"}
        mock_group_results.return_value = {
            "updated": [("SYSTEM.md", "Updated")],
            "preserved": [],
            "skipped": [],
            "errors": [],
            "prompts": None,
        }

        # Call with dry_run=True to avoid actual file operations
        config_update(dry_run=True, force=False)

        # Verify helpers were called
        mock_get_preserve.assert_called_once_with(False)
        mock_group_results.assert_called_once()
        mock_display_results.assert_called_once()
        mock_display_footer.assert_called_once()
