"""Tests for ServiceLocator pattern."""

import pytest
from alfred.container import ServiceLocator
from alfred.storage.sqlite import SQLiteStore
from alfred.session import SessionManager
from alfred.tools.search_sessions import SessionSummarizer


class TestServiceLocator:
    """Tests for ServiceLocator dependency injection."""

    def test_register_and_resolve(self, tmp_path):
        """Verify services can be registered and resolved."""
        # Clear any previous registrations
        ServiceLocator.clear()
        
        # Create and register a service
        db_path = tmp_path / "test.db"
        store = SQLiteStore(db_path)
        ServiceLocator.register(SQLiteStore, store)
        
        # Resolve and verify
        resolved = ServiceLocator.resolve(SQLiteStore)
        assert resolved is store

    def test_resolve_unregistered_raises(self):
        """Verify resolving unregistered service raises KeyError."""
        ServiceLocator.clear()
        
        with pytest.raises(KeyError, match="SQLiteStore not registered"):
            ServiceLocator.resolve(SQLiteStore)

    def test_has_service(self, tmp_path):
        """Verify has() checks registration."""
        ServiceLocator.clear()
        
        assert not ServiceLocator.has(SQLiteStore)
        
        db_path = tmp_path / "test.db"
        store = SQLiteStore(db_path)
        ServiceLocator.register(SQLiteStore, store)
        
        assert ServiceLocator.has(SQLiteStore)

    def test_multiple_services(self, tmp_path):
        """Verify multiple services can be registered."""
        ServiceLocator.clear()
        
        db_path = tmp_path / "test.db"
        store = SQLiteStore(db_path)
        
        # Mock summarizer
        class MockSummarizer:
            pass
        
        ServiceLocator.register(SQLiteStore, store)
        ServiceLocator.register(SessionSummarizer, MockSummarizer())
        
        # Verify both can be resolved
        assert ServiceLocator.resolve(SQLiteStore) is store
        assert isinstance(ServiceLocator.resolve(SessionSummarizer), MockSummarizer)

    def test_clear_removes_all(self, tmp_path):
        """Verify clear() removes all registrations."""
        ServiceLocator.clear()
        
        db_path = tmp_path / "test.db"
        store = SQLiteStore(db_path)
        ServiceLocator.register(SQLiteStore, store)
        
        assert ServiceLocator.has(SQLiteStore)
        
        ServiceLocator.clear()
        
        assert not ServiceLocator.has(SQLiteStore)
