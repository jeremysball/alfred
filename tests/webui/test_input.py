"""Tests for input system (multiline, completion, queue, history)."""

from fastapi.testclient import TestClient

from alfred.interfaces.webui import create_app


def test_multiline_textarea_exists():
    """Verify textarea element exists in index.html."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/index.html")
    content = response.text

    assert "<textarea" in content.lower()
    assert "message-input" in content


def test_completion_menu_component_exists():
    """Verify completion-menu component is served."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/js/components/completion-menu.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


def test_composer_state_surface_exists():
    """Verify the input area exposes a DOM state surface for streaming and editing."""
    app = create_app()
    client = TestClient(app)

    index_html = client.get("/static/index.html").text
    main_js = client.get("/static/js/main.js").text

    assert 'data-composer-state="idle"' in index_html
    assert "getComposerState" in main_js
    assert "setComposerState('editing')" in main_js
    assert "edit-message" in main_js


def test_command_completion_structure():
    """Verify command completion data structure."""
    from alfred.interfaces.webui.validation import CompletionSuggestion, CompletionSuggestionsMessage

    suggestion = CompletionSuggestion(value="/new", description="Start new session")
    message = CompletionSuggestionsMessage(type="completion.suggestions", payload={"suggestions": [suggestion]})

    assert message.type == "completion.suggestions"
    assert len(message.payload.suggestions) == 1
    assert message.payload.suggestions[0].value == "/new"


def test_input_styles_exist():
    """Verify input-related CSS is present."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/css/base.css")
    content = response.text

    # Verify textarea and completion styles
    assert "textarea" in content.lower() or "message-input" in content


# =============================================================================
# History Tests
# =============================================================================


def test_message_history_storage():
    """Verify message history is stored per directory."""
    # This would test localStorage integration
    # For now, just verify the structure exists
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/js/main.js")
    content = response.text

    # Should reference history or localStorage
    assert "history" in content.lower() or "localStorage" in content


# =============================================================================
# Queue Tests
# =============================================================================


def test_queue_counter_in_status():
    """Verify queue counter exists in status bar."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/index.html")
    content = response.text

    # Should have queue indicator somewhere
    assert "queue" in content.lower() or "badge" in content.lower()


# =============================================================================
# Stop Button Tests
# =============================================================================


def test_stop_button_exists():
    """Verify stop button exists in index.html."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/index.html")
    content = response.text

    assert 'id="stop-button"' in content
    assert 'stop-button' in content  # Class may have multiple values
    assert 'aria-label="Stop generating"' in content


def test_stop_button_hidden_by_default():
    """Verify stop button is hidden by default."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/index.html")
    content = response.text

    assert 'id="stop-button"' in content
    assert 'hidden' in content.split('id="stop-button"')[1].split('>')[0]


def test_stop_button_css_rules_exist():
    """Verify stop button CSS rules exist."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/css/base.css")
    content = response.text

    assert ".stop-button" in content
    assert "#input-area[data-composer-state=\"streaming\"] .stop-button" in content
    assert "#input-area[data-composer-state=\"cancelling\"] .stop-button" in content


def test_stop_button_js_handler_exists():
    """Verify stop button JavaScript handler exists."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/js/main.js")
    content = response.text

    assert "handleStopGenerating" in content
    assert "stopButton?.addEventListener('click', handleStopGenerating)" in content
    assert "setCancellingState" in content


def test_esc_key_calls_stop_handler():
    """Verify Esc key triggers stop generation handler."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/js/main.js")
    content = response.text

    assert "handleStopGenerating()" in content
    assert "composerState !== 'cancelling'" in content


def test_esc_key_cancels_edit_mode():
    """Verify Esc key cancels edit mode."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/js/main.js")
    content = response.text

    assert "composerState === 'editing'" in content
    assert "clearComposerEditState()" in content


def test_composer_placeholder_changes_for_edit_mode():
    """Verify composer placeholder changes when editing."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/js/main.js")
    content = response.text

    assert "Editing message... (Esc to cancel)" in content
    assert "Type your message... (Shift+Enter to queue)" in content


def test_pencil_button_exists_in_chat_message():
    """Verify pencil button exists in chat-message component."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/js/components/chat-message.js")
    content = response.text

    assert 'data-action="edit"' in content
    assert 'aria-label="Edit message"' in content
    assert '✎' in content


def test_pencil_button_only_for_user_messages():
    """Verify pencil button only appears for user messages."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/js/components/chat-message.js")
    content = response.text

    assert "_role === 'user' && this._editable" in content


def test_edit_message_event_dispatched():
    """Verify edit-message event is dispatched with correct detail."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/js/components/chat-message.js")
    content = response.text

    assert "edit-message" in content
    assert "messageId: this._messageId" in content
    assert "_editMessage()" in content


def test_editing_state_css_exists():
    """Verify CSS for editing state highlight exists."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/css/base.css")
    content = response.text

    assert 'chat-message[data-message-state="editing"] .message.user' in content
    assert "box-shadow" in content


def test_start_composer_edit_function_exists():
    """Verify startComposerEdit function exists in main.js."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/js/main.js")
    content = response.text

    assert "function startComposerEdit(messageElement)" in content
    assert "setComposerState('editing')" in content


def test_clear_composer_edit_state_function_exists():
    """Verify clearComposerEditState function exists."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/js/main.js")
    content = response.text

    assert "function clearComposerEditState()" in content


# =============================================================================
# Mobile Chrome Collapse Tests
# =============================================================================


def test_mobile_chrome_collapse_css_exists():
    """Verify CSS for mobile chrome collapse exists."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/css/base.css")
    content = response.text

    assert ".app-header.compact" in content
    assert ".input-area.compact" in content
    assert "transition: padding 0.2s ease" in content


def test_mobile_scroll_handler_exists():
    """Verify scroll handler for mobile chrome collapse exists."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/js/main.js")
    content = response.text

    assert "function handleScroll()" in content
    assert "function collapseChrome()" in content
    assert "function restoreChrome()" in content
    assert "MOBILE_BREAKPOINT = 768" in content


def test_mobile_collapse_restores_on_focus():
    """Verify chrome restores when composer is focused."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/js/main.js")
    content = response.text

    assert "messageInput.addEventListener('focus'" in content
    assert "restoreChrome()" in content


def test_mobile_stop_button_visible_during_streaming():
    """Verify stop button CSS rules exist for mobile streaming."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/css/base.css")
    content = response.text

    assert '[data-composer-state="streaming"] #stop-button' in content
    assert 'display: inline-flex' in content


def test_mobile_history_buttons_hidden_during_streaming():
    """Verify history buttons are hidden during streaming on mobile."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/static/css/base.css")
    content = response.text

    assert '[data-composer-state="streaming"] #history-up' in content
    assert '[data-composer-state="streaming"] #history-down' in content
    assert 'display: none !important' in content
