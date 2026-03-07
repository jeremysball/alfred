"""Integration test for session_id persistence in session message writes."""

import asyncio
import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.session import SessionManager
from src.session_storage import SessionStorage


@pytest.fixture
def mock_embedder() -> MagicMock:
    """Create a mock embedder."""
    embedder = MagicMock()
    embedder.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
    embedder.embed_batch = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    return embedder


@pytest.fixture
def session_manager(tmp_path: Path, mock_embedder: MagicMock) -> SessionManager:
    """Create an initialized SessionManager with clean singleton state."""
    SessionManager._instance = None
    SessionManager._storage = None
    SessionManager._sessions = {}
    SessionManager._cli_session_id = None

    storage = SessionStorage(embedder=mock_embedder, data_dir=tmp_path)
    SessionManager.initialize(storage)
    manager = SessionManager.get_instance()
    yield manager

    SessionManager._instance = None
    SessionManager._storage = None
    SessionManager._sessions = {}
    SessionManager._cli_session_id = None


async def _wait_for_message_file(path: Path, timeout_seconds: float = 1.0) -> None:
    """Wait for the message file to be written by the background task."""
    start = time.monotonic()
    while time.monotonic() - start < timeout_seconds:
        if path.exists() and path.read_text().strip():
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"Timed out waiting for message file {path}")


@pytest.mark.asyncio
async def test_message_written_gets_session_id(session_manager: SessionManager) -> None:
    """Message writes should include session_id in persisted JSON."""
    session = session_manager.new_session()
    session_manager.add_message("user", "Hello")

    messages_path = (
        session_manager.storage.sessions_dir
        / session.meta.session_id
        / "current.jsonl"
    )

    await _wait_for_message_file(messages_path)
    data = json.loads(messages_path.read_text().strip())

    assert data["session_id"] == session.meta.session_id
