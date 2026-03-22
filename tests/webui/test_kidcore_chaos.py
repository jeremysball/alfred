from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
THEME_CSS = PROJECT_ROOT / "src/alfred/interfaces/webui/static/css/themes/kidcore-playground.css"
HOMEBOARD_CSS = PROJECT_ROOT / "src/alfred/interfaces/webui/static/css/themes/kidcore-homeboard.css"
INDEX_HTML = PROJECT_ROOT / "src/alfred/interfaces/webui/static/index.html"


def test_index_includes_kidcore_homeboard_and_controls() -> None:
    source = INDEX_HTML.read_text()

    assert "kidcore-banner" not in source
    assert "kidcore-homeboard" in source
    assert "kidcore-guestbook-panel" in source
    assert "kidcore-webring-panel" in source
    assert "kidcore-links-panel" in source
    assert "kidcore-music-play" in source
    assert "kidcore-music-mute" in source
    assert "kidcore-sfx-toggle" in source
    assert "/static/js/kidcore-homeboard.js?v=3" in source


def test_kidcore_homeboard_css_styles_functional_panels() -> None:
    source = HOMEBOARD_CSS.read_text()

    for selector in [
        '[data-theme="kidcore-playground"] .kidcore-homeboard',
        '[data-theme="kidcore-playground"] .kidcore-homeboard-tab',
        '[data-theme="kidcore-playground"] .kidcore-homeboard-panel',
        '[data-theme="kidcore-playground"] .kidcore-homeboard-panel.active',
        '[data-theme="kidcore-playground"] .kidcore-guestbook-entry',
        '[data-theme="kidcore-playground"] .kidcore-webring-card',
        '[data-theme="kidcore-playground"] .kidcore-link-card',
        '[data-theme="kidcore-playground"] .kidcore-sfx-toggle',
    ]:
        assert selector in source

    assert '[data-theme="kidcore-playground"] .kidcore-homeboard[hidden]' in source
    assert '[data-theme="kidcore-playground"] .kidcore-link-button.active' in source
    assert '[data-theme="kidcore-playground"] .kidcore-guestbook-submit' in source


def test_kidcore_theme_keeps_message_and_composer_surfaces_readable() -> None:
    source = THEME_CSS.read_text()

    for selector in [
        '[data-theme="kidcore-playground"] .message.user .message-bubble',
        '[data-theme="kidcore-playground"] .message.assistant .message-bubble',
        '[data-theme="kidcore-playground"] .message.system .message-bubble',
        '[data-theme="kidcore-playground"] .message-input',
        '[data-theme="kidcore-playground"] .send-button',
    ]:
        assert selector in source

    assert "background: linear-gradient(135deg, #fff3cf 0%, #ffd0ea 58%, #ffb2d6 100%)" in source
    assert "background: linear-gradient(135deg, #f8f2ff 0%, #e7f5ff 100%)" in source
    assert "border-color: #ff70c8" in source
    assert "border-color: #8a5cf6" in source
    assert "background: #fff5fd" in source
