"""Regression tests for the Python module entrypoint."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_python_module_entrypoint_reaches_webui_command() -> None:
    """`python -m alfred webui` should invoke the CLI app."""
    result = subprocess.run(
        [sys.executable, "-m", "alfred", "webui", "--help"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    output = result.stdout + result.stderr
    assert "Launch web interface" in output
    assert "Port to run the Web UI server on" in output
