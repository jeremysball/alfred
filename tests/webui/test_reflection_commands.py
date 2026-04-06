"""Tests for PRD #169 reflection slash-command surfaces in the Web UI server."""

from __future__ import annotations

from fastapi.testclient import TestClient

from alfred.interfaces.webui import create_app
from tests.webui.fakes import FakeAlfred


def _consume_startup(websocket) -> None:
    websocket.receive_json()  # connected
    websocket.receive_json()  # session.loaded
    websocket.receive_json()  # daemon.status
    websocket.receive_json()  # status.update



def test_support_command_renders_snapshot_through_chat_message_flow() -> None:
    """/support should reuse the normal assistant-message websocket flow for inspection output."""

    fake_alfred = FakeAlfred()
    client = TestClient(create_app(alfred_instance=fake_alfred))

    with client.websocket_connect("/ws") as websocket:
        _consume_startup(websocket)
        websocket.send_json({"type": "command.execute", "payload": {"command": "/support execute webui_cleanup"}})

        chat_started = websocket.receive_json()
        chat_chunk = websocket.receive_json()
        chat_complete = websocket.receive_json()

    assert chat_started["type"] == "chat.started"
    assert chat_chunk["type"] == "chat.chunk"
    assert "Support snapshot for execute (webui_cleanup)" in chat_chunk["payload"]["content"]
    assert chat_complete["type"] == "chat.complete"
    assert fake_alfred.support_calls[-1] == (
        "snapshot",
        (),
        {"response_mode": "execute", "arc_id": "webui_cleanup"},
    )



def test_support_confirm_command_routes_typed_correction_action() -> None:
    """/support confirm should build a typed correction action instead of a generic blob."""

    fake_alfred = FakeAlfred()
    client = TestClient(create_app(alfred_instance=fake_alfred))

    with client.websocket_connect("/ws") as websocket:
        _consume_startup(websocket)
        websocket.send_json(
            {
                "type": "command.execute",
                "payload": {"command": "/support confirm pattern-candidate-1 yes this one is real"},
            }
        )

        chat_started = websocket.receive_json()
        chat_chunk = websocket.receive_json()
        chat_complete = websocket.receive_json()

    assert chat_started["type"] == "chat.started"
    assert chat_chunk["type"] == "chat.chunk"
    assert "Applied correction: ConfirmPatternAction" in chat_chunk["payload"]["content"]
    assert chat_complete["type"] == "chat.complete"
    action = fake_alfred.support_calls[-1][1][0]
    assert type(action).__name__ == "ConfirmPatternAction"
    assert action.pattern_id == "pattern-candidate-1"
    assert action.reason == "yes this one is real"



def test_review_week_command_renders_weekly_review_output() -> None:
    """/review week should request the bounded weekly review surface."""

    fake_alfred = FakeAlfred()
    client = TestClient(create_app(alfred_instance=fake_alfred))

    with client.websocket_connect("/ws") as websocket:
        _consume_startup(websocket)
        websocket.send_json({"type": "command.execute", "payload": {"command": "/review week"}})

        chat_started = websocket.receive_json()
        chat_chunk = websocket.receive_json()
        chat_complete = websocket.receive_json()

    assert chat_started["type"] == "chat.started"
    assert chat_chunk["type"] == "chat.chunk"
    assert "Review mode: weekly" in chat_chunk["payload"]["content"]
    assert chat_complete["type"] == "chat.complete"
    assert fake_alfred.support_calls[-1] == ("review", (), {"mode": "weekly"})
