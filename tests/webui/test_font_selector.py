"""Tests for font selector functionality."""

import os


def test_font_family_classes_exist():
    """Verify font family CSS classes are properly defined."""
    css_path = "src/alfred/interfaces/webui/static/css/base.css"
    assert os.path.exists(css_path), f"CSS file not found: {css_path}"

    with open(css_path) as f:
        content = f.read()

    # Check that html/:root selectors exist
    assert "html.font-family-system" in content, "Missing html.font-family-system selector"
    assert ":root.font-family-system" in content, "Missing :root.font-family-system selector"
    assert "html.font-family-serif" in content, "Missing html.font-family-serif selector"
    assert "html.font-family-mono" in content, "Missing html.font-family-mono selector"
    assert "html.font-family-sans" in content, "Missing html.font-family-sans selector"


def test_font_family_overrides_body():
    """Verify font family classes override body font-family."""
    css_path = "src/alfred/interfaces/webui/static/css/base.css"

    with open(css_path) as f:
        content = f.read()

    # Check that body font-family is overridden with !important
    assert "html.font-family-system body" in content, "Missing body override for system font"
    assert "font-family: var(--font-family-override) !important" in content, "Missing !important on font-family"


def test_font_family_overrides_theme_variables():
    """Verify font family classes override theme-specific font variables."""
    css_path = "src/alfred/interfaces/webui/static/css/base.css"

    with open(css_path) as f:
        content = f.read()

    # Check that theme-specific font variables are overridden with !important
    # This is necessary because theme CSS files load after base.css
    assert "--da-font-primary: var(--font-family-override) !important" in content, "Missing dark academia font override with !important"
    assert "--swiss-font-primary: var(--font-family-override) !important" in content, "Missing swiss font override with !important"
    assert "--min-font-primary: var(--font-family-override) !important" in content, "Missing minimal font override with !important"
    assert "--font-primary: var(--font-family-override) !important" in content, "Missing generic font override with !important"
    assert "--md-font-primary: var(--font-family-override) !important" in content, "Missing modern dark font override with !important"


def test_font_size_classes_use_html_root():
    """Verify font size classes target html/:root element."""
    css_path = "src/alfred/interfaces/webui/static/css/base.css"

    with open(css_path) as f:
        content = f.read()

    # Check that font size classes use html/:root selectors
    assert "html.font-size-small" in content, "Missing html.font-size-small selector"
    assert ":root.font-size-small" in content, "Missing :root.font-size-small selector"
    assert "html.font-size-large" in content, "Missing html.font-size-large selector"


def test_javascript_applies_font_family_to_root():
    """Verify JavaScript applies font family class to document.documentElement."""
    js_path = "src/alfred/interfaces/webui/static/js/components/theme-selector.js"
    assert os.path.exists(js_path), f"JS file not found: {js_path}"

    with open(js_path) as f:
        content = f.read()

    # Check that _applyFontFamily adds class to document.documentElement
    assert "document.documentElement" in content, "Missing document.documentElement reference"
    assert 'root.classList.add(`font-family-${fontId}`)' in content, "Missing font-family class addition"
    assert 'font-family-system' in content, "Missing font-family-system class name"


def test_javascript_persists_font_selection():
    """Verify JavaScript persists font selection to localStorage."""
    js_path = "src/alfred/interfaces/webui/static/js/components/theme-selector.js"

    with open(js_path) as f:
        content = f.read()

    # Check that localStorage is used
    assert "localStorage.setItem('alfred-font-family'" in content, "Missing localStorage set for font-family"
    assert "localStorage.getItem('alfred-font-family'" in content, "Missing localStorage get for font-family"
    assert "localStorage.setItem('alfred-font-size'" in content, "Missing localStorage set for font-size"
