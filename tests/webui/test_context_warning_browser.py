from __future__ import annotations

import asyncio
import socket
import time
import urllib.request
from threading import Thread
from typing import cast
from unittest.mock import AsyncMock, patch

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
async def test_browser_context_warning_renders_persistent_system_message() -> None:
    port = _find_free_port()
    fake_alfred = FakeAlfred()
    context_data = {
        "system_prompt": {"sections": [{"name": "AGENTS.md", "tokens": 12}], "total_tokens": 12},
        "blocked_context_files": ["SOUL.md"],
        "warnings": ["Blocked context files: SOUL.md"],
        "memories": {"displayed": 0, "total": 0, "items": [], "tokens": 0},
        "session_history": {"count": 0, "messages": [], "tokens": 0},
        "tool_calls": {"count": 0, "items": [], "tokens": 0},
        "total_tokens": 12,
    }

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

        with patch("alfred.context_display.get_context_display", AsyncMock(return_value=context_data)):
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch()
                page = await browser.new_page(viewport={"width": 1440, "height": 900})
                await page.goto(f"http://127.0.0.1:{port}/static/index.html", wait_until="domcontentloaded")

                await page.wait_for_function(
                    "() => document.querySelector('#connection-pill')?.classList.contains('connected')",
                    timeout=10000,
                )

                await page.fill('#message-input', '/context')
                await page.click('#send-button')

                warning_message = page.locator('chat-message[data-warning="true"]')
                await warning_message.wait_for(state="attached", timeout=10000)
                rendered = await warning_message.locator('.message-content').text_content()

                assert rendered is not None
                assert rendered.startswith('WARNING:')
                assert 'Blocked context files: SOUL.md' in rendered
                await browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
