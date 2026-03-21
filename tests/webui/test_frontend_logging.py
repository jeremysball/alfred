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
    assert source.index('<script src="/app-config.js"></script>') < source.index(
        '<script src="/static/js/websocket-client.js?v=3"></script>'
    )
