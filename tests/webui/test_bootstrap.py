from __future__ import annotations

import pytest
from playwright.async_api import async_playwright, expect


@pytest.mark.slow
@pytest.mark.asyncio
async def test_webui_bootstrap_allows_message_send(websocket_server) -> None:
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

        try:
            await page.goto(
                f"http://127.0.0.1:{websocket_server.port}/static/index.html",
                wait_until="networkidle",
            )

            await expect(page.locator("#input-area")).to_have_attribute("data-composer-state", "idle")
            assert await page.evaluate("() => !!window.__alfredWebUI") is True
            assert await page.evaluate("() => window.__alfredWebUI.getComposerState()") == "idle"

            await page.fill("#message-input", "bootstrap smoke test")
            await page.click("#send-button")

            await page.wait_for_function(
                """
                () => window.__sentWebSocketMessages.some((message) => {
                  try {
                    const parsed = JSON.parse(message);
                    return parsed.type === 'chat.send' && parsed.payload?.content === 'bootstrap smoke test';
                  } catch {
                    return false;
                  }
                })
                """
            )
        finally:
            await browser.close()
