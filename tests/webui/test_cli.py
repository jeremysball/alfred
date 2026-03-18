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
