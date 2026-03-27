from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_websocket_client_does_not_log_every_message() -> None:
    """The low-level websocket client should not log every inbound message."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/websocket-client.js").read_text()

    assert "console.log('WebSocket message received:'" not in source


def test_main_does_not_log_every_message_payload() -> None:
    """The main UI message handler should not dump every websocket message to console."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/main.js").read_text()

    assert "console.log('[WebSocket] Received message:'" not in source


def test_index_loads_app_config_before_websocket_client() -> None:
    """The page should load runtime config before websocket code reads debug flags."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/index.html").read_text()

    assert '<script src="/app-config.js"></script>' in source
    assert 'webui-client-logger.js?v=' in source
    assert 'websocket-client.js?v=' in source
    # Verify load order: app-config before logger before websocket client
    assert source.index('/app-config.js') < source.index('webui-client-logger.js')
    assert source.index('webui-client-logger.js') < source.index('websocket-client.js')


def test_webui_client_logger_prefixes_console_methods() -> None:
    """The browser console should be wrapped with a stable webui-client prefix."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/webui-client-logger.js").read_text()

    assert "[webui-client]" in source
    assert "console[methodName] = (...args) =>" in source
    assert "window[MARKER] = true;" in source


def test_main_js_handles_connected_message() -> None:
    """main.js should explicitly handle 'connected' WebSocket message."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/main.js").read_text()

    # Should have explicit case for 'connected' message
    assert "case 'connected':" in source


def test_main_js_handles_daemon_status_message() -> None:
    """main.js should explicitly handle 'daemon.status' WebSocket message."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/main.js").read_text()

    # Should have explicit case for 'daemon.status' message
    assert "case 'daemon.status':" in source


def test_connection_status_uses_daemon_status_message() -> None:
    """Connection status tooltip should use daemon.status message, not /health fetch."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/main.js").read_text()

    # Should apply daemon status payload from WebSocket message
    assert "applyDaemonStatusPayload" in source

    # daemon.status handler should call applyDaemonStatusPayload
    # (This ensures the popover gets data from WebSocket, not HTTP)
    daemon_status_section = source.split("case 'daemon.status':")[1].split("case '")[0]
    assert "applyDaemonStatusPayload" in daemon_status_section or "msg.payload" in daemon_status_section


def test_no_health_fetch_at_runtime() -> None:
    """Web UI should not fetch /health at runtime for live status."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/main.js").read_text()

    # The hydrateConnectionStatusFromHealth function should not be invoked at startup
    # (Function may exist for ops/debug but call was removed in Milestone 2)
    # Check that the call pattern (void hydrate... or hydrate...()) is not present
    # outside of comments or the function definition itself
    lines = source.split("\n")
    for line in lines:
        stripped = line.strip()
        # Skip comments and function definition
        if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("async function"):
            continue
        # Assert no invocation of hydrateConnectionStatusFromHealth
        assert "hydrateConnectionStatusFromHealth()" not in stripped, f"Found call in: {line}"
