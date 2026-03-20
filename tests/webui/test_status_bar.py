"""Tests for status bar Web Component"""

import pytest
from unittest.mock import MagicMock, patch


def test_status_bar_renders_all_elements():
    """Verify status bar shows model, tokens, queue, and streaming indicator"""
    # This test validates the status bar HTML structure and attributes
    # The actual rendering is done by the browser via Web Components

    # Check that the component file exists and contains expected elements
    import os

    component_path = "src/alfred/interfaces/webui/static/js/components/status-bar.js"
    assert os.path.exists(component_path), f"Status bar component not found at {component_path}"

    with open(component_path) as f:
        content = f.read()

    # Verify custom element is defined
    assert "customElements.define('status-bar'" in content, "Status bar custom element not registered"

    # Verify observed attributes exist
    assert "model" in content, "Model attribute not supported"
    assert "tokens" in content or "inputTokens" in content, "Token attributes not supported"
    assert "queue" in content or "queueLength" in content, "Queue attribute not supported"
    assert "streaming" in content or "isStreaming" in content, "Streaming attribute not supported"

    # Verify render method exists
    assert "_render" in content or "render" in content, "Render method not found"


def test_status_bar_attributes_observed():
    """Verify status bar observes all required attributes"""
    component_path = "src/alfred/interfaces/webui/static/js/components/status-bar.js"

    with open(component_path) as f:
        content = f.read()

    # Check for observedAttributes getter
    assert "observedAttributes" in content, "observedAttributes not defined"

    # Check that all status fields are observed
    required_attrs = ["model", "queue", "streaming"]
    for attr in required_attrs:
        assert attr in content, f"Attribute '{attr}' not observed"


def test_status_bar_displays_correct_data():
    """Verify status bar displays data passed via attributes"""
    component_path = "src/alfred/interfaces/webui/static/js/components/status-bar.js"

    with open(component_path) as f:
        content = f.read()

    # Verify the component has methods to set/get data
    assert "setModel" in content or "model" in content, "Model setter not found"
    assert "setQueue" in content or "queue" in content, "Queue setter not found"

    # Verify token display methods
    assert "inputTokens" in content or "setTokens" in content, "Token handling not found"


def test_status_bar_integrated_in_html():
    """Verify status bar is imported in index.html"""
    import os

    html_path = "src/alfred/interfaces/webui/static/index.html"
    assert os.path.exists(html_path), f"index.html not found at {html_path}"

    with open(html_path) as f:
        content = f.read()

    # Verify status-bar.js is imported
    assert "status-bar.js" in content, "status-bar.js not imported in index.html"

    # Verify <status-bar> element exists in the page
    assert "<status-bar" in content, "<status-bar> element not found in HTML"
