from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_readme_documents_surface_scoped_logging() -> None:
    """README should explain surface-scoped logging and grep-friendly file logs."""
    readme = (PROJECT_ROOT / "README.md").read_text()

    assert "The root `--log` flag and the Web UI `--log` flag are separate." in readme
    assert "alfred --log debug webui" in readme
    assert "alfred webui --log debug" in readme
    assert "alfred --log debug webui --log debug" in readme
    assert "[core]" in readme
    assert "[webui-server]" in readme
    assert "[webui-client]" in readme
    assert "surface=..." in readme
    assert "TTY" in readme
    assert "non-TTY" in readme
    assert "grep-friendly" in readme
