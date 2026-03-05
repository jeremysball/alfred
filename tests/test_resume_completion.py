"""Tests for /resume command completion."""

from datetime import UTC, datetime
from unittest.mock import MagicMock


def test_session_id_provider_returns_matching_sessions():
    """Test that _session_id_provider returns session IDs matching partial input."""
    from src.interfaces.pypitui.tui import AlfredTUI

    # Mock Alfred and session manager
    mock_alfred = MagicMock()
    mock_storage = MagicMock()
    mock_storage.list_sessions.return_value = [
        "sess_abc123",
        "sess_def456",
        "sess_abc789",
    ]
    mock_alfred.session_manager.storage = mock_storage

    # Mock get_meta to return proper metadata objects
    mock_meta = MagicMock()
    mock_meta.last_active = datetime.now(UTC)
    mock_meta.current_count = 5
    mock_meta.archive_count = 2
    mock_storage.get_meta.return_value = mock_meta

    # Mock terminal
    mock_terminal = MagicMock()

    # Create TUI with mocked Alfred and terminal
    tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

    # Test with partial "abc" - should match sess_abc123 and sess_abc789
    results = tui._session_id_provider("/resume abc")

    # Should return sessions containing "abc"
    assert len(results) == 2
    values = [r[0] for r in results]
    assert "/resume sess_abc123" in values
    assert "/resume sess_abc789" in values
    assert "/resume sess_def456" not in values


def test_session_id_provider_returns_all_if_empty_partial():
    """Test that empty partial returns all sessions (limited to 5)."""
    from src.interfaces.pypitui.tui import AlfredTUI

    # Mock Alfred and session manager
    mock_alfred = MagicMock()
    mock_storage = MagicMock()
    mock_storage.list_sessions.return_value = [
        "sess_001",
        "sess_002",
        "sess_003",
    ]
    mock_alfred.session_manager.storage = mock_storage

    # Mock get_meta to return proper metadata objects
    mock_meta = MagicMock()
    mock_meta.last_active = datetime.now(UTC)
    mock_meta.current_count = 5
    mock_meta.archive_count = 2
    mock_storage.get_meta.return_value = mock_meta

    mock_terminal = MagicMock()
    tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

    # Test with empty partial
    results = tui._session_id_provider("/resume ")

    # Should return all sessions (limited to 5)
    assert len(results) == 3
    values = [r[0] for r in results]
    assert "/resume sess_001" in values
    assert "/resume sess_002" in values
    assert "/resume sess_003" in values


def test_session_id_provider_limits_to_5_results():
    """Test that provider limits results to 5."""
    from src.interfaces.pypitui.tui import AlfredTUI

    # Mock Alfred and session manager
    mock_alfred = MagicMock()
    mock_storage = MagicMock()
    # Create 10 sessions
    mock_storage.list_sessions.return_value = [f"sess_{i:03d}" for i in range(10)]
    mock_alfred.session_manager.storage = mock_storage

    # Mock get_meta to return proper metadata objects
    mock_meta = MagicMock()
    mock_meta.last_active = datetime.now(UTC)
    mock_meta.current_count = 5
    mock_meta.archive_count = 2
    mock_storage.get_meta.return_value = mock_meta

    mock_terminal = MagicMock()
    tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

    results = tui._session_id_provider("/resume ")

    # Should limit to 5 results
    assert len(results) == 5


def test_session_id_provider_returns_empty_if_wrong_prefix():
    """Test that provider returns empty list if text doesn't start with /resume."""
    from src.interfaces.pypitui.tui import AlfredTUI

    # Mock Alfred
    mock_alfred = MagicMock()
    mock_terminal = MagicMock()
    tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

    results = tui._session_id_provider("/new")
    assert results == []

    results = tui._session_id_provider("resume ")
    assert results == []


def test_session_id_provider_uses_fuzzy_matching():
    """Test that provider uses fuzzy matching for session IDs."""
    from src.interfaces.pypitui.tui import AlfredTUI

    # Mock Alfred and session manager
    mock_alfred = MagicMock()
    mock_storage = MagicMock()
    mock_storage.list_sessions.return_value = ["sess_abc123xyz"]
    mock_alfred.session_manager.storage = mock_storage

    # Mock get_meta to return proper metadata
    mock_meta = MagicMock()
    mock_meta.last_active = datetime.now(UTC)
    mock_meta.current_count = 5
    mock_meta.archive_count = 2
    mock_storage.get_meta.return_value = mock_meta

    mock_terminal = MagicMock()
    tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

    # Test with fuzzy query "a1x" - should match "abc123xyz"
    results = tui._session_id_provider("/resume a1x")

    # Should match because 'a', '1', 'x' appear in order in "abc123xyz"
    assert len(results) == 1
    assert results[0][0] == "/resume sess_abc123xyz"


def test_session_id_provider_is_case_insensitive():
    """Test that matching is case-insensitive."""
    from src.interfaces.pypitui.tui import AlfredTUI

    # Mock Alfred and session manager
    mock_alfred = MagicMock()
    mock_storage = MagicMock()
    mock_storage.list_sessions.return_value = ["sess_ABC123"]
    mock_alfred.session_manager.storage = mock_storage

    # Mock get_meta to return proper metadata
    mock_meta = MagicMock()
    mock_meta.last_active = datetime.now(UTC)
    mock_meta.current_count = 5
    mock_meta.archive_count = 2
    mock_storage.get_meta.return_value = mock_meta

    mock_terminal = MagicMock()
    tui = AlfredTUI(mock_alfred, terminal=mock_terminal)

    # Test with lowercase query
    results = tui._session_id_provider("/resume abc")

    assert len(results) == 1
    assert results[0][0] == "/resume sess_ABC123"
