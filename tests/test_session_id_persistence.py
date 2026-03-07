"""Tests for session_id persistence in session storage (PRD #76)."""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.session import Message, Role, SessionManager
from src.session_storage import SessionStorage


@pytest.fixture
def mock_embedder() -> MagicMock:
    """Create a mock embedder."""
    embedder = MagicMock()
    embedder.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
    embedder.embed_batch = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    return embedder


@pytest.fixture
def storage(tmp_path: Path, mock_embedder: MagicMock) -> SessionStorage:
    """Create SessionStorage with a temporary data directory."""
    return SessionStorage(embedder=mock_embedder, data_dir=tmp_path)


@pytest.fixture
def session_manager(storage: SessionStorage) -> SessionManager:
    """Create initialized SessionManager with reset state."""
    SessionManager._instance = None
    SessionManager._storage = None
    SessionManager._sessions = {}
    SessionManager._cli_session_id = None

    SessionManager.initialize(storage)
    manager = SessionManager.get_instance()
    yield manager

    SessionManager._instance = None
    SessionManager._storage = None
    SessionManager._sessions = {}
    SessionManager._cli_session_id = None


def test_session_manager_assigns_session_id(session_manager: SessionManager) -> None:
    """Message added to session has session_id set."""
    session = session_manager.new_session()
    session_manager.add_message("user", "Hello")

    assert session.messages[0].session_id == session.meta.session_id


@pytest.mark.asyncio
async def test_storage_persists_session_id(storage: SessionStorage) -> None:
    """SessionStorage writes session_id to current.jsonl."""
    storage.create_session("sess_123")
    message = Message(
        idx=0,
        role=Role.USER,
        content="Hello",
        timestamp=datetime.now(UTC),
        session_id="sess_123",
    )

    await storage.append_message("sess_123", message)

    messages_path = storage.sessions_dir / "sess_123" / "current.jsonl"
    line = messages_path.read_text().strip()
    data = json.loads(line)

    assert data["session_id"] == "sess_123"


def test_load_messages_requires_session_id(storage: SessionStorage) -> None:
    """load_messages raises when session_id is missing."""
    storage.create_session("sess_missing")
    messages_path = storage.sessions_dir / "sess_missing" / "current.jsonl"
    payload = {
        "idx": 0,
        "role": "user",
        "content": "Hello",
        "timestamp": datetime.now(UTC).isoformat(),
    }
    messages_path.write_text(json.dumps(payload) + "\n")

    with pytest.raises(ValueError, match="session_id"):
        storage.load_messages("sess_missing")
