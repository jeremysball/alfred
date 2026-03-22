"""Parity tests for Web UI server behavior.

These tests ensure the Web UI server uses the modern Alfred contract and
shared test fakes instead of legacy root-level fixture shapes.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from alfred.interfaces.webui import create_app
from alfred.token_tracker import TokenTracker
from tests.webui.fakes import FakeAlfred


def _connect_and_consume_startup(websocket) -> tuple[dict, dict, dict]:
    """Receive the normal Web UI startup sequence."""

    connected = websocket.receive_json()
    session_loaded = websocket.receive_json()
    status_update = websocket.receive_json()
    return connected, session_loaded, status_update


class LegacyBaseAlfred:
    """Legacy Alfred shape kept only for negative contract tests."""

    def __init__(self) -> None:
        self.core = type("LegacyCore", (), {})()
        self.token_tracker = TokenTracker()
        self.model_name = "legacy/test"
        self.config = {"model": "legacy/test"}


class LegacyNewSessionAlfred(LegacyBaseAlfred):
    def __init__(self) -> None:
        super().__init__()
        self.new_session_called = False

    async def new_session(self):
        self.new_session_called = True
        return object()


class LegacyResumeAlfred(LegacyBaseAlfred):
    def __init__(self) -> None:
        super().__init__()
        self.resume_session_called = False

    async def resume_session(self, session_id):
        self.resume_session_called = True
        return object()


class LegacyListSessionsAlfred(LegacyBaseAlfred):
    def __init__(self) -> None:
        super().__init__()
        self.list_sessions_called = False

    async def list_sessions(self, limit=10):
        self.list_sessions_called = True
        return []


class LegacyCurrentSessionAlfred(LegacyBaseAlfred):
    def __init__(self) -> None:
        super().__init__()
        self.current_session_called = False
        self._current_session = object()

    @property
    def current_session(self):
        self.current_session_called = True
        return self._current_session


class LegacyContextAlfred(LegacyBaseAlfred):
    def __init__(self) -> None:
        super().__init__()
        self.get_context_called = False

    def get_context(self):
        self.get_context_called = True
        return {"cwd": "/tmp"}


def test_websocket_connect_syncs_token_tracker_and_sends_status_update() -> None:
    """Web UI should reuse Alfred token tracker for historical session totals."""

    class FakeDaemonManager:
        def is_running(self) -> bool:
            return True

        def read_pid(self) -> int | None:
            return 4321

    fake_alfred = FakeAlfred()
    client = TestClient(create_app(alfred_instance=fake_alfred))

    with patch("alfred.interfaces.webui.server.DaemonManager", FakeDaemonManager), client.websocket_connect("/ws") as websocket:
        connected, session_loaded, status_update = _connect_and_consume_startup(websocket)

    assert connected["type"] == "connected"
    assert session_loaded["type"] == "session.loaded"
    assert status_update["type"] == "status.update"
    assert status_update["payload"] == {
        "model": "kimi/k2-test",
        "contextTokens": 321,
        "inputTokens": 11,
        "outputTokens": 22,
        "cacheReadTokens": 3,
        "reasoningTokens": 4,
        "queueLength": 0,
        "isStreaming": False,
        "daemonStatus": "running",
        "daemonPid": 4321,
    }
    assert fake_alfred.synced_session_ids == [None]


def test_websocket_connect_ignores_dict_config_when_contract_is_valid() -> None:
    """A dict-shaped config should not suppress normal startup behavior."""

    fake_alfred = FakeAlfred(config={"model": "custom/test"})
    client = TestClient(create_app(alfred_instance=fake_alfred))

    with client.websocket_connect("/ws") as websocket:
        connected, session_loaded, status_update = _connect_and_consume_startup(websocket)

    assert connected["type"] == "connected"
    assert session_loaded["type"] == "session.loaded"
    assert status_update["type"] == "status.update"
    assert fake_alfred.config == {"model": "custom/test"}


def test_resume_command_syncs_historical_tokens_for_resumed_session() -> None:
    """/resume should mirror TUI behavior by syncing historical token totals."""

    fake_alfred = FakeAlfred()
    client = TestClient(create_app(alfred_instance=fake_alfred))

    with client.websocket_connect("/ws") as websocket:
        _connect_and_consume_startup(websocket)

        websocket.send_json({"type": "command.execute", "payload": {"command": "/resume session-2"}})

        session_loaded = websocket.receive_json()
        status_update = websocket.receive_json()

    assert session_loaded["type"] == "session.loaded"
    assert session_loaded["payload"]["sessionId"] == "session-2"
    assert status_update["type"] == "status.update"
    assert status_update["payload"]["inputTokens"] == 44
    assert status_update["payload"]["outputTokens"] == 55
    assert status_update["payload"]["cacheReadTokens"] == 6
    assert status_update["payload"]["reasoningTokens"] == 7
    assert fake_alfred.synced_session_ids[-1] == "session-2"


def test_new_command_resets_status_totals_for_fresh_session() -> None:
    """/new should mirror TUI behavior by clearing token totals."""

    fake_alfred = FakeAlfred()
    client = TestClient(create_app(alfred_instance=fake_alfred))

    with client.websocket_connect("/ws") as websocket:
        _connect_and_consume_startup(websocket)

        websocket.send_json({"type": "command.execute", "payload": {"command": "/new"}})

        session_new = websocket.receive_json()
        status_update = websocket.receive_json()

    assert session_new["type"] == "session.new"
    assert session_new["payload"]["sessionId"] == "session-3"
    assert status_update["type"] == "status.update"
    assert status_update["payload"]["inputTokens"] == 0
    assert status_update["payload"]["outputTokens"] == 0
    assert status_update["payload"]["cacheReadTokens"] == 0
    assert status_update["payload"]["reasoningTokens"] == 0


def test_new_command_rejects_legacy_root_level_new_session_shape() -> None:
    """The server should not fall back to root-level new_session()."""

    legacy = LegacyNewSessionAlfred()
    client = TestClient(create_app(alfred_instance=legacy))

    with client.websocket_connect("/ws") as websocket:
        connected = websocket.receive_json()
        status_update = websocket.receive_json()
        assert connected["type"] == "connected"
        assert status_update["type"] == "status.update"

        websocket.send_json({"type": "command.execute", "payload": {"command": "/new"}})

        response = websocket.receive_json()

    assert response["type"] == "chat.error"
    assert legacy.new_session_called is False


def test_sessions_command_marks_current_session_and_uses_live_message_count() -> None:
    """/sessions should mirror TUI current-session metadata behavior."""

    fake_alfred = FakeAlfred()
    current_session = fake_alfred.core.session_manager.get_current_cli_session()
    assert current_session is not None
    current_session.meta.message_count = 5
    client = TestClient(create_app(alfred_instance=fake_alfred))

    with client.websocket_connect("/ws") as websocket:
        _connect_and_consume_startup(websocket)

        websocket.send_json({"type": "command.execute", "payload": {"command": "/sessions"}})
        response = websocket.receive_json()

    assert response["type"] == "session.list"
    first_session = response["payload"]["sessions"][0]
    assert first_session["id"] == "session-1"
    assert first_session["isCurrent"] is True
    assert first_session["messageCount"] == 5


def test_sessions_command_rejects_legacy_root_level_list_sessions_shape() -> None:
    """The server should not fall back to root-level list_sessions()."""

    legacy = LegacyListSessionsAlfred()
    client = TestClient(create_app(alfred_instance=legacy))

    with client.websocket_connect("/ws") as websocket:
        connected = websocket.receive_json()
        status_update = websocket.receive_json()
        assert connected["type"] == "connected"
        assert status_update["type"] == "status.update"

        websocket.send_json({"type": "command.execute", "payload": {"command": "/sessions"}})

        response = websocket.receive_json()

    assert response["type"] == "chat.error"
    assert legacy.list_sessions_called is False


def test_session_command_rejects_legacy_root_level_current_session_shape() -> None:
    """The server should not fall back to root-level current_session."""

    legacy = LegacyCurrentSessionAlfred()
    client = TestClient(create_app(alfred_instance=legacy))

    with client.websocket_connect("/ws") as websocket:
        connected = websocket.receive_json()
        status_update = websocket.receive_json()
        assert connected["type"] == "connected"
        assert status_update["type"] == "status.update"

        websocket.send_json({"type": "command.execute", "payload": {"command": "/session"}})

        response = websocket.receive_json()

    assert response["type"] == "chat.error"
    assert legacy.current_session_called is False


def test_context_command_uses_shared_context_display() -> None:
    "/context should reuse the shared context display implementation."

    fake_alfred = FakeAlfred()
    client = TestClient(create_app(alfred_instance=fake_alfred))
    context_data = {
        "system_prompt": {"sections": [{"name": "AGENTS.md", "tokens": 12}], "total_tokens": 12},
        "memories": {
            "displayed": 1,
            "total": 2,
            "items": [{"role": "user", "content": "Remember this", "timestamp": "2026-03-20"}],
            "tokens": 8,
        },
        "session_history": {"count": 1, "messages": [{"role": "user", "content": "hello"}], "tokens": 3},
        "tool_calls": {
            "count": 1,
            "items": [
                {
                    "tool_name": "read",
                    "arguments": {"path": "README.md"},
                    "output": "file contents",
                    "status": "success",
                }
            ],
            "tokens": 9,
        },
        "total_tokens": 32,
    }

    with (
        patch(
            "alfred.context_display.get_context_display",
            AsyncMock(return_value=context_data),
        ) as mock_get_context,
        client.websocket_connect("/ws") as websocket,
    ):
        _connect_and_consume_startup(websocket)

        websocket.send_json({"type": "command.execute", "payload": {"command": "/context"}})
        response = websocket.receive_json()

    assert response["type"] == "context.info"
    assert response["payload"]["systemPrompt"]["totalTokens"] == 12
    assert response["payload"]["memories"]["displayed"] == 1
    assert response["payload"]["sessionHistory"]["count"] == 1
    assert response["payload"]["toolCalls"]["count"] == 1
    assert response["payload"]["totalTokens"] == 32
    mock_get_context.assert_awaited_once_with(fake_alfred)


def test_context_command_rejects_legacy_get_context_shape() -> None:
    """The server should not fall back to legacy get_context()."""

    legacy = LegacyContextAlfred()
    client = TestClient(create_app(alfred_instance=legacy))

    with (
        patch(
            "alfred.context_display.get_context_display",
            AsyncMock(side_effect=RuntimeError("boom")),
        ),
        client.websocket_connect("/ws") as websocket,
    ):
        connected = websocket.receive_json()
        status_update = websocket.receive_json()
        assert connected["type"] == "connected"
        assert status_update["type"] == "status.update"

        websocket.send_json({"type": "command.execute", "payload": {"command": "/context"}})

        response = websocket.receive_json()

    assert response["type"] == "chat.error"
    assert legacy.get_context_called is False


def test_session_command_matches_tui_session_details() -> None:
    """/session should expose the same core session metadata the TUI shows."""

    fake_alfred = FakeAlfred()
    client = TestClient(create_app(alfred_instance=fake_alfred))

    with client.websocket_connect("/ws") as websocket:
        _connect_and_consume_startup(websocket)

        websocket.send_json({"type": "command.execute", "payload": {"command": "/session"}})
        response = websocket.receive_json()

    assert response["type"] == "session.info"
    assert response["payload"]["sessionId"] == "session-1"
    assert response["payload"]["status"] == "active"
    assert "lastActive" in response["payload"]
    assert response["payload"]["messageCount"] == 1
