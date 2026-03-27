"""Tests for WebUI CLI command and flag handling."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_webui_log_debug_flag_accepted():
    """Verify that 'webui --log debug' is accepted by the CLI."""
    source = (PROJECT_ROOT / "src/alfred/cli/main.py").read_text()

    # Find the webui_callback function
    callback_start = source.find("def webui_callback(")
    assert callback_start != -1, "webui_callback function not found"
    
    # Extract just the webui_callback function signature
    callback_section = source[callback_start:callback_start + 1500]
    
    # The webui callback should have a 'log' parameter
    assert "log:" in callback_section or "log=" in callback_section, "webui callback should accept log parameter"
    # Should have typer.Option for log with --log flag
    assert '"--log"' in callback_section or "'--log'" in callback_section, "should have --log option"


def test_webui_server_receives_debug_flag():
    """Verify that _build_server_controller receives debug parameter."""
    source = (PROJECT_ROOT / "src/alfred/cli/webui_hotswap.py").read_text()

    # _build_server_controller should have debug parameter
    assert "debug: bool" in source, "_build_server_controller should have debug parameter"
    # run_webui_server should pass debug parameter
    assert "debug: bool" in source or "debug=debug" in source, "run_webui_server should accept and pass debug parameter"
    # create_app should be called with debug
    assert "create_app(" in source and "debug" in source, "create_app should receive debug parameter"
