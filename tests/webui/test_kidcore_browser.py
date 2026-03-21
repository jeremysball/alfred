import asyncio
import socket
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import cast

import pytest
from playwright.async_api import async_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[2]


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
async def test_kidcore_playground_theme_activates_in_browser() -> None:
    port = _find_free_port()
    process = await asyncio.create_subprocess_exec(
        "uv",
        "run",
        "alfred",
        "webui",
        "--port",
        str(port),
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        await _wait_for_server(port)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            await page.add_init_script(
                "localStorage.setItem('alfred-theme', 'kidcore-playground');"
            )
            await page.goto(
                f"http://127.0.0.1:{port}/static/index.html",
                wait_until="networkidle",
            )
            await page.click('button[aria-label="Settings"]')
            await page.wait_for_timeout(150)

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
                      <div class="message-content">Kidcore still needs to read like a chat app.</div>
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
                  const active = document.querySelector('.theme-option.active[data-theme="kidcore-playground"]');
                  const banner = document.querySelector('.kidcore-banner');
                  const bannerStyle = banner ? getComputedStyle(banner) : null;
                  const messageBubble = document.querySelector('.message.assistant .message-bubble');
                  const messageBubbleStyle = messageBubble ? getComputedStyle(messageBubble) : null;
                  const messageInput = getComputedStyle(document.querySelector('.message-input'));
                  const sendButton = getComputedStyle(document.querySelector('.send-button'));

                  return {
                    theme: document.documentElement.getAttribute('data-theme'),
                    fontFamily: body.fontFamily,
                    backgroundImage: body.backgroundImage,
                    headerColor: header.color,
                    activeText: active?.querySelector('.theme-name')?.textContent || '',
                    bannerDisplay: bannerStyle?.display || '',
                    bannerText: banner?.textContent || '',
                    bannerBorder: bannerStyle?.borderTopWidth || '',
                    messageBubbleBackground:
                      messageBubbleStyle?.backgroundImage || messageBubbleStyle?.backgroundColor || '',
                    messageBubbleBorder: messageBubbleStyle?.borderTopWidth || '',
                    messageInputBackground: messageInput.backgroundColor,
                    sendButtonBackground: sendButton.backgroundImage || sendButton.backgroundColor,
                  };
                }
                """
            )

            assert data["theme"] == "kidcore-playground"
            assert "Comic Sans" in data["fontFamily"] or "Trebuchet" in data["fontFamily"]
            assert "radial-gradient" in data["backgroundImage"]
            assert data["activeText"] == "Kidcore Playground"
            assert data["headerColor"]

            assert data["bannerDisplay"] == "flex"
            assert "KIDCORE PLAYGROUND" in data["bannerText"]
            assert data["bannerBorder"] != "0px"

            assert data["messageBubbleBackground"]
            assert data["messageBubbleBorder"] != "0px"
            assert data["messageInputBackground"] != "rgba(0, 0, 0, 0)"
            assert data["sendButtonBackground"] != "none"

            await page.reload(wait_until="networkidle")
            persisted = await page.evaluate(
                """
                () => {
                  const active = document.querySelector('.theme-option.active[data-theme="kidcore-playground"]');
                  return {
                    theme: document.documentElement.getAttribute('data-theme'),
                    activeText: active?.querySelector('.theme-name')?.textContent || '',
                  };
                }
                """
            )

            assert persisted["theme"] == "kidcore-playground"
            assert persisted["activeText"] == "Kidcore Playground"

            await browser.close()
    finally:
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except TimeoutError:
                process.kill()
                await process.wait()
