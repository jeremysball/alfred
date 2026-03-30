from __future__ import annotations

import asyncio
import socket
import time
import urllib.request
from threading import Thread
from typing import cast

import pytest
import uvicorn
from playwright.async_api import async_playwright

from alfred.interfaces.webui.server import create_app
from tests.webui.fakes import FakeAlfred


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return cast(int, sock.getsockname()[1])


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
@pytest.mark.slow
async def test_browser_context_menu_sheet_uses_theme_tokens() -> None:
    port = _find_free_port()
    fake_alfred = FakeAlfred()

    config = uvicorn.Config(
        create_app(alfred_instance=fake_alfred, debug=True),
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    thread = Thread(target=server.run, daemon=True)
    thread.start()

    try:
        await _wait_for_server(port)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 390, "height": 844})
            await page.goto(f"http://127.0.0.1:{port}/static/index.html", wait_until="domcontentloaded")

            await page.wait_for_function(
                "() => typeof window.MessageContextMenu === 'object' && typeof window.ContextMenuLib === 'object'",
                timeout=10000,
            )

            await page.evaluate(
                """
                () => {
                  document.documentElement.setAttribute('data-theme', 'spacejam-neocities');

                  const messageList = document.getElementById('message-list');
                  const message = document.createElement('div');
                  message.id = 'context-menu-sample';
                  message.className = 'message user';
                  message.innerHTML = `
                    <div class="message-header">
                      <span class="message-avatar" aria-hidden="true">👤</span>
                      <span class="message-role">User</span>
                    </div>
                    <div class="message-bubble">
                      <span class="message-avatar-small">👤</span>
                      <span class="message-content">This context menu sheet should feel like a themed surface and keep enough width to avoid cramped labels.</span>
                    </div>
                  `;
                  messageList.appendChild(message);
                }
                """,
            )

            await page.evaluate(
                """
                () => {
                  const message = document.querySelector('#context-menu-sample');
                  if (!message || !window.MessageContextMenu) {
                    throw new Error('message context menu is unavailable');
                  }
                  window.MessageContextMenu.showMessageMenu(message, 24, 24);
                }
                """,
            )

            menu = page.locator('.context-menu[data-layout="sheet"]')
            await menu.wait_for(state="visible", timeout=10000)

            menu_text = await menu.text_content()
            assert menu_text is not None
            assert "Copy Text" in menu_text
            assert "Quote Reply" in menu_text
            assert "Select All" in menu_text

            menu_items = menu.locator('.context-menu-item')
            assert await menu_items.count() == 3

            menu_style = await page.evaluate(
                """
                () => {
                  const probe = document.createElement('div');
                  probe.style.cssText = 'position: fixed; left: -9999px; top: -9999px; background: var(--surface-panel-bg); border: 1px solid var(--surface-panel-border); color: var(--surface-panel-header-text);';
                  document.body.appendChild(probe);

                  const menu = document.querySelector('.context-menu');
                  const probeStyle = getComputedStyle(probe);
                  const menuStyle = menu ? getComputedStyle(menu) : null;

                  return {
                    probeBg: probeStyle.backgroundColor,
                    probeBorder: probeStyle.borderTopColor,
                    probeText: probeStyle.color,
                    menuBg: menuStyle ? menuStyle.backgroundColor : '',
                    menuBorder: menuStyle ? menuStyle.borderTopColor : '',
                    menuText: menuStyle ? menuStyle.color : '',
                    menuLayout: menu?.dataset.layout || '',
                  };
                }
                """,
            )

            assert menu_style["menuLayout"] == "sheet"
            assert menu_style["menuBg"] == menu_style["probeBg"]
            assert menu_style["menuBorder"] == menu_style["probeBorder"]
            assert menu_style["menuText"] == menu_style["probeText"]

            box = await menu.bounding_box()
            assert box is not None
            assert box["width"] > 340
            assert box["x"] <= 12
            assert box["y"] > 500

            await browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
