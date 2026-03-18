"""Tests for WebSocket functionality."""

import pytest
from fastapi.testclient import TestClient

from alfred.interfaces.webui import create_app


def test_websocket_endpoint_exists():
    """Verify WebSocket endpoint accepts connections."""
    app = create_app()
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Receive initial connection message
        data = websocket.receive_text()
        assert data == "connected"


def test_websocket_echo_message():
    """Verify connected client can send/receive messages."""
    app = create_app()
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Receive initial connection message
        websocket.receive_text()

        # Send a message and verify echo
        websocket.send_text("hello")
        response = websocket.receive_text()
        assert response == "echo: hello"


def test_websocket_multiple_clients():
    """Verify server handles multiple concurrent connections."""
    app = create_app()
    client = TestClient(app)

    # Connect two clients
    with client.websocket_connect("/ws") as ws1:
        with client.websocket_connect("/ws") as ws2:
            # Both should receive connection message
            assert ws1.receive_text() == "connected"
            assert ws2.receive_text() == "connected"

            # Both should be able to send/receive independently
            ws1.send_text("client1")
            ws2.send_text("client2")

            assert ws1.receive_text() == "echo: client1"
            assert ws2.receive_text() == "echo: client2"
