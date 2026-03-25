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
