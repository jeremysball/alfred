"""Tests for WebUI CLI command."""

import subprocess
import sys

import pytest


def test_webui_command_registered():
    """Verify `alfred webui --help` shows help message."""
    result = subprocess.run(
        [sys.executable, "-m", "alfred.cli.main", "webui", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "webui" in result.stdout.lower() or "Usage:" in result.stdout


def test_webui_command_accepts_port():
    """Verify `--port` flag is recognized."""
    result = subprocess.run(
        [sys.executable, "-m", "alfred.cli.main", "webui", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--port" in result.stdout


def test_webui_command_accepts_open():
    """Verify `--open` flag is recognized."""
    result = subprocess.run(
        [sys.executable, "-m", "alfred.cli.main", "webui", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--open" in result.stdout


def test_webui_server_starts_on_specified_port():
    """Verify server actually starts on specified port."""
    import time

    # Start server in background with a test port
    test_port = 9998
    process = subprocess.Popen(
        [sys.executable, "-m", "alfred.cli.main", "webui", "--port", str(test_port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to start
    time.sleep(2)

    try:
        # Test health endpoint
        result = subprocess.run(
            ["curl", "-s", f"http://localhost:{test_port}/health"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert '"status"' in result.stdout and '"ok"' in result.stdout
    finally:
        # Clean up
        process.terminate()
        process.wait(timeout=5)
