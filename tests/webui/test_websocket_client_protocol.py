from __future__ import annotations

import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _websocket_client_url(protocol: str, host: str = "example.com") -> str:
    script = f"""
global.EventTarget = global.EventTarget || class {{}};
global.window = {{
  __ALFRED_WEBUI_CONFIG__: {{}},
  location: {{ protocol: {protocol!r}, host: {host!r} }},
}};
const {{ AlfredWebSocketClient }} = require('./src/alfred/interfaces/webui/static/js/websocket-client.js');
process.stdout.write(new AlfredWebSocketClient().url);
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def test_websocket_client_uses_wss_on_https():
    assert _websocket_client_url("https:").strip() == "wss://example.com/ws"


def test_websocket_client_uses_ws_on_http():
    assert _websocket_client_url("http:").strip() == "ws://example.com/ws"


def test_connect_guards_against_open_state():
    """connect() should be idempotent when WebSocket is already OPEN."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/websocket-client.js").read_text()

    # Should have guard for OPEN state at start of connect()
    assert "readyState === WebSocket.OPEN" in source or "this.ws?.readyState === WebSocket.OPEN" in source


def test_connect_guards_against_connecting_state():
    """connect() should be idempotent when WebSocket is CONNECTING."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/websocket-client.js").read_text()

    # Should have guard for CONNECTING state
    assert "WebSocket.CONNECTING" in source


def test_connect_guards_against_closing_state():
    """connect() should be idempotent when WebSocket is CLOSING."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/websocket-client.js").read_text()

    # Should have guard for CLOSING state
    assert "WebSocket.CLOSING" in source


def test_lifecycle_listeners_tracked_for_cleanup():
    """freeze, resume, pagehide, pageshow listeners should be tracked to prevent duplicates."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/websocket-client.js").read_text()

    # Should track freeze handler
    assert "_freezeHandler" in source or "freezeHandler" in source
    # Should track resume handler
    assert "_resumeHandler" in source or "resumeHandler" in source
    # Should track pagehide handler
    assert "_pagehideHandler" in source or "pagehideHandler" in source
    # Should track pageshow handler
    assert "_pageshowHandler" in source or "pageshowHandler" in source


def test_queue_flushes_on_connect():
    """Message queue should flush when connection opens."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/websocket-client.js").read_text()

    # _flushMessageQueue should be called in onopen handler
    assert "_flushMessageQueue()" in source


def test_message_queue_exists():
    """WebSocket client should have a message queue for offline buffering."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/websocket-client.js").read_text()

    # Should have messageQueue property initialized
    assert "this.messageQueue = []" in source or "messageQueue" in source


def test_websocket_client_reads_debug_config():
    """Verify WEBSOCKET_DEBUG_ENABLED is set from window.__ALFRED_WEBUI_CONFIG__."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/websocket-client.js").read_text()

    # Should read debug from window config
    assert "window.__ALFRED_WEBUI_CONFIG__" in source, "should read from window.__ALFRED_WEBUI_CONFIG__"
    # Should have WEBSOCKET_DEBUG_ENABLED constant
    assert "WEBSOCKET_DEBUG_ENABLED" in source, "should define WEBSOCKET_DEBUG_ENABLED"
