import asyncio
import socket
import time
import urllib.request
from threading import Thread

import pytest
import uvicorn
from playwright.async_api import async_playwright

from alfred.interfaces.webui.server import create_app

THEMES = ("swiss-international", "element-modern", "spacejam-neocities")


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def _wait_for_server(port: int, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/health"
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        await asyncio.sleep(0.25)
    raise RuntimeError(f"server did not start: {last_error}")


@pytest.mark.asyncio
async def test_settings_menu_text_has_usable_contrast_across_themes() -> None:
    port = _find_free_port()
    config = uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = Thread(target=server.run, daemon=True)
    thread.start()

    try:
        await _wait_for_server(port)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 900})

            for theme in THEMES:
                await page.add_init_script(f"localStorage.setItem('alfred-theme', '{theme}');")
                await page.goto(f"http://127.0.0.1:{port}/static/index.html", wait_until="networkidle")
                await page.click('button[aria-label="Settings"]')
                await page.wait_for_timeout(150)

                ratios = await page.evaluate(
                    r"""
                    () => {
                      const parse = (value) => {
                        const match = value.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
                        if (!match) return [0, 0, 0, 1];
                        return [Number(match[1]), Number(match[2]), Number(match[3]), match[4] ? Number(match[4]) : 1];
                      };

                      const luminance = ([r, g, b]) => {
                        const channel = (component) => {
                          const normalized = component / 255;
                          return normalized <= 0.03928
                            ? normalized / 12.92
                            : Math.pow((normalized + 0.055) / 1.055, 2.4);
                        };
                        return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
                      };

                      const contrast = (foreground, background) => {
                        const fg = parse(foreground);
                        const bg = parse(background);
                        const fgLum = luminance(fg);
                        const bgLum = luminance(bg);
                        const lighter = Math.max(fgLum, bgLum);
                        const darker = Math.min(fgLum, bgLum);
                        return (lighter + 0.05) / (darker + 0.05);
                      };

                      const sectionHeader = document.querySelector('.settings-section-header');
                      const activeCheck = document.querySelector('.theme-check');
                      const activeOption = document.querySelector('.theme-option.active');
                      const themeDescription = document.querySelector('.theme-description');
                      const themeOption = themeDescription?.closest('.theme-option');

                      return {
                        sectionHeader: sectionHeader
                          ? contrast(getComputedStyle(sectionHeader).color, getComputedStyle(sectionHeader).backgroundColor)
                          : 0,
                        activeCheck: activeCheck && activeOption
                          ? contrast(getComputedStyle(activeCheck).color, getComputedStyle(activeOption).backgroundColor)
                          : 0,
                        themeDescription: themeDescription && themeOption
                          ? contrast(getComputedStyle(themeDescription).color, getComputedStyle(themeOption).backgroundColor)
                          : 0,
                      };
                    }
                    """
                )

                assert ratios["sectionHeader"] >= 4.5, theme
                assert ratios["themeDescription"] >= 4.5, theme
                assert ratios["activeCheck"] >= 4.5, theme

            await browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)


@pytest.mark.asyncio
async def test_light_theme_rows_are_readable_on_dark_theme() -> None:
    port = _find_free_port()
    config = uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = Thread(target=server.run, daemon=True)
    thread.start()

    try:
        await _wait_for_server(port)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            await page.add_init_script("localStorage.setItem('alfred-theme', 'modern-dark');")
            await page.goto(f"http://127.0.0.1:{port}/static/index.html", wait_until="networkidle")
            await page.click('button[aria-label="Settings"]')
            await page.wait_for_timeout(150)

            rows = await page.evaluate(
                r"""
                () => {
                  const parse = (value) => {
                    const match = value.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
                    if (!match) return [0, 0, 0, 1];
                    return [Number(match[1]), Number(match[2]), Number(match[3]), match[4] ? Number(match[4]) : 1];
                  };

                  const luminance = ([r, g, b]) => {
                    const channel = (component) => {
                      const normalized = component / 255;
                      return normalized <= 0.03928
                        ? normalized / 12.92
                        : Math.pow((normalized + 0.055) / 1.055, 2.4);
                    };
                    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
                  };

                  const contrast = (foreground, background) => {
                    const fg = parse(foreground);
                    const bg = parse(background);
                    const fgLum = luminance(fg);
                    const bgLum = luminance(bg);
                    const lighter = Math.max(fgLum, bgLum);
                    const darker = Math.min(fgLum, bgLum);
                    return (lighter + 0.05) / (darker + 0.05);
                  };

                  const themeIds = ["dark-academia-light", "swiss-international", "neumorphism", "minimal", "spacejam-neocities"];
                  return themeIds.map((themeId) => {
                    const option = document.querySelector(`.theme-option[data-theme="${themeId}"]`);
                    if (!option) {
                      return { themeId, name: 0, description: 0 };
                    }

                    const name = option.querySelector('.theme-name');
                    const description = option.querySelector('.theme-description');
                    const background = getComputedStyle(option).backgroundColor;

                    return {
                      themeId,
                      name: name ? contrast(getComputedStyle(name).color, background) : 0,
                      description: description ? contrast(getComputedStyle(description).color, background) : 0,
                    };
                  });
                }
                """
            )

            for row in rows:
                assert row["name"] >= 4.5, row["themeId"]
                assert row["description"] >= 4.5, row["themeId"]

            await browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
