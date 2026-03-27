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
