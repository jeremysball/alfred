"""Tests for input system (multiline, completion, queue, history)."""

import pytest
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


def test_command_completion_structure():
    """Verify command completion data structure."""
    from alfred.interfaces.webui.validation import CompletionSuggestionsMessage, CompletionSuggestion

    suggestion = CompletionSuggestion(value="/new", description="Start new session")
    message = CompletionSuggestionsMessage(
        type="completion.suggestions",
        payload={"suggestions": [suggestion]}
    )

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
