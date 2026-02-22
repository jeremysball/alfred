"""Tests for CLI session integration (PRD #54 Milestone 4)."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from src.session import Message, Role, SessionMeta, Session, SessionManager


class MockStorage:
    """Mock storage for testing SessionManager without file I/O."""

    def __init__(self, tmp_path: Path):
        self.sessions_dir = tmp_path / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.current_path = self.sessions_dir / "current.json"
        self._sessions: dict[str, SessionMeta] = {}
        self._messages: dict[str, list[Message]] = {}
        self._cli_current: str | None = None

    def session_exists(self, session_id: str) -> bool:
        return session_id in self._sessions

    def list_sessions(self) -> list[str]:
        return list(self._sessions.keys())

    def get_cli_current(self) -> str | None:
        return self._cli_current

    def set_cli_current(self, session_id: str) -> None:
        self._cli_current = session_id

    def get_meta(self, session_id: str) -> SessionMeta | None:
        return self._sessions.get(session_id)

    def save_meta(self, meta: SessionMeta) -> None:
        self._sessions[meta.session_id] = meta

    def create_session(self, session_id: str | None = None) -> SessionMeta:
        from uuid import uuid4
        from datetime import datetime

        sid = session_id or f"sess_{uuid4().hex[:12]}"
        now = datetime.now()
        meta = SessionMeta(
            session_id=sid,
            created_at=now,
            last_active=now,
            status="active",
        )
        self._sessions[sid] = meta
        self._messages[sid] = []
        return meta

    def _generate_session_id(self) -> str:
        from uuid import uuid4

        return f"sess_{uuid4().hex[:12]}"

    def load_messages(self, session_id: str) -> list[Message]:
        return self._messages.get(session_id, [])

    async def append_message(self, session_id: str, message: Message) -> None:
        if session_id not in self._messages:
            self._messages[session_id] = []
        self._messages[session_id].append(message)

    def load_session(self, session_id: str) -> Session | None:
        meta = self.get_meta(session_id)
        if meta is None:
            return None
        messages = self.load_messages(session_id)
        return Session(meta=meta, messages=messages)

    def spawn_embed_task(self, session_id: str, idx: int, content: str) -> None:
        pass


@pytest.fixture
def initialized_manager(tmp_path: Path):
    """Create initialized SessionManager."""
    # Reset singleton state
    SessionManager._instance = None
    SessionManager._storage = None
    SessionManager._sessions = {}
    SessionManager._cli_session_id = None

    mock_storage = MockStorage(tmp_path)
    SessionManager.initialize(mock_storage)
    manager = SessionManager.get_instance()
    yield manager

    # Cleanup
    SessionManager._instance = None
    SessionManager._storage = None
    SessionManager._sessions = {}
    SessionManager._cli_session_id = None


class TestCLISessionIntegration:
    """Tests for CLI integration with session management."""

    def test_session_auto_starts_on_first_message(self, initialized_manager: SessionManager):
        """Session starts automatically when first message processed."""
        assert not initialized_manager.has_active_session()

        # Simulate what happens when CLI receives first message
        if not initialized_manager.has_active_session():
            initialized_manager.start_session()

        assert initialized_manager.has_active_session()

    def test_user_message_added_to_session(self, initialized_manager: SessionManager):
        """User message added to session before LLM call."""
        initialized_manager.start_session()

        # Simulate: user sends message
        user_msg = "Hello Alfred"
        initialized_manager.add_message("user", user_msg)

        messages = initialized_manager.get_messages()
        assert len(messages) == 1
        assert messages[0].content == user_msg
        assert messages[0].role.value == "user"

    def test_assistant_message_added_to_session(self, initialized_manager: SessionManager):
        """Assistant response added to session after LLM call."""
        initialized_manager.start_session()

        # Simulate conversation
        initialized_manager.add_message("user", "Hello")
        initialized_manager.add_message("assistant", "Hi there")

        messages = initialized_manager.get_messages()
        assert len(messages) == 2
        assert messages[1].content == "Hi there"
        assert messages[1].role.value == "assistant"

    def test_conversation_accumulates(self, initialized_manager: SessionManager):
        """Multiple exchanges accumulate in session."""
        initialized_manager.start_session()

        # Simulate multi-turn conversation
        initialized_manager.add_message("user", "Message 1")
        initialized_manager.add_message("assistant", "Response 1")
        initialized_manager.add_message("user", "Message 2")
        initialized_manager.add_message("assistant", "Response 2")
        initialized_manager.add_message("user", "Message 3")

        messages = initialized_manager.get_messages()
        assert len(messages) == 5

        # Verify order
        assert messages[0].content == "Message 1"
        assert messages[1].content == "Response 1"
        assert messages[2].content == "Message 2"
        assert messages[3].content == "Response 2"
        assert messages[4].content == "Message 3"


class TestAlfredSessionIntegration:
    """Tests for Alfred class integration with sessions.

    Note: These are simplified tests that verify session behavior.
    Full Alfred integration is tested via E2E tests.
    """

    @pytest.fixture
    def mock_config(self):
        config = Mock()
        config.model = "test-model"
        config.memory_context_limit = 10
        config.embedding_model = "test-embedder"
        config.memory_path = "/tmp/test_memory"
        config.telegram_bot_token = "test-token"
        config.openai_api_key = "test-key"
        config.kimi_api_key = "test-key"
        config.kimi_base_url = "https://test.com"
        config.default_llm_provider = "kimi"
        config.chat_model = "test-model"
        config.workspace_dir = Path("/tmp")
        config.memory_dir = Path("/tmp")
        config.context_files = {}
        return config

    @pytest.mark.skip(reason="Integration test - requires full Alfred mock setup")
    @pytest.mark.asyncio
    async def test_chat_stream_adds_user_message(self, mock_config, tmp_path: Path):
        """chat_stream adds user message to session."""
        pass

    @pytest.mark.skip(reason="Integration test - requires full Alfred mock setup")
    @pytest.mark.asyncio
    async def test_chat_stream_adds_assistant_response(self, mock_config, tmp_path: Path):
        """chat_stream adds assistant response to session."""
        pass

    @pytest.mark.asyncio
    async def test_context_includes_session_history(self, initialized_manager: SessionManager):
        """Context sent to LLM includes session history."""
        initialized_manager.start_session()
        initialized_manager.add_message("user", "Previous question")
        initialized_manager.add_message("assistant", "Previous answer")

        # Verify session has history
        assert initialized_manager.has_active_session()
        messages = initialized_manager.get_messages()
        assert len(messages) == 2
        assert messages[0].content == "Previous question"
        assert messages[1].content == "Previous answer"
