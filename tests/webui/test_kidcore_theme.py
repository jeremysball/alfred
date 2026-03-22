from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_theme_selector_lists_kidcore_playground_theme() -> None:
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/components/theme-selector.js").read_text()

    assert "kidcore-playground" in source
    assert "Kidcore Playground" in source


def test_index_loads_kidcore_playground_stylesheet() -> None:
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/index.html").read_text()

    assert "/static/css/themes/kidcore-playground.css?v=5" in source


def test_kidcore_theme_file_defines_core_surface_tokens() -> None:
    path = PROJECT_ROOT / "src/alfred/interfaces/webui/static/css/themes/kidcore-playground.css"
    assert path.exists(), "kidcore-playground.css is missing"

    source = path.read_text()

    assert '[data-theme="kidcore-playground"]' in source
    for token in [
        "--bg-primary",
        "--bg-secondary",
        "--text-primary",
        "--accent-primary",
        "--composer-bg",
        "--status-bg",
        "--send-button-bg",
    ]:
        assert token in source, f"Missing token: {token}"


def test_theme_selector_keeps_generic_activation_and_existing_themes() -> None:
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/components/theme-selector.js").read_text()

    assert "document.documentElement.setAttribute('data-theme', themeId)" in source
    assert "localStorage.setItem('alfred-theme', themeId)" in source
    for theme_id in [
        "dark-academia",
        "swiss-international",
        "swiss-international-dark",
        "neumorphism",
        "neumorphism-dark",
        "minimal",
        "element-modern",
        "kidcore-playground",
        "spacejam-neocities",
    ]:
        assert theme_id in source
