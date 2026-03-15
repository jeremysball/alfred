"""Tests for SessionManager as a Service via ServiceLocator."""

from alfred.config import load_config
from alfred.container import ServiceLocator
from alfred.session import SessionManager
from alfred.storage.sqlite import SQLiteStore


class TestSessionManagerService:
    """Test SessionManager service pattern and ServiceLocator integration."""

    def test_session_manager_created_directly(self, tmp_path):
        """SessionManager should be creatable via constructor."""
        store = SQLiteStore(tmp_path / "test.db")
        manager = SessionManager(store=store, data_dir=tmp_path)

        assert isinstance(manager, SessionManager)
        assert manager.store is store

    def test_session_manager_registered_in_locator(self, tmp_path):
        """SessionManager should be resolvable from ServiceLocator."""
        store = SQLiteStore(tmp_path / "test.db")
        manager = SessionManager(store=store, data_dir=tmp_path)

        ServiceLocator.register(SessionManager, manager)
        resolved = ServiceLocator.resolve(SessionManager)

        assert resolved is manager

    def test_session_manager_not_singleton(self, tmp_path):
        """Multiple SessionManager instances should be independent."""
        store1 = SQLiteStore(tmp_path / "test1.db")
        store2 = SQLiteStore(tmp_path / "test2.db")

        manager1 = SessionManager(store=store1, data_dir=tmp_path / "dir1")
        manager2 = SessionManager(store=store2, data_dir=tmp_path / "dir2")

        # Should be independent instances
        assert manager1 is not manager2
        assert manager1.store is not manager2.store

    def test_session_manager_no_class_level_state(self, tmp_path):
        """SessionManager should not use class-level singleton state."""
        store = SQLiteStore(tmp_path / "test.db")
        manager = SessionManager(store=store, data_dir=tmp_path)

        # CLI session ID should be instance-level
        manager._cli_session_id = "test-session"

        # Creating another manager should not share the CLI session
        store2 = SQLiteStore(tmp_path / "test2.db")
        manager2 = SessionManager(store=store2, data_dir=tmp_path)

        assert manager2._cli_session_id is None


class TestSessionManagerIntegration:
    """Integration tests for SessionManager service."""

    def test_alfred_core_creates_session_manager(self, tmp_path, monkeypatch):
        """AlfredCore should create SessionManager directly."""
        from alfred.core import AlfredCore

        # Mock config
        config = load_config()
        monkeypatch.setattr(config, "data_dir", tmp_path)

        core = AlfredCore(config)

        assert core.session_manager is not None
        assert isinstance(core.session_manager, SessionManager)

        # Should be in ServiceLocator
        resolved = ServiceLocator.resolve(SessionManager)
        assert resolved is core.session_manager
