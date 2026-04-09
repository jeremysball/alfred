"""Parity tests for Web UI server behavior.

These tests ensure the Web UI server uses the modern Alfred contract and
shared test fakes instead of legacy root-level fixture shapes.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from alfred.interfaces.webui import create_app
from alfred.interfaces.webui.daemon_bootstrap import DaemonBootstrapResult
from alfred.token_tracker import TokenTracker
from tests.webui.fakes import FakeAlfred


def _connect_and_consume_startup(websocket) -> tuple[dict, dict, dict]:
    """Receive the normal Web UI startup sequence."""

    connected = websocket.receive_json()
    session_loaded = websocket.receive_json()
    daemon_status = websocket.receive_json()
    status_update = websocket.receive_json()
    assert daemon_status["type"] == "daemon.status"
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


@pytest.mark.timeout(5)
def test_websocket_connect_emits_daemon_status_before_status_update(tmp_path) -> None:
    """Web UI should emit daemon.status separately from status.update."""

    pid_file = tmp_path / "cron-runner.pid"
    socket_path = tmp_path / "notify.sock"
    pid_file.write_text("4321")
    socket_path.write_text("socket")

    class FakeDaemonManager:
        def __init__(self) -> None:
            self.pid_file = pid_file

        def read_pid(self) -> int | None:
            return 4321

    fake_alfred = FakeAlfred()
    fake_alfred.socket_client.socket_path = socket_path
    fake_alfred.socket_client.is_connected = True
    client = TestClient(create_app(alfred_instance=fake_alfred))

    with patch("alfred.interfaces.webui.daemon_status.DaemonManager", FakeDaemonManager), client.websocket_connect("/ws") as websocket:
        connected = websocket.receive_json()
        session_loaded = websocket.receive_json()
        daemon_status = websocket.receive_json()
        status_update = websocket.receive_json()

    assert connected["type"] == "connected"
    assert session_loaded["type"] == "session.loaded"
    assert daemon_status["type"] == "daemon.status"
    assert daemon_status["payload"]["daemon"]["state"] == "running"
    assert daemon_status["payload"]["daemon"]["pid"] == 4321
    assert status_update["type"] == "status.update"
    assert "daemonStatus" not in status_update["payload"]
    assert "daemonPid" not in status_update["payload"]
    assert fake_alfred.synced_session_ids == [None]


@pytest.mark.timeout(5)
def test_websocket_connect_emits_failed_daemon_status_when_bootstrap_error_is_present(tmp_path) -> None:
    """Web UI should surface bootstrap failures in the initial daemon.status payload."""

    pid_file = tmp_path / "cron-runner.pid"

    class FakeDaemonManager:
        def __init__(self) -> None:
            self.pid_file = pid_file

        def read_pid(self) -> int | None:
            return None

    fake_alfred = FakeAlfred()
    app = create_app(alfred_instance=fake_alfred)
    app.state.webui_bootstrap_result = DaemonBootstrapResult(
        daemon_was_running=False,
        daemon_started=False,
        startup_error="daemon failed to start",
    )
    client = TestClient(app)

    with patch("alfred.interfaces.webui.daemon_status.DaemonManager", FakeDaemonManager), client.websocket_connect("/ws") as websocket:
        connected = websocket.receive_json()
        session_loaded = websocket.receive_json()
        daemon_status = websocket.receive_json()
        status_update = websocket.receive_json()

    assert connected["type"] == "connected"
    assert session_loaded["type"] == "session.loaded"
    assert daemon_status["type"] == "daemon.status"
    assert daemon_status["payload"]["daemon"]["state"] == "failed"
    assert daemon_status["payload"]["daemon"]["lastError"] == "daemon failed to start"
    assert status_update["type"] == "status.update"
    assert "daemonStatus" not in status_update["payload"]
    assert "daemonPid" not in status_update["payload"]


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


def test_status_update_includes_context_window_tokens_for_known_model() -> None:
    """Status updates should include the inferred model context window."""

    fake_alfred = FakeAlfred(model_name="kimi-k2-5", context_tokens=68272)
    client = TestClient(create_app(alfred_instance=fake_alfred))

    with client.websocket_connect("/ws") as websocket:
        connected, session_loaded, status_update = _connect_and_consume_startup(websocket)

    assert connected["type"] == "connected"
    assert session_loaded["type"] == "session.loaded"
    assert status_update["type"] == "status.update"
    assert status_update["payload"]["contextTokens"] == 68272
    assert status_update["payload"]["contextWindowTokens"] == 272000


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
        daemon_status = websocket.receive_json()
        status_update = websocket.receive_json()
        assert connected["type"] == "connected"
        assert daemon_status["type"] == "daemon.status"
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
        daemon_status = websocket.receive_json()
        status_update = websocket.receive_json()
        assert connected["type"] == "connected"
        assert daemon_status["type"] == "daemon.status"
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
        daemon_status = websocket.receive_json()
        status_update = websocket.receive_json()
        assert connected["type"] == "connected"
        assert daemon_status["type"] == "daemon.status"
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
        "blocked_context_files": ["SOUL.md"],
        "conflicted_context_files": [
            {
                "id": "soul",
                "name": "soul",
                "label": "SOUL.md",
                "reason": "Conflicted managed template SOUL.md is blocked",
            }
        ],
        "warnings": [],
        "support_state": {
            "enabled": True,
            "request": {"response_mode": "execute", "arc_id": "webui_cleanup"},
            "summary": {
                "response_mode": "execute",
                "active_arc_id": "webui_cleanup",
                "active_pattern_count": 1,
                "candidate_pattern_count": 0,
                "confirmed_pattern_count": 1,
                "recent_update_event_count": 1,
                "recent_intervention_count": 1,
                "active_domain_count": 1,
                "active_arc_count": 1,
            },
            "active_runtime_state": {
                "effective_support_values": {"pacing": "brisk"},
                "effective_relational_values": {"warmth": "medium"},
                "active_patterns": [
                    {
                        "pattern_id": "pattern-runtime-1",
                        "kind": "support_preference",
                        "scope": {"type": "arc", "id": "webui_cleanup", "label": "arc:webui_cleanup"},
                        "status": "confirmed",
                        "claim": "Short next steps work better here.",
                        "confidence": 0.91,
                    }
                ],
            },
            "learned_state": {
                "candidate_patterns_count": 0,
                "confirmed_patterns_count": 1,
                "recent_update_event_count": 1,
                "recent_intervention_count": 1,
                "candidate_patterns": [],
                "confirmed_patterns": [
                    {
                        "pattern_id": "pattern-confirmed-1",
                        "kind": "support_preference",
                        "scope": {"type": "global", "id": "user", "label": "global:user"},
                        "status": "confirmed",
                        "claim": "A single next step works better than many options.",
                        "confidence": 0.95,
                    }
                ],
                "recent_update_events": [
                    {
                        "event_id": "event-1",
                        "registry": "support",
                        "dimension": "pacing",
                        "scope": {"type": "arc", "id": "webui_cleanup", "label": "arc:webui_cleanup"},
                        "status": "applied",
                        "old_value": "steady",
                        "new_value": "brisk",
                        "reason": "The narrower pace improved follow-through.",
                        "confidence": 0.88,
                        "timestamp": "2026-03-23T00:00:00+00:00",
                    }
                ],
                "recent_interventions": [
                    {
                        "situation_id": "sit-1",
                        "session_id": "session-123",
                        "response_mode": "execute",
                        "intervention_family": "narrow",
                        "behavior_contract_summary": "One practical next step with firm pacing.",
                        "recorded_at": "2026-03-23T00:00:00+00:00",
                    }
                ],
            },
            "active_domains": [
                {"domain_id": "work", "name": "Work", "status": "active", "salience": 0.92}
            ],
            "active_arcs": [
                {
                    "arc_id": "webui_cleanup",
                    "title": "Web UI cleanup",
                    "kind": "project",
                    "status": "active",
                    "salience": 0.97,
                    "primary_domain_id": "work",
                }
            ],
        },
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
    assert response["payload"]["system_prompt"]["total_tokens"] == 12
    assert response["payload"]["blocked_context_files"] == ["SOUL.md"]
    assert response["payload"]["conflicted_context_files"] == [
        {
            "id": "soul",
            "name": "soul",
            "label": "SOUL.md",
            "reason": "Conflicted managed template SOUL.md is blocked",
        }
    ]
    assert response["payload"]["warnings"] == []
    assert response["payload"]["support_state"]["enabled"] is True
    assert response["payload"]["support_state"]["summary"]["active_arc_id"] == "webui_cleanup"
    assert response["payload"]["support_state"]["active_runtime_state"]["effective_support_values"] == {"pacing": "brisk"}
    assert response["payload"]["memories"]["displayed"] == 1
    assert response["payload"]["session_history"]["count"] == 1
    assert response["payload"]["tool_calls"]["count"] == 1
    assert response["payload"]["total_tokens"] == 32
    mock_get_context.assert_awaited_once_with(fake_alfred)


def test_context_info_refresh_keeps_disabled_sections_in_sync() -> None:
    """The refreshed /context payload should keep ids and labels aligned after toggles."""

    fake_alfred = FakeAlfred()

    class ToggleableContextLoader:
        def __init__(self) -> None:
            self._disabled_sections: set[str] = set()
            self._files = {
                "system": self._make_file("SYSTEM.md", "System prompt body"),
                "agents": self._make_file("AGENTS.md", "Agents prompt body"),
                "tools": self._make_file("TOOLS.md", "Tools prompt body"),
                "soul": self._make_file("SOUL.md", "Soul prompt body"),
                "user": self._make_file("USER.md", "User prompt body"),
            }

        @staticmethod
        def _make_file(name: str, content: str) -> SimpleNamespace:
            return SimpleNamespace(
                name=name,
                path=f"/workspace/alfred/{name}",
                content=content,
                is_blocked=lambda: False,
            )

        def toggle_section(self, section: str, enabled: bool) -> bool:
            section_id = section.upper()
            was_enabled = section_id not in self._disabled_sections
            if enabled:
                self._disabled_sections.discard(section_id)
            else:
                self._disabled_sections.add(section_id)
            return was_enabled != enabled

        def get_disabled_sections(self) -> list[str]:
            return sorted(self._disabled_sections)

        async def load_all(self) -> dict[str, SimpleNamespace]:
            return {
                section_id: file
                for section_id, file in self._files.items()
                if section_id.upper() not in self._disabled_sections
            }

    def build_self_model() -> SimpleNamespace:
        return SimpleNamespace(
            identity=SimpleNamespace(name="Alfred", role="Assistant"),
            runtime=SimpleNamespace(
                interface=SimpleNamespace(value="cli"),
                session_id="session-1",
                daemon_mode=False,
            ),
            capabilities=SimpleNamespace(
                memory_enabled=True,
                search_enabled=True,
                tools_available=["read", "write", "bash"],
            ),
            context_pressure=SimpleNamespace(
                message_count=1,
                memory_count=0,
                approximate_tokens=15,
            ),
        )

    fake_alfred.context_loader = ToggleableContextLoader()
    fake_alfred.core.memory_store = SimpleNamespace(get_all_entries=AsyncMock(return_value=[]))
    fake_alfred.build_self_model = build_self_model  # type: ignore[attr-defined]
    client = TestClient(create_app(alfred_instance=fake_alfred))

    with client.websocket_connect("/ws") as websocket:
        _connect_and_consume_startup(websocket)

        websocket.send_json({"type": "command.execute", "payload": {"command": "/context toggle SYSTEM off"}})
        toast = websocket.receive_json()
        response = websocket.receive_json()

    assert toast["type"] == "toast"
    assert response["type"] == "context.info"
    assert response["payload"]["disabled_sections"] == ["SYSTEM"]
    assert "disabledSections" not in response["payload"]
    assert response["payload"]["warnings"] == ["Disabled sections: SYSTEM"]
    assert [section["id"] for section in response["payload"]["system_prompt"]["sections"]] == [
        "agents",
        "tools",
        "soul",
        "user",
    ]
    assert [section["label"] for section in response["payload"]["system_prompt"]["sections"]] == [
        "AGENTS.md",
        "TOOLS.md",
        "SOUL.md",
        "USER.md",
    ]


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
        daemon_status = websocket.receive_json()
        status_update = websocket.receive_json()
        assert connected["type"] == "connected"
        assert daemon_status["type"] == "daemon.status"
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


def test_app_config_includes_debug_flag_when_false() -> None:
    """/app-config.js should return debug: false when server created without debug flag."""
    fake_alfred = FakeAlfred()
    client = TestClient(create_app(alfred_instance=fake_alfred, debug=False))

    response = client.get("/app-config.js")

    assert response.status_code == 200
    assert '"debug": false' in response.text or "'debug': False" in response.text


def test_app_config_includes_debug_flag_when_true() -> None:
    """/app-config.js should return debug: true when server created with debug=True."""
    fake_alfred = FakeAlfred()
    client = TestClient(create_app(alfred_instance=fake_alfred, debug=True))

    response = client.get("/app-config.js")

    assert response.status_code == 200
    assert '"debug": true' in response.text or "'debug': True" in response.text
