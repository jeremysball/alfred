import asyncio
import socket
import time
import urllib.request
from threading import Thread

import pytest
import uvicorn
from playwright.async_api import async_playwright

from alfred.interfaces.webui.server import create_app

THEMES = ("kidcore-playground", "element-modern", "spacejam-neocities")


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


@pytest.mark.slow
@pytest.mark.asyncio
@pytest.mark.parametrize("theme", THEMES)
async def test_settings_menu_renders_into_a_body_level_portal(theme: str) -> None:
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
            await page.add_init_script(f"localStorage.setItem('alfred-theme', '{theme}');")
            await page.goto(
                f"http://127.0.0.1:{port}/static/index.html",
                wait_until="networkidle",
            )
            await page.click('button[aria-label="Settings"]')
            await page.wait_for_timeout(150)

            data = await page.evaluate(
                """
                () => {
                  const portalRoot = document.getElementById('settings-portal-root');
                  const settingsContent = portalRoot?.querySelector('.settings-content');
                  const contentBox = settingsContent?.getBoundingClientRect();
                  const topmost = contentBox
                    ? document.elementFromPoint(
                        Math.floor(contentBox.left + contentBox.width / 2),
                        Math.floor(contentBox.top + contentBox.height / 2)
                      )
                    : null;

                  return {
                    portalRootParent: portalRoot?.parentElement?.tagName || '',
                    portalRootChildren: portalRoot?.children.length || 0,
                    contentParentId: settingsContent?.parentElement?.id || '',
                    contentInsideSettingsMenu: Boolean(document.querySelector('settings-menu .settings-content')),
                    settingsContentVisible: Boolean(settingsContent && contentBox && contentBox.width > 0 && contentBox.height > 0),
                    topmostIsSettingsContent: Boolean(topmost?.closest('.settings-content')),
                  };
                }
                """
            )

            assert data["portalRootParent"] == "BODY"
            assert data["portalRootChildren"] == 2
            assert data["contentParentId"] == "settings-portal-root"
            assert data["contentInsideSettingsMenu"] is False
            assert data["settingsContentVisible"] is True
            assert data["topmostIsSettingsContent"] is True

            target_theme = {
                "kidcore-playground": "element-modern",
                "element-modern": "spacejam-neocities",
                "spacejam-neocities": "kidcore-playground",
            }[theme]
            await page.click(f'.settings-content .theme-option[data-theme="{target_theme}"]')
            await page.wait_for_timeout(150)

            post_click = await page.evaluate(
                """
                () => {
                  const portalRoot = document.getElementById('settings-portal-root');
                  return {
                    theme: document.documentElement.getAttribute('data-theme'),
                    portalRootChildren: portalRoot?.children.length || 0,
                  };
                }
                """
            )

            assert post_click["theme"] == target_theme
            assert post_click["portalRootChildren"] == 0

            await browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
