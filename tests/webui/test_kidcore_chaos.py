from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
THEME_CSS = PROJECT_ROOT / "src/alfred/interfaces/webui/static/css/themes/kidcore-playground.css"
INDEX_HTML = PROJECT_ROOT / "src/alfred/interfaces/webui/static/index.html"


def test_index_includes_kidcore_decorative_hooks() -> None:
    source = INDEX_HTML.read_text()

    assert 'class="kidcore-banner"' in source
    assert 'kidcore-banner-marquee' in source
    assert 'kidcore-banner-badge' in source
    assert 'aria-hidden="true"' in source


def test_kidcore_theme_defines_chaos_animations() -> None:
    source = THEME_CSS.read_text()

    assert '[data-theme="kidcore-playground"] .kidcore-banner' in source
    assert '[data-theme="kidcore-playground"] .kidcore-banner-marquee span' in source
    assert '[data-theme="kidcore-playground"] .kidcore-badge' in source
    assert '@keyframes kidcore-marquee-scroll' in source
    assert '@keyframes kidcore-badge-float' in source
    assert '@keyframes kidcore-badge-wiggle' in source


def test_kidcore_theme_styles_secondary_components() -> None:
    source = THEME_CSS.read_text()

    for selector in [
        '[data-theme="kidcore-playground"] .status-bar',
        '[data-theme="kidcore-playground"] .toast',
        '[data-theme="kidcore-playground"] .session-card',
        '[data-theme="kidcore-playground"] .tool-call',
        '[data-theme="kidcore-playground"] .tool-header',
    ]:
        assert selector in source


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

    assert 'border: 4px solid #140022' in source
    assert 'background: #fff5fd' in source
    assert 'background: linear-gradient(135deg, #ff4fd8 0%, #7c4dff 100%)' in source
