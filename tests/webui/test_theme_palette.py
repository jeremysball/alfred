"""Tests for theme palette fuzzy finder."""

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
async def test_theme_palette_opens_with_nested_leader_path(websocket_server, page_helper):
    """Test Ctrl+S -> T -> T opens theme palette."""
    page = page_helper

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    await open_theme_palette_via_leader(page)

    # Theme palette should be visible
    theme_palette = page.locator(".theme-palette-overlay")
    await expect(theme_palette).to_be_visible()

    # Should have input and results
    await expect(page.locator(".theme-palette-input")).to_be_visible()
    await expect(page.locator(".theme-palette-results")).to_be_visible()


@pytest.mark.asyncio
async def test_theme_palette_fuzzy_search(websocket_server, page_helper):
    """Test theme palette fuzzy search filters themes."""
    page = page_helper

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    await open_theme_palette_via_leader(page)

    # Type "dark" to filter
    await page.keyboard.type("dark")

    # Should show filtered results
    results = page.locator(".theme-palette-item")
    count = await results.count()
    assert count > 0
    assert count < 12  # Less than total themes


@pytest.mark.asyncio
async def test_theme_palette_escape_closes(websocket_server, page_helper):
    """Test Escape closes theme palette."""
    page = page_helper

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    await open_theme_palette_via_leader(page)

    theme_palette = page.locator(".theme-palette-overlay")
    await expect(theme_palette).to_be_visible()

    await page.keyboard.press("Escape")
    await expect(theme_palette).not_to_be_visible()


@pytest.mark.asyncio
async def test_theme_palette_selects_theme(websocket_server, page_helper):
    """Test selecting theme from palette changes theme."""
    page = page_helper

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    await open_theme_palette_via_leader(page)

    theme_palette = page.locator(".theme-palette-overlay")
    await expect(theme_palette).to_be_visible()

    # Type "space jam" to find Space Jam Neocities
    await page.locator(".theme-palette-input").fill("space jam")

    # Press Enter to select
    await page.keyboard.press("Enter")

    # Verify theme changed
    await page.wait_for_timeout(100)
    theme = await page.evaluate("document.documentElement.getAttribute('data-theme')")
    assert theme == "spacejam-neocities"


@pytest.mark.asyncio
async def test_which_key_uses_theme_surface_tokens_for_background_and_border(websocket_server, page_helper):
    """Test theme switching updates WhichKey surface tokens."""
    page = page_helper

    await page.wait_for_function(
        "() => window.__alfredWebUI?.getComposerState?.() !== undefined",
        timeout=5000,
    )

    async def read_which_key_surface():
        return await page.locator(".which-key").evaluate(
            """
            (el) => {
              const style = getComputedStyle(el);
              return {
                background: style.backgroundColor,
                border: style.borderTopColor,
                shadow: style.boxShadow,
              };
            }
            """,
        )

    await page.evaluate(
        "(theme) => document.documentElement.setAttribute('data-theme', theme)",
        "modern-dark",
    )
    await page.focus("#message-input")
    await page.keyboard.press("Control+s")

    which_key = page.locator(".which-key")
    await expect(which_key).to_be_visible()

    modern_dark = await read_which_key_surface()

    await page.evaluate(
        "(theme) => document.documentElement.setAttribute('data-theme', theme)",
        "kidcore-playground",
    )
    await page.wait_for_timeout(50)
    kidcore = await read_which_key_surface()

    assert modern_dark["background"] != kidcore["background"]
    assert modern_dark["border"] != kidcore["border"]
    assert modern_dark["shadow"] != kidcore["shadow"]
