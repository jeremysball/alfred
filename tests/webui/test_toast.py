"""Tests for toast notification system"""

import os


def test_toast_container_file_exists():
    """Verify toast-container.js component exists"""
    component_path = "src/alfred/interfaces/webui/static/js/components/toast-container.js"
    assert os.path.exists(component_path), f"Toast container not found at {component_path}"


def test_toast_container_registered():
    """Verify toast-container custom element is registered"""
    component_path = "src/alfred/interfaces/webui/static/js/components/toast-container.js"

    with open(component_path) as f:
        content = f.read()

    assert "customElements.define('toast-container'" in content, "Toast container not registered"


def test_toast_levels_supported():
    """Verify toast supports info, success, warning, error levels"""
    component_path = "src/alfred/interfaces/webui/static/js/components/toast-container.js"

    with open(component_path) as f:
        content = f.read()

    levels = ["info", "success", "warning", "error"]
    for level in levels:
        assert level in content, f"Toast level '{level}' not supported"


def test_toast_methods_exist():
    """Verify toast has show and dismiss methods"""
    component_path = "src/alfred/interfaces/webui/static/js/components/toast-container.js"

    with open(component_path) as f:
        content = f.read()

    assert "show" in content, "show() method not found"
    assert "dismiss" in content or "remove" in content, "dismiss/remove method not found"


def test_toast_auto_dismiss():
    """Verify toast auto-dismisses after timeout"""
    component_path = "src/alfred/interfaces/webui/static/js/components/toast-container.js"

    with open(component_path) as f:
        content = f.read()

    assert "setTimeout" in content or "setInterval" in content, "Auto-dismiss timeout not found"


def test_toast_imported_in_html():
    """Verify toast-container is imported in index.html"""
    html_path = "src/alfred/interfaces/webui/static/index.html"

    with open(html_path) as f:
        content = f.read()

    assert "toast-container.js" in content, "toast-container.js not imported"
    assert "<toast-container" in content, "<toast-container> element not found"


def test_main_js_handles_toast():
    """Verify main.js handles toast messages"""
    main_path = "src/alfred/interfaces/webui/static/js/main.js"

    with open(main_path) as f:
        content = f.read()

    assert "case 'toast':" in content, "toast message handler not found"
    assert "showToast" in content, "showToast function not found"
