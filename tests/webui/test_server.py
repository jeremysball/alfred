"""Tests for Web UI server."""

import signal
import subprocess
import time

import pytest
import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient

from alfred.interfaces.webui import WebUIServer, create_app


def test_webui_module_exists():
    """Verify webui module is importable and WebUIServer can be instantiated."""
    server = WebUIServer(port=8080)
    assert server is not None
    assert server.port == 8080


def test_webui_server_default_port():
    """Verify WebUIServer uses default port 8080."""
    server = WebUIServer()
    assert server.port == 8080


def test_webui_server_custom_port():
    """Verify WebUIServer accepts custom port."""
    server = WebUIServer(port=3000)
    assert server.port == 3000


def test_fastapi_app_factory():
    """Verify create_app returns a valid FastAPI application."""
    app = create_app()
    assert app is not None
    assert isinstance(app, FastAPI)
    assert app.title == "Alfred Web UI"


def test_health_endpoint_returns_ok():
    """Verify /health endpoint returns 200 with status."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert data["version"] == "0.1.0"


def test_server_shuts_down_on_sigint():
    """Verify server shuts down cleanly on SIGINT signal.

    Starts uvicorn in a subprocess, verifies it's running,
    sends SIGINT, and confirms clean exit.
    """
    # Use a unique port to avoid conflicts
    port = 19999

    # Start server in subprocess using uv run
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

    try:
        # Wait for server to start (max 10 seconds)
        health_url = f"http://127.0.0.1:{port}/health"
        server_ready = False
        for _ in range(50):  # 50 * 0.2s = 10s
            try:
                response = requests.get(health_url, timeout=1)
                if response.status_code == 200:
                    server_ready = True
                    break
            except requests.ConnectionError:
                pass
            time.sleep(0.2)

        assert server_ready, "Server failed to start"

        # Verify server is responding
        response = requests.get(health_url, timeout=1)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        # Send SIGINT for graceful shutdown
        proc.send_signal(signal.SIGINT)

        # Wait for clean shutdown (max 5 seconds)
        try:
            exit_code = proc.wait(timeout=5)
            # `uv run` can surface SIGINT as a negative return code even when the
            # server tears down cleanly, so accept either the raw signal result or 0.
            assert exit_code in {0, -signal.SIGINT}, f"Server exited with code {exit_code}"
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            pytest.fail("Server did not shut down gracefully within timeout")

    except Exception:
        # Clean up on any error
        proc.kill()
        proc.wait()
        raise
