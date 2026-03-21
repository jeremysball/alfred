from __future__ import annotations

import asyncio
import socket
import time
import urllib.request
from pathlib import Path
from typing import cast

import pytest
from playwright.async_api import async_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[2]
THEME_SELECTOR = PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/components/theme-selector.js"
INDEX_HTML = PROJECT_ROOT / "src/alfred/interfaces/webui/static/index.html"
SPACEJAM_THEME = PROJECT_ROOT / "src/alfred/interfaces/webui/static/css/themes/spacejam-neocities.css"


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


def test_spacejam_theme_is_registered_and_loaded() -> None:
    selector_source = THEME_SELECTOR.read_text()
    index_source = INDEX_HTML.read_text()

    assert "spacejam-neocities" in selector_source
    assert "Space Jam Neocities" in selector_source
    assert "/static/css/themes/spacejam-neocities.css?v=3" in index_source
    assert SPACEJAM_THEME.exists(), "spacejam-neocities.css is missing"

    theme_source = SPACEJAM_THEME.read_text()
    assert '[data-theme="spacejam-neocities"]' in theme_source
    for token in [
        "--bg-primary",
        "--bg-secondary",
        "--text-primary",
        "--accent-primary",
        "--composer-bg",
        "--status-bg",
        "--send-button-bg",
    ]:
        assert token in theme_source, f"Missing token: {token}"


@pytest.mark.asyncio
async def test_spacejam_theme_activates_with_loud_retro_surface() -> None:
    port = _find_free_port()
    process = await asyncio.create_subprocess_exec(
        "uv",
        "run",
        "alfred",
        "webui",
        "--port",
        str(port),
        cwd=PROJECT_ROOT,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )

    try:
        await _wait_for_server(port)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            await page.add_init_script(
                "localStorage.setItem('alfred-theme', 'spacejam-neocities');"
            )
            await page.goto(
                f"http://127.0.0.1:{port}/static/index.html",
                wait_until="networkidle",
            )

            await page.evaluate(
                """
                () => {
                  const list = document.querySelector('#message-list');
                  if (!list) return;

                  const message = document.createElement('div');
                  message.className = 'message assistant';
                  message.innerHTML = `
                    <div class="message-header">
                      <span class="message-avatar" aria-hidden="true">◆</span>
                      <span class="message-role">Alfred</span>
                    </div>
                    <div class="message-bubble">
                      <div class="message-content">The neon needs a little more gravity.</div>
                    </div>
                  `;
                  list.appendChild(message);
                }
                """
            )

            data = await page.evaluate(
                """
                () => {
                  const body = getComputedStyle(document.body);
                  const header = getComputedStyle(document.querySelector('.app-header h1'));
                  const messageBubble = document.querySelector('.message.assistant .message-bubble');
                  const messageBubbleStyle = messageBubble ? getComputedStyle(messageBubble) : null;
                  const homeboard = document.querySelector('#kidcore-homeboard');
                  const tabs = Array.from(document.querySelectorAll('.kidcore-homeboard-tab'))
                    .map((button) => button.textContent?.replace(/\\s+/g, ' ').trim() || '');

                  return {
                    theme: document.documentElement.getAttribute('data-theme'),
                    backgroundImage: body.backgroundImage,
                    headerFont: header.fontFamily,
                    messageTransform: messageBubbleStyle?.transform || 'none',
                    messageBorderWidth: messageBubbleStyle?.borderTopWidth || '',
                    messageShadow: messageBubbleStyle?.boxShadow || '',
                    homeboardHidden: homeboard ? homeboard.hidden : true,
                    tabs,
                  };
                }
                """
            )

            assert data["theme"] == "spacejam-neocities"
            assert "radial-gradient" in data["backgroundImage"] or "conic-gradient" in data["backgroundImage"]
            assert "Arial Black" in data["headerFont"] or "Impact" in data["headerFont"]
            assert data["messageTransform"] != "none"
            assert data["messageBorderWidth"] != "0px"
            assert data["messageShadow"]
            assert data["homeboardHidden"] is False
            assert "updates" in data["tabs"]

            await browser.close()
    finally:
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except TimeoutError:
                process.kill()
                await process.wait()
