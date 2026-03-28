"""Tests for theme persistence to localStorage."""

import pytest
from playwright.async_api import expect


async def open_theme_palette_via_leader(page) -> None:
    """Open the theme palette through the nested leader path."""
    await page.focus("#message-input")
    await page.keyboard.press("Control+s")

    which_key = page.locator(".which-key")
    await expect(which_key).to_be_visible()

    await page.keyboard.press("T")
    await page.keyboard.press("T")
    await expect(page.locator(".theme-palette-input")).to_be_focused()


@pytest.mark.asyncio
async def test_theme_restored_from_localstorage(websocket_server, page_helper):
    """Test theme is restored from localStorage on page reload."""
    page = page_helper

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    # Set theme to kidcore-playground via localStorage
    await page.evaluate("localStorage.setItem('theme', 'kidcore-playground')")

    # Reload the page
    await page.reload()

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    # Verify theme is restored
    theme = await page.evaluate("document.documentElement.getAttribute('data-theme')")
    assert theme == "kidcore-playground"


@pytest.mark.asyncio
async def test_theme_leader_key_changes_theme(websocket_server, page_helper):
    """Test Ctrl+S -> T -> T opens theme palette, fuzzy find Kidcore, and persists."""
    page = page_helper

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    # Clear any existing theme
    await page.evaluate("localStorage.removeItem('theme')")

    # Open the nested theme palette leader path
    await open_theme_palette_via_leader(page)

    # Theme palette should be visible
    theme_palette = page.locator(".theme-palette-overlay")
    await expect(theme_palette).to_be_visible()

    # Type "kid" to fuzzy search for Kidcore
    await page.keyboard.type("kid")

    # Select first result (Kidcore Playground)
    await page.keyboard.press("Enter")

    # Verify theme changed
    await page.wait_for_timeout(100)
    theme = await page.evaluate("document.documentElement.getAttribute('data-theme')")
    assert theme == "kidcore-playground"

    # Verify persisted to localStorage
    saved_theme = await page.evaluate("localStorage.getItem('theme')")
    assert saved_theme == "kidcore-playground"


def test_theme_files_define_surface_panel_tokens_where_needed() -> None:
    """Theme CSS should define the leader overlay surface tokens where used."""
    from pathlib import Path

    css_root = Path("src/alfred/interfaces/webui/static/css")
    assert "--surface-panel-bg" in (css_root / "themes.css").read_text()
    assert "--surface-panel-border" in (css_root / "themes.css").read_text()

    theme_files = [
        "kidcore-playground.css",
        "spacejam-neocities.css",
        "modern-dark.css",
        "elegant-modern-yellow.css",
    ]

    for filename in theme_files:
        content = (css_root / "themes" / filename).read_text()
        assert "--surface-panel-bg" in content, filename
        assert "--surface-panel-border" in content, filename
        assert "--surface-panel-header-bg" in content, filename
        assert "--surface-panel-shadow" in content, filename


@pytest.mark.asyncio
async def test_theme_persists_across_reload(websocket_server, page_helper):
    """Test theme set via leader key persists after page reload."""
    page = page_helper

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    # Set theme via localStorage directly
    await page.evaluate("localStorage.setItem('theme', 'spacejam-neocities')")

    # Reload
    await page.reload()

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    # Verify theme still set
    theme = await page.evaluate("document.documentElement.getAttribute('data-theme')")
    assert theme == "spacejam-neocities"
