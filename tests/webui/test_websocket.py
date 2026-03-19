"""Tests for WebSocket functionality."""

import signal
import subprocess
import time
from threading import Thread

import pytest
import requests
import websocket as ws_client
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
    with client.websocket_connect("/ws") as ws1, client.websocket_connect("/ws") as ws2:
        # Both should receive connection message
        assert ws1.receive_text() == "connected"
        assert ws2.receive_text() == "connected"

        # Both should be able to send/receive independently
        ws1.send_text("client1")
        ws2.send_text("client2")

        assert ws1.receive_text() == "echo: client1"
        assert ws2.receive_text() == "echo: client2"


def test_websocket_connections_closed_on_shutdown():
    """Verify active WebSocket connections are closed cleanly on server shutdown.

    Starts server in subprocess, connects WebSocket client, triggers shutdown
    via SIGINT, and verifies connection is terminated.
    """
    port = 19998  # Use unique port to avoid conflicts
    ws_url = f"ws://127.0.0.1:{port}/ws"
    health_url = f"http://127.0.0.1:{port}/health"

    # Start server in subprocess
    proc = subprocess.Popen(
        [
            "uv",
            "run",
            "python",
            "-c",
            f"from alfred.interfaces.webui.server import create_app; "
            f"import uvicorn; "
            f"uvicorn.run(create_app(), host='127.0.0.1', port={port}, log_level='warning')",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    connection_terminated = False

    try:
        # Wait for server to start
        server_ready = False
        for _ in range(50):  # 50 * 0.2s = 10s max
            try:
                response = requests.get(health_url, timeout=1)
                if response.status_code == 200:
                    server_ready = True
                    break
            except requests.ConnectionError:
                pass
            time.sleep(0.2)

        assert server_ready, "Server failed to start"

        # Connect WebSocket client in a separate thread
        def connect_websocket():
            nonlocal connection_terminated
            try:
                ws = ws_client.create_connection(ws_url, timeout=5)
                # Set socket timeout for recv operations
                ws.settimeout(1.0)
                # Receive initial "connected" message
                ws.recv()
                # Block waiting for next message with timeout
                while True:
                    try:
                        ws.recv()  # This will raise when connection is terminated
                    except ws_client.WebSocketTimeoutException:
                        # Timeout - check if we should continue or exit
                        continue
            except (
                ws_client.WebSocketConnectionClosedException,
                ws_client.WebSocketException,
                ConnectionResetError,
                BrokenPipeError,
                OSError,
            ):
                connection_terminated = True
            except Exception:
                # Any other exception during connection handling indicates termination
                connection_terminated = True

        ws_thread = Thread(target=connect_websocket)
        ws_thread.start()

        # Give WebSocket time to connect
        time.sleep(0.5)

        # Send SIGINT to trigger graceful shutdown
        proc.send_signal(signal.SIGINT)

        # Wait for WebSocket thread to complete (should terminate due to connection close)
        ws_thread.join(timeout=10)

        # Verify connection was terminated
        assert connection_terminated, "WebSocket connection was not terminated during shutdown"

        # Wait for server to exit cleanly
        try:
            exit_code = proc.wait(timeout=5)
            assert exit_code == 0, f"Server exited with code {exit_code}"
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            pytest.fail("Server did not shut down gracefully within timeout")

    except Exception:
        # Clean up on any error
        proc.kill()
        proc.wait()
        raise
