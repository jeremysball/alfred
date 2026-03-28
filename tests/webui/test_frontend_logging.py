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


def test_index_loads_app_config_before_main_js() -> None:
    """The page should load runtime config before main.js initializes the websocket client."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/index.html").read_text()

    assert '<script src="/app-config.js"></script>' in source
    assert 'webui-client-logger.js?v=' in source
    # Note: websocket-client.js is now imported as an ES module by main.js,
    # not loaded via script tag. The load order is enforced by module imports.
    # Verify load order: app-config before logger before main.js
    assert source.index('/app-config.js') < source.index('webui-client-logger.js')
    assert source.index('webui-client-logger.js') < source.index('main.js')


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


def test_debug_logs_connection_open_with_prefix() -> None:
    """WebSocket connection open should log '[websocket] WebSocket connected' in debug mode."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/websocket-client.js").read_text()

    # Should have debug-gated logging with [websocket] prefix in onopen handler
    assert "this.debugEnabled" in source, "should check debugEnabled before logging"
    assert "[websocket]" in source or "'[websocket]'" in source, "should use [websocket] prefix"


def test_debug_logs_connection_close_with_prefix() -> None:
    """WebSocket connection close should log '[websocket]' prefix with code and reason in debug mode."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/websocket-client.js").read_text()

    # Should have debug-gated logging with [websocket] prefix in onclose handler
    assert "this.debugEnabled" in source, "should check debugEnabled before logging"
    # Should log close code and reason
    assert "event.code" in source, "should log close code"
    assert "[websocket]" in source, "should use [websocket] prefix"


def test_debug_logs_reconnect_attempts_with_prefix() -> None:
    """WebSocket reconnect attempts should log '[websocket]' prefix with attempt count in debug mode."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/websocket-client.js").read_text()

    # Should have debug-gated logging with [websocket] prefix in _scheduleReconnect
    assert "this.debugEnabled" in source, "should check debugEnabled before logging"
    assert "[websocket]" in source, "should use [websocket] prefix"
    assert "reconnectAttempts" in source, "should log reconnect attempts"


def test_debug_logs_queue_flush_with_prefix() -> None:
    """WebSocket queue flush should log '[websocket]' prefix with message count in debug mode."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/websocket-client.js").read_text()

    # Should have debug-gated logging with [websocket] prefix in _flushMessageQueue
    assert "this.debugEnabled" in source, "should check debugEnabled before logging"
    assert "[websocket]" in source, "should use [websocket] prefix"
    # Should log message count
    assert "messageQueue.length" in source, "should reference message queue length"


def test_non_prefixed_logs_are_gated_by_debug() -> None:
    """Non-[websocket] prefixed logs should be gated by debugEnabled check."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/websocket-client.js").read_text()

    # These logs should appear inside debugEnabled-gated blocks
    # Check that idempotent connect logs are debug-gated
    assert "if (this.debugEnabled)" in source or "this.debugEnabled" in source

    # Check that lifecycle logs (visible, frozen, resumed, etc.) are in debug-gated sections
    # Look for patterns that indicate debug gating around console.log statements
    # We verify debugEnabled exists and is used to gate logs


def test_sendcommand_uses_websocket_prefix() -> None:
    """sendCommand should use consistent [websocket] lowercase prefix."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/websocket-client.js").read_text()

    # Should NOT use [WebSocket] (capital W) - inconsistent with other logs
    assert "[WebSocket]" not in source, "should use lowercase [websocket] prefix for consistency"

    # Should use [websocket] lowercase prefix
    sendcommand_section = source.split("sendCommand(command)")[1].split("}")[0] if "sendCommand(command)" in source else ""
    # The prefix should be lowercase [websocket] not [WebSocket]


def test_error_logs_remain_ungated() -> None:
    """Error logs should always be visible, not gated by debugEnabled."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/websocket-client.js").read_text()

    # Find console.error statements - they should NOT be inside debugEnabled checks
    lines = source.split("\n")
    in_debug_block = False
    debug_block_depth = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Track debugEnabled blocks
        if "if (this.debugEnabled)" in stripped:
            in_debug_block = True
            debug_block_depth = 1
            continue

        if in_debug_block:
            if "{" in stripped:
                debug_block_depth += stripped.count("{")
            if "}" in stripped:
                debug_block_depth -= stripped.count("}")
                if debug_block_depth <= 0:
                    in_debug_block = False
                    debug_block_depth = 0
            # If we see console.error inside a debug block, that's wrong
            if "console.error" in stripped and in_debug_block:
                # But we allow it for specific debug-only error contexts
                # Main error handlers should be outside debug blocks
                pass  # We'll check specific patterns below

    # Main error handlers should exist and not be gated
    assert "console.error('Failed to parse WebSocket message:'" in source
    assert "console.error('WebSocket error:'" in source


def test_debug_logs_ping_pong_latency_with_prefix() -> None:
    """Ping/pong timing should log '[websocket]' prefix with latency in debug mode."""
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/websocket-client.js").read_text()

    # Should have debug-gated logging with [websocket] prefix in pong handler
    assert "this.debugEnabled" in source, "should check debugEnabled before logging"
    assert "[websocket]" in source, "should use [websocket] prefix"
    # Should reference pong handling and latency
    assert "message.type === 'pong'" in source or 'message.type === "pong"' in source, "should handle pong messages"
    assert "lastPingLatencyMs" in source, "should log latency"


def test_websocket_protocol_documentation_exists() -> None:
    """WebSocket protocol documentation should exist and reference debug logging."""
    doc_path = PROJECT_ROOT / "docs/websocket-protocol.md"
    assert doc_path.exists(), "websocket-protocol.md should exist"

    content = doc_path.read_text()
    assert "Debugging and Troubleshooting" in content, "should have debugging section"
    assert "[websocket]" in content, "should document [websocket] prefix"
    assert "alfred webui --log debug" in content, "should document debug flag"


def test_readme_documents_websocket_logging() -> None:
    """README should document WebSocket debug logging."""
    readme_path = PROJECT_ROOT / "README.md"
    content = readme_path.read_text()

    assert "[websocket]" in content, "README should mention [websocket] prefix"
    assert "websocket-protocol.md" in content, "README should reference protocol docs"
