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
    assert 'class="stop-button"' in content
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
