"""Tests for session storage persistence (PRD #53)."""

import json
import pytest
from datetime import datetime
from pathlib import Path

from src.session import Message, Role, SessionMeta
from src.session_storage import SessionStorage


@pytest.fixture
def sessions_dir(tmp_path: Path) -> Path:
    """Create temporary sessions directory."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir(parents=True)
    return sessions_dir


@pytest.fixture
def embedder():
    """Create mock embedder."""
    class MockEmbedder:
        async def embed(self, text: str) -> list[float]:
            return [0.1, 0.2, 0.3]

        async def embed_batch(self, texts: list[str]) -> list[list[float]]:
            return [[0.1, 0.2, 0.3] for _ in texts]

    return MockEmbedder()


@pytest.fixture
def storage(sessions_dir: Path, embedder) -> SessionStorage:
    """Create SessionStorage instance."""
    # Create storage with sessions_dir injected directly
    storage = SessionStorage.__new__(SessionStorage)
    storage.sessions_dir = sessions_dir
    storage.current_path = sessions_dir / "current.json"
    storage.embedder = embedder
    return storage


class TestSessionDiscovery:
    """Tests for session discovery."""

    def test_session_exists_false(self, storage: SessionStorage):
        """session_exists returns False for non-existent session."""
        assert not storage.session_exists("nonexistent")

    def test_session_exists_true(self, storage: SessionStorage):
        """session_exists returns True after session created."""
        storage.create_session("test123")
        assert storage.session_exists("test123")

    def test_list_sessions_empty(self, storage: SessionStorage):
        """list_sessions returns empty list when no sessions."""
        assert storage.list_sessions() == []

    def test_list_sessions_returns_all(self, storage: SessionStorage):
        """list_sessions returns all session IDs."""
        storage.create_session("sess_aaa")
        storage.create_session("sess_bbb")
        storage.create_session("sess_ccc")

        sessions = storage.list_sessions()
        assert len(sessions) == 3
        assert "sess_aaa" in sessions
        assert "sess_bbb" in sessions
        assert "sess_ccc" in sessions


class TestCLICurrentSession:
    """Tests for CLI current session tracking."""

    def test_get_cli_current_none(self, storage: SessionStorage):
        """get_cli_current returns None when no current session."""
        assert storage.get_cli_current() is None

    def test_set_and_get_cli_current(self, storage: SessionStorage):
        """set_cli_current and get_cli_current work together."""
        storage.set_cli_current("sess_abc123")
        assert storage.get_cli_current() == "sess_abc123"

    def test_set_cli_current_overwrites(self, storage: SessionStorage):
        """set_cli_current overwrites previous value."""
        storage.set_cli_current("sess_first")
        storage.set_cli_current("sess_second")
        assert storage.get_cli_current() == "sess_second"


class TestSessionMetadata:
    """Tests for session metadata."""

    def test_get_meta_none(self, storage: SessionStorage):
        """get_meta returns None for non-existent session."""
        assert storage.get_meta("nonexistent") is None

    def test_save_and_get_meta(self, storage: SessionStorage):
        """save_meta and get_meta work together."""
        now = datetime.now()
        meta = SessionMeta(
            session_id="test123",
            created_at=now,
            last_active=now,
            status="active",
            current_count=5,
            archive_count=3,
        )
        storage.save_meta(meta)

        loaded = storage.get_meta("test123")
        assert loaded is not None
        assert loaded.session_id == "test123"
        assert loaded.status == "active"
        assert loaded.current_count == 5
        assert loaded.archive_count == 3
        assert loaded.message_count == 8

    def test_get_meta_invalid_json(self, storage: SessionStorage):
        """get_meta raises on invalid JSON."""
        session_dir = storage.sessions_dir / "bad_session"
        session_dir.mkdir(parents=True)
        (session_dir / "meta.json").write_text("not valid json")

        with pytest.raises(ValueError, match="Invalid meta.json"):
            storage.get_meta("bad_session")


class TestSessionCreation:
    """Tests for session creation."""

    def test_create_session_generates_id(self, storage: SessionStorage):
        """create_session generates ID when not provided."""
        meta = storage.create_session()

        assert meta.session_id.startswith("sess_")
        assert len(meta.session_id) == 17  # "sess_" + 12 hex chars
        assert meta.status == "active"
        assert storage.session_exists(meta.session_id)

    def test_create_session_with_id(self, storage: SessionStorage):
        """create_session uses provided ID."""
        meta = storage.create_session("custom_id")

        assert meta.session_id == "custom_id"
        assert storage.session_exists("custom_id")

    def test_create_session_creates_files(self, storage: SessionStorage):
        """create_session creates session folder and files."""
        meta = storage.create_session("test123")

        session_dir = storage.sessions_dir / "test123"
        assert session_dir.is_dir()
        assert (session_dir / "meta.json").exists()
        assert (session_dir / "current.jsonl").exists()


class TestMessages:
    """Tests for message persistence."""

    def test_load_messages_empty(self, storage: SessionStorage):
        """load_messages returns empty list for new session."""
        storage.create_session("test123")
        messages = storage.load_messages("test123")
        assert messages == []

    def test_append_and_load_messages(self, storage: SessionStorage):
        """append_message and load_messages work together."""
        storage.create_session("test123")

        msg1 = Message(
            idx=0,
            role=Role.USER,
            content="Hello",
            timestamp=datetime.now(),
        )
        msg2 = Message(
            idx=1,
            role=Role.ASSISTANT,
            content="Hi there",
            timestamp=datetime.now(),
        )

        import asyncio
        asyncio.run(storage.append_message("test123", msg1))
        asyncio.run(storage.append_message("test123", msg2))

        messages = storage.load_messages("test123")
        assert len(messages) == 2
        assert messages[0].role == Role.USER
        assert messages[0].content == "Hello"
        assert messages[1].role == Role.ASSISTANT
        assert messages[1].content == "Hi there"

    def test_update_message_embedding(self, storage: SessionStorage):
        """update_message_embedding updates embedding in place."""
        storage.create_session("test123")

        msg = Message(
            idx=0,
            role=Role.USER,
            content="Hello",
            timestamp=datetime.now(),
            embedding=None,
        )

        import asyncio
        asyncio.run(storage.append_message("test123", msg))
        asyncio.run(storage.update_message_embedding("test123", 0, [0.5, 0.6, 0.7]))

        messages = storage.load_messages("test123")
        assert len(messages) == 1
        assert messages[0].embedding == [0.5, 0.6, 0.7]


class TestFullSessionLoad:
    """Tests for full session loading."""

    def test_load_session_nonexistent(self, storage: SessionStorage):
        """load_session returns None for non-existent session."""
        assert storage.load_session("nonexistent") is None

    def test_load_session_full(self, storage: SessionStorage):
        """load_session returns meta and messages together."""
        storage.create_session("test123")

        msg = Message(
            idx=0,
            role=Role.USER,
            content="Hello",
            timestamp=datetime.now(),
        )

        import asyncio
        asyncio.run(storage.append_message("test123", msg))

        # Update meta
        meta = storage.get_meta("test123")
        assert meta is not None
        meta.current_count = 1
        storage.save_meta(meta)

        session = storage.load_session("test123")
        assert session is not None
        assert session.meta.session_id == "test123"
        assert len(session.messages) == 1
        assert session.messages[0].content == "Hello"
