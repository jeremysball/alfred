"""Tests for static file serving."""

from pathlib import Path


def test_static_directory_exists():
    """Verify static files directory is created."""
    static_dir = Path("src/alfred/interfaces/webui/static")
    assert static_dir.exists(), f"Static directory not found: {static_dir}"
    assert static_dir.is_dir(), f"Static path is not a directory: {static_dir}"


def test_static_css_directory_exists():
    """Verify CSS subdirectory exists."""
    css_dir = Path("src/alfred/interfaces/webui/static/css")
    assert css_dir.exists(), f"CSS directory not found: {css_dir}"
    assert css_dir.is_dir(), f"CSS path is not a directory: {css_dir}"


def test_static_js_directory_exists():
    """Verify JS subdirectory exists."""
    js_dir = Path("src/alfred/interfaces/webui/static/js")
    assert js_dir.exists(), f"JS directory not found: {js_dir}"
    assert js_dir.is_dir(), f"JS path is not a directory: {js_dir}"
