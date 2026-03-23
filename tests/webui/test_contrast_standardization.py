from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_contrast_utility_exposes_theme_contrast_system() -> None:
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/utils/contrast.js").read_text()

    assert "export function applyThemeContrast" in source
    assert "export function getContrastTextFast" in source
    assert "export function getContrastPalette" in source
    assert "--contrast-text" in source
    assert "--contrast-muted" in source
    assert "--contrast-accent" in source


def test_theme_selector_uses_shared_contrast_utility() -> None:
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/components/theme-selector.js").read_text()

    assert "from '../utils/contrast.js'" in source or 'from "../utils/contrast.js"' in source
    assert "applyThemeContrast(" in source
    assert "getContrastPalette(" in source
    assert "getComputedStyle(document.documentElement)" not in source
    assert "0.299 * r" not in source


def test_base_css_standardizes_contrast_vars_and_composer_width() -> None:
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/css/base.css").read_text()

    assert "--composer-max-width" in source
    assert "max-width: var(--composer-max-width" in source
    assert "--contrast-text" in source
    assert "--contrast-muted" in source
    assert "--contrast-accent" in source
    assert "var(--contrast-text" in source


def test_index_loads_theme_selector_and_main_as_modules() -> None:
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/index.html").read_text()

    assert '<script type="module" src="/static/js/components/theme-selector.js?v=3"></script>' in source
    assert '<script type="module" src="/static/js/main.js?v=6"></script>' in source


def test_theme_css_does_not_hardcode_contrast_text_colors() -> None:
    theme_dir = PROJECT_ROOT / "src/alfred/interfaces/webui/static/css/themes"
    banned = [
        "--theme-name-text:",
        "--theme-description-text:",
        "--theme-check-color:",
        "--status-text:",
        "--status-label:",
        "--status-value:",
        "--tool-name:",
        "--tool-status-text:",
        "--tool-toggle:",
    ]

    for path in theme_dir.glob("*.css"):
        source = path.read_text()
        for needle in banned:
            assert needle not in source, f"{path.name} still hardcodes {needle}"


def test_modern_dark_uses_contrast_vars_for_badges_and_inputs() -> None:
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/css/themes/modern-dark.css").read_text()

    assert "var(--contrast-send-text" in source
    assert "var(--contrast-tool-text" in source
    assert "var(--contrast-tool-muted" in source
    assert "var(--contrast-status-success-text" in source
    assert "var(--contrast-status-error-text" in source
    assert "var(--contrast-status-running-text" in source
    assert "background: #79c0ff;" not in source
    assert "background: var(--md-accent-primary-hover);" in source
    assert "color: #fff" not in source
    assert "color: #000" not in source
