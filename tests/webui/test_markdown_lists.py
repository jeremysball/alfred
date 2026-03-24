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

MARKDOWN_SAMPLE = """Markdown list containment check.

- bullet item one with enough words to wrap inside the message bubble on a narrow screen
- bullet item two with another long sentence that should still stay within the same bubble

1. ordered item one with enough words to wrap inside the message bubble on a narrow screen
2. ordered item two with another long sentence that should still stay within the same bubble
"""


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


async def _render_markdown_message(page, theme: str) -> None:
    await page.evaluate(
        """
        ({ theme, markdown }) => {
          document.documentElement.setAttribute('data-theme', theme);
          const messageList = document.getElementById('message-list');
          if (!messageList) {
            return;
          }

          messageList.innerHTML = '';
          const message = document.createElement('chat-message');
          message.setAttribute('role', 'assistant');
          message.setAttribute('content', markdown);
          message.setAttribute('timestamp', new Date().toISOString());
          messageList.appendChild(message);
        }
        """,
        {"theme": theme, "markdown": MARKDOWN_SAMPLE},
    )

    await page.wait_for_function(
        """
        () => {
          const message = document.querySelector('#message-list chat-message[role="assistant"]');
          return Boolean(
            message?.querySelector('.message-content ul') &&
            message?.querySelector('.message-content ol')
          );
        }
        """
    )


async def _measure_list_containment(page) -> dict[str, object]:
    return await page.evaluate(
        """
        () => {
          const message = document.querySelector('#message-list chat-message[role="assistant"]');
          const bubble = message?.querySelector('.message-bubble');
          const content = message?.querySelector('.message-content');

          if (!bubble || !content) {
            return null;
          }

          const bubbleRect = bubble.getBoundingClientRect();
          const contentRect = content.getBoundingClientRect();
          return {
            bubbleClientWidth: bubble.clientWidth,
            bubbleScrollWidth: bubble.scrollWidth,
            bubbleWidth: bubbleRect.width,
            contentClientWidth: content.clientWidth,
            contentScrollWidth: content.scrollWidth,
            contentWidth: contentRect.width,
            listMetrics: Array.from(content.querySelectorAll('ul, ol')).map((list) => {
              const rect = list.getBoundingClientRect();
              return {
                tag: list.tagName.toLowerCase(),
                leftOffset: rect.left - bubbleRect.left,
                rightOffset: bubbleRect.right - rect.right,
                scrollWidth: list.scrollWidth,
                clientWidth: list.clientWidth,
              };
            }),
          };
        }
        """
    )


@pytest.mark.slow
@pytest.mark.asyncio
async def test_markdown_lists_stay_inside_message_bubbles_on_mobile_and_desktop() -> None:
    port = _find_free_port()
    config = uvicorn.Config(
        create_app(alfred_instance=FakeAlfred()),
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
            await page.goto(f"http://127.0.0.1:{port}/static/index.html", wait_until="networkidle")

            themes = ["modern-dark", "kidcore-playground"]
            viewports = [
                {"width": 1440, "height": 900},
                {"width": 390, "height": 844},
            ]

            for viewport in viewports:
                await page.set_viewport_size(viewport)
                await page.wait_for_timeout(100)

                for theme in themes:
                    await _render_markdown_message(page, theme)
                    metrics = await _measure_list_containment(page)

                    assert metrics is not None
                    assert metrics["bubbleScrollWidth"] <= metrics["bubbleClientWidth"] + 1
                    assert metrics["contentScrollWidth"] <= metrics["contentClientWidth"] + 1
                    assert metrics["listMetrics"]

                    for list_metrics in metrics["listMetrics"]:
                        assert list_metrics["tag"] in {"ul", "ol"}
                        assert list_metrics["leftOffset"] >= -1
                        assert list_metrics["rightOffset"] >= -1
                        assert list_metrics["scrollWidth"] <= list_metrics["clientWidth"] + 1

            await browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
