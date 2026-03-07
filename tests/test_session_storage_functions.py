"""Tests for Phase 2 session storage standalone functions."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from src.session_storage import SessionStorage, ensure_sessions_dir, create_session_folder
from src.session_storage import store_session_message, get_session_messages


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory."""
    return tmp_path


@pytest.fixture
def mock_embedder() -> MagicMock:
    """Create a mock embedder."""
    return MagicMock()


class TestEnsureSessionsDir:
    """Test ensure_sessions_dir function."""

    def test_ensure_sessions_dir_creates_directory(self, temp_data_dir: Path) -> None:
        """Verify data/sessions/ directory is created."""
        sessions_dir = ensure_sessions_dir(temp_data_dir)
        
        assert sessions_dir.exists()
        assert sessions_dir.is_dir()
        assert sessions_dir.name == "sessions"
        assert sessions_dir.parent == temp_data_dir


class TestCreateSessionFolder:
    """Test create_session_folder function."""

    def test_create_session_folder_creates_folder(
        self, temp_data_dir: Path, mock_embedder: MagicMock
    ) -> None:
        """Verify {session_id}/ folder is created."""
        storage = SessionStorage(embedder=mock_embedder, data_dir=temp_data_dir)
        session_id = "test_session_123"
        
        session_path = create_session_folder(storage, session_id)
        
        assert session_path.exists()
        assert session_path.is_dir()
        assert session_path.name == session_id


class TestStoreSessionMessage:
    """Test store_session_message function."""

    async def test_store_session_message_writes_to_jsonl(
        self, temp_data_dir: Path, mock_embedder: MagicMock
    ) -> None:
        """Verify message written to {session_id}/messages.jsonl."""
        from src.session import Message, Role
        from datetime import UTC, datetime
        
        storage = SessionStorage(embedder=mock_embedder, data_dir=temp_data_dir)
        session_id = "test_session_456"
        
        # Create session folder first
        create_session_folder(storage, session_id)
        
        message = Message(
            idx=0,
            role=Role.USER,
            content="Test message content",
            timestamp=datetime.now(UTC),
            session_id=session_id,
        )
        
        await store_session_message(storage, session_id, message)
        
        # Verify message was stored
        messages = await get_session_messages(storage, session_id)
        assert len(messages) == 1
        assert messages[0].content == "Test message content"


class TestGetSessionMessages:
    """Test get_session_messages function."""

    async def test_get_session_messages_returns_all_messages(
        self, temp_data_dir: Path, mock_embedder: MagicMock
    ) -> None:
        """Verify retrieval returns list of messages."""
        from src.session import Message, Role
        from datetime import UTC, datetime
        
        storage = SessionStorage(embedder=mock_embedder, data_dir=temp_data_dir)
        session_id = "test_session_789"
        
        # Create session and store messages
        create_session_folder(storage, session_id)
        
        for i in range(3):
            message = Message(
                idx=i,
                role=Role.USER if i % 2 == 0 else Role.ASSISTANT,
                content=f"Message {i}",
                timestamp=datetime.now(UTC),
                session_id=session_id,
            )
            await store_session_message(storage, session_id, message)
        
        messages = await get_session_messages(storage, session_id)
        
        assert len(messages) == 3
        assert messages[0].content == "Message 0"
        assert messages[1].content == "Message 1"
        assert messages[2].content == "Message 2"
