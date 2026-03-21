"""Contract tests for the Web UI test harness."""

from __future__ import annotations

from alfred.interfaces.webui.contracts import WebUIAlfred, WebUICore, WebUISessionManager
from alfred.session import Message, Session, SessionMeta, ToolCallRecord
from alfred.token_tracker import TokenTracker
from tests.webui.fakes import FakeAlfred, FakeCore, FakeSessionManager, make_message, make_session, make_session_meta, make_tool_call


def test_webui_contract_protocols_are_runtime_checkable() -> None:
    """The Web UI contract should be a runtime-checkable Protocol."""

    assert getattr(WebUISessionManager, "_is_runtime_protocol", False) is True
    assert getattr(WebUICore, "_is_runtime_protocol", False) is True
    assert getattr(WebUIAlfred, "_is_runtime_protocol", False) is True

    class _SessionManager:
        async def new_session_async(self) -> Session:
            raise NotImplementedError

        async def resume_session_async(self, session_id: str) -> Session:
            raise NotImplementedError

        async def list_sessions_async(self) -> list[SessionMeta]:
            raise NotImplementedError

        def get_current_cli_session(self) -> Session | None:
            raise NotImplementedError

        def start_session(self) -> Session:
            raise NotImplementedError

    class _Core:
        def __init__(self) -> None:
            self.session_manager = _SessionManager()

    class _Alfred:
        def __init__(self) -> None:
            self.core = _Core()
            self.token_tracker = TokenTracker()
            self.model_name = "kimi/test"

        async def chat_stream(
            self,
            message: str,
            tool_callback=None,
            session_id: str | None = None,
        ):
            if False:
                yield message

        async def stop(self) -> None:
            return None

        def sync_token_tracker_from_session(self, session_id: str | None = None) -> None:
            return None

    alfred = _Alfred()

    assert isinstance(alfred.core.session_manager, WebUISessionManager)
    assert isinstance(alfred.core, WebUICore)
    assert isinstance(alfred, WebUIAlfred)


def test_fake_harness_uses_real_production_models() -> None:
    """The fake harness should build real production session/message/token objects."""

    session_meta = make_session_meta("session-123")
    tool_call = make_tool_call("tool-123", tool_name="read", output="done")
    message = make_message("assistant", "hello", tool_calls=[tool_call])
    session = make_session("session-123", messages=[message])

    assert isinstance(session_meta, SessionMeta)
    assert isinstance(tool_call, ToolCallRecord)
    assert isinstance(message, Message)
    assert isinstance(session, Session)
    assert isinstance(FakeAlfred().token_tracker, TokenTracker)


def test_fake_alfred_matches_webui_protocols() -> None:
    """The fake top-level Alfred object should satisfy the Web UI contract."""

    fake = FakeAlfred()

    assert isinstance(fake, WebUIAlfred)
    assert isinstance(fake.core, WebUICore)
    assert isinstance(fake.core.session_manager, WebUISessionManager)
    assert isinstance(fake.core.session_manager, FakeSessionManager)
    assert isinstance(fake.core, FakeCore)
