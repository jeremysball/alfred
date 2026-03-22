"""Web UI keepalive regressions for long-running assistant streams."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from alfred.interfaces.webui import create_app
from tests.webui.fakes import FakeAlfred

STREAM_CONTENT = ["chunk "] * 120


def _consume_startup_messages(websocket) -> None:
    """Read the standard websocket startup sequence."""

    assert websocket.receive_json()["type"] == "connected"
    assert websocket.receive_json()["type"] == "session.loaded"
    assert websocket.receive_json()["type"] == "status.update"


def _drain_chat_until_complete(websocket) -> None:
    """Consume a streaming turn until chat.complete and trailing status.update."""

    saw_complete = False
    while not saw_complete:
        message = websocket.receive_json()
        message_type = message["type"]
        if message_type == "chat.complete":
            saw_complete = True
        elif message_type in {"chat.chunk", "reasoning.chunk", "status.update", "pong"}:
            continue
        else:
            pytest.fail(f"Unexpected websocket message while draining: {message_type}")

    trailing = websocket.receive_json()
    assert trailing["type"] == "status.update"


def test_ping_receives_pong_before_chat_complete_during_long_stream() -> None:
    """Long assistant turns must not block websocket keepalive pings."""

    fake_alfred = FakeAlfred(chunks=STREAM_CONTENT, chunk_delay=0.01)
    client = TestClient(create_app(alfred_instance=fake_alfred))

    with client.websocket_connect("/ws") as websocket:
        _consume_startup_messages(websocket)

        websocket.send_json({"type": "chat.send", "payload": {"content": "stream for a while"}})
        started = websocket.receive_json()
        assert started["type"] == "chat.started"

        websocket.send_json({"type": "ping"})

        saw_pong_before_complete = False
        while True:
            message = websocket.receive_json()
            message_type = message["type"]
            if message_type == "pong":
                saw_pong_before_complete = True
            elif message_type == "chat.complete":
                break
            elif message_type in {"chat.chunk", "reasoning.chunk", "status.update"}:
                continue
            else:
                pytest.fail(f"Unexpected websocket message during streaming keepalive test: {message_type}")

        assert saw_pong_before_complete is True

        trailing = websocket.receive_json()
        assert trailing["type"] == "status.update"


def test_debug_turn_summary_reports_ping_during_active_stream(caplog: pytest.LogCaptureFixture) -> None:
    """Debug summaries should say when keepalive traffic was handled mid-stream."""

    fake_alfred = FakeAlfred(chunks=STREAM_CONTENT, chunk_delay=0.01)
    client = TestClient(create_app(alfred_instance=fake_alfred, debug=True))

    with caplog.at_level("DEBUG", logger="alfred.interfaces.webui.server"), client.websocket_connect("/ws") as websocket:
        _consume_startup_messages(websocket)

        websocket.send_json({"type": "chat.send", "payload": {"content": "observe the keepalive"}})
        started = websocket.receive_json()
        assert started["type"] == "chat.started"

        websocket.send_json({"type": "ping"})
        _drain_chat_until_complete(websocket)

    turn_logs = [record.message for record in caplog.records if "webui.websocket.turn_summary" in record.message]
    assert turn_logs
    assert "pings_during_stream=1" in turn_logs[-1]
