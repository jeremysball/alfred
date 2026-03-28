"""Test reasoning block scroll behavior preserves manual scroll position."""

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

REASONING_SAMPLE = """Analyzing the problem step by step.

First, I need to consider all possible approaches.
Then evaluate each one carefully.
Finally, select the optimal solution based on constraints."""


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


async def _create_message_with_reasoning(page, theme: str) -> None:
    await page.evaluate(
        """
        ({ theme }) => {
          document.documentElement.setAttribute('data-theme', theme);
          const messageList = document.getElementById('message-list');
          if (!messageList) {
            return;
          }

          messageList.innerHTML = '';
          const message = document.createElement('chat-message');
          message.setAttribute('role', 'assistant');
          message.setAttribute('timestamp', new Date().toISOString());
          messageList.appendChild(message);

          // Match live streaming: create an active reasoning block first,
          // then append into it so the block starts expanded.
          message.startNewReasoningBlock();
          message.appendReasoning('Initial reasoning line\\n');
        }
        """,
        {"theme": theme},
    )

    await page.wait_for_function(
        """
        () => {
          const message = document.querySelector('#message-list chat-message[role="assistant"]');
          const reasoning = message?.querySelector('.reasoning-content');
          return Boolean(
            reasoning && getComputedStyle(reasoning).display !== 'none'
          );
        }
        """
    )


async def _get_reasoning_scroll_state(page) -> dict[str, object] | None:
    return await page.evaluate(
        """
        () => {
          const message = document.querySelector('#message-list chat-message[role="assistant"]');
          const reasoning = message?.querySelector('.reasoning-content');
          
          if (!reasoning) {
            return null;
          }
          
          return {
            scrollTop: reasoning.scrollTop,
            scrollHeight: reasoning.scrollHeight,
            clientHeight: reasoning.clientHeight,
            atBottom: (reasoning.scrollTop + reasoning.clientHeight) >= (reasoning.scrollHeight - 8),
          };
        }
        """
    )


async def _append_reasoning_chunk(page, chunk: str) -> None:
    await page.evaluate(
        """
        ({ chunk }) => {
          const message = document.querySelector('#message-list chat-message[role="assistant"]');
          if (message && message.appendReasoning) {
            message.appendReasoning(chunk);
          }
        }
        """,
        {"chunk": chunk},
    )


async def _scroll_reasoning_to(page, position: str) -> None:
    """Scroll reasoning to 'top', 'middle', or 'bottom'."""
    await page.evaluate(
        """
        ({ position }) => {
          const message = document.querySelector('#message-list chat-message[role="assistant"]');
          const reasoning = message?.querySelector('.reasoning-content');
          
          if (!reasoning) return;
          
          if (position === 'top') {
            reasoning.scrollTop = 0;
          } else if (position === 'bottom') {
            reasoning.scrollTop = reasoning.scrollHeight;
          } else if (position === 'middle') {
            reasoning.scrollTop = Math.floor(reasoning.scrollHeight / 3);
          }
        }
        """,
        {"position": position},
    )


@pytest.mark.slow
@pytest.mark.asyncio
async def test_reasoning_scroll_preserves_manual_position() -> None:
    """When user scrolls up, new chunks should not jump scroll to bottom."""
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

            await _create_message_with_reasoning(page, "modern-dark")

            # Add enough content to make it scrollable
            for i in range(20):
                await _append_reasoning_chunk(page, f"Line {i}: {REASONING_SAMPLE}\n\n")

            await page.wait_for_timeout(100)

            # Scroll to middle position (simulating user reading)
            await _scroll_reasoning_to(page, "middle")
            await page.wait_for_timeout(50)

            # Capture scroll state before update
            before_state = await _get_reasoning_scroll_state(page)
            assert before_state is not None
            assert before_state["atBottom"] is False  # We scrolled up

            scroll_top_before = before_state["scrollTop"]

            # Append new chunk while user is scrolled up
            await _append_reasoning_chunk(page, "NEW CHUNK: This should not jump scroll\n")
            await page.wait_for_timeout(100)

            # Capture scroll state after update
            after_state = await _get_reasoning_scroll_state(page)
            assert after_state is not None

            # Scroll position should be preserved (approximately)
            scroll_delta = abs(after_state["scrollTop"] - scroll_top_before)
            assert scroll_delta < 50, f"Scroll jumped by {scroll_delta}px, should preserve position"

            await browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)


@pytest.mark.slow
@pytest.mark.asyncio
async def test_reasoning_scroll_auto_sticks_when_at_bottom() -> None:
    """When user is at bottom, new chunks should auto-stick to bottom."""
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

            await _create_message_with_reasoning(page, "modern-dark")

            # Add content to make it scrollable
            for i in range(10):
                await _append_reasoning_chunk(page, f"Line {i}: {REASONING_SAMPLE}\n\n")

            await page.wait_for_timeout(100)

            # Scroll to bottom (simulating user watching new content)
            await _scroll_reasoning_to(page, "bottom")
            await page.wait_for_timeout(50)

            # Verify we're at bottom
            before_state = await _get_reasoning_scroll_state(page)
            assert before_state is not None
            assert before_state["atBottom"] is True

            scroll_height_before = before_state["scrollHeight"]

            # Append several rapid chunks to reproduce the "fighting itself" behavior.
            for i in range(5):
                await _append_reasoning_chunk(page, f"NEW CHUNK {i}: This should auto-stick\n")

            await page.wait_for_timeout(150)

            # Capture scroll state after update
            after_state = await _get_reasoning_scroll_state(page)
            assert after_state is not None

            # Should still be at bottom after new content
            assert after_state["atBottom"] is True, "Should auto-stick to bottom when already there"

            # Scroll height should have increased
            assert after_state["scrollHeight"] > scroll_height_before

            await browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
