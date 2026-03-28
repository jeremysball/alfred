from __future__ import annotations

import asyncio
import socket
import time
import urllib.request
from threading import Thread
from typing import cast

import pytest
import uvicorn
from playwright.async_api import async_playwright, expect

from alfred.interfaces.webui.server import create_app
from tests.webui.fakes import FakeAlfred, make_session


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


@pytest.mark.slow
@pytest.mark.asyncio
async def test_streaming_composer_keyboard_contract() -> None:
    port = _find_free_port()
    fake_alfred = FakeAlfred(
        chunks=["one ", "two ", "three"],
        chunk_delay=0.55,
        sessions=[make_session("session-1", messages=[])],
    )
    config = uvicorn.Config(
        create_app(alfred_instance=fake_alfred),
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
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            await page.add_init_script(
                """
                window.__sentWebSocketMessages = [];
                const originalSend = WebSocket.prototype.send;
                WebSocket.prototype.send = function(data) {
                  window.__sentWebSocketMessages.push(data);
                  return originalSend.call(this, data);
                };
                """
            )
            await page.goto(f"http://127.0.0.1:{port}/static/index.html", wait_until="networkidle")

            await expect(page.locator("#input-area")).to_have_attribute("data-composer-state", "idle")
            assert await page.evaluate("() => window.__alfredWebUI.getComposerState()") == "idle"

            await page.fill("#message-input", "first prompt")
            await page.click("#send-button")

            await expect(page.locator("#input-area")).to_have_attribute("data-composer-state", "streaming")
            await expect(page.locator("chat-message.streaming")).to_have_count(1)
            assert await page.evaluate("() => window.__alfredWebUI.getComposerState()") == "streaming"
            assert await page.evaluate("() => window.__alfredWebUI.getCurrentAssistantMessageState()") == "streaming"
            assert await page.locator("chat-message.streaming").get_attribute("data-message-state") == "streaming"
            await expect(page.locator("#message-input")).to_be_enabled()

            await page.fill("#message-input", "queued follow-up")
            await page.keyboard.press("Control+a")
            await page.keyboard.press("Enter")
            await expect(page.locator("#queue-badge")).to_have_text("1")
            await expect(page.locator("#message-input")).to_have_value("")

            await page.keyboard.press("Escape")
            await page.wait_for_function(
                """
                () => window.__sentWebSocketMessages.some((message) => {
                  try {
                    return JSON.parse(message).type === 'chat.cancel';
                  } catch {
                    return false;
                  }
                })
                """
            )
            await page.wait_for_function(
                """
                () => window.__sentWebSocketMessages.some((message) => {
                  try {
                    const parsed = JSON.parse(message);
                    return parsed.type === 'chat.send' && parsed.payload?.content === 'queued follow-up';
                  } catch {
                    return false;
                  }
                })
                """
            )

            await page.wait_for_function(
                """
                () => document.querySelectorAll('chat-message.streaming').length === 1 &&
                  window.__alfredWebUI.getComposerState() === 'streaming'
                """
            )

            await page.fill("#message-input", "steer now")
            await page.keyboard.press("Enter")
            await page.wait_for_function(
                """
                () => window.__sentWebSocketMessages.filter((message) => {
                  try {
                    return JSON.parse(message).type === 'chat.cancel';
                  } catch {
                    return false;
                  }
                }).length >= 2
                """
            )
            await page.wait_for_function(
                """
                () => window.__sentWebSocketMessages.some((message) => {
                  try {
                    const parsed = JSON.parse(message);
                    return parsed.type === 'chat.send' && parsed.payload?.content === 'steer now';
                  } catch {
                    return false;
                  }
                })
                """
            )

            await page.wait_for_function(
                """
                () => window.__alfredWebUI.getComposerState() === 'idle' &&
                  document.querySelectorAll('#message-list chat-message[role="assistant"]').length >= 1 &&
                  document.querySelectorAll('chat-message.streaming').length === 0
                """
            )

            last_user = page.locator('#message-list chat-message[role="user"]').last
            last_user_content = await last_user.get_attribute('content')
            last_user_id = await last_user.get_attribute('message-id')
            assert last_user_content == 'steer now'
            assert last_user_id
            await expect(last_user.locator('[data-action="edit"]')).to_be_visible()

            await last_user.locator('[data-action="edit"]').click()
            await expect(page.locator('#input-area')).to_have_attribute('data-composer-state', 'editing')
            await expect(last_user).to_have_attribute('data-message-state', 'editing')
            await expect(page.locator('#input-area')).to_have_attribute('data-edit-message-id', last_user_id)
            await expect(page.locator('#message-input')).to_have_value('steer now')
            assert await page.evaluate("() => window.__alfredWebUI.getComposerState()") == 'editing'

            await page.fill('#message-input', 'steer now revised')
            await page.keyboard.press('Enter')
            await page.wait_for_function(
                """
                () => window.__sentWebSocketMessages.some((message) => {
                  try {
                    const parsed = JSON.parse(message);
                    return parsed.type === 'chat.edit' && parsed.payload?.content === 'steer now revised';
                  } catch {
                    return false;
                  }
                })
                """
            )
            await expect(page.locator('#input-area')).to_have_attribute('data-composer-state', 'streaming')

            await browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
