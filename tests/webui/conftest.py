"""Shared fixtures for Web UI browser tests."""

from __future__ import annotations

import asyncio
import socket
import time
import urllib.request
from collections.abc import AsyncIterator
from dataclasses import dataclass
from threading import Thread
from typing import cast

import pytest
import uvicorn
from playwright.async_api import Page, async_playwright

from alfred.interfaces.webui.server import create_app
from tests.webui.fakes import FakeAlfred, make_session


def _find_free_port() -> int:
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return cast(int, sock.getsockname()[1])


async def _wait_for_server(port: int, timeout: float = 20.0) -> None:
    """Wait for server to be ready."""
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


@dataclass
class WebSocketServer:
    """Running WebSocket server fixture data."""

    port: int
    alfred: FakeAlfred
    server: uvicorn.Server
    thread: Thread


@pytest.fixture(scope="function")
async def websocket_server() -> AsyncIterator[WebSocketServer]:
    """Create a WebSocket server with FakeAlfred for browser tests."""
    port = _find_free_port()
    fake_alfred = FakeAlfred(
        chunks=["Hello", "!", " How", " can", " I", " help", "?"],
        sessions=[make_session("session-1", messages=[])],
    )

    config = uvicorn.Config(
        create_app(alfred_instance=fake_alfred),  # type: ignore[arg-type]
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    thread = Thread(target=server.run, daemon=True)
    thread.start()

    try:
        await _wait_for_server(port)
        yield WebSocketServer(port=port, alfred=fake_alfred, server=server, thread=thread)
    finally:
        server.should_exit = True
        thread.join(timeout=5.0)


@pytest.fixture(scope="function")
async def page_helper(
    websocket_server: WebSocketServer,
) -> AsyncIterator[Page]:
    """Create a Playwright page connected to the WebSocket server."""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 375, "height": 667})

        # Inject WebSocket message tracking
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

        await page.goto(
            f"http://127.0.0.1:{websocket_server.port}/static/index.html",
            wait_until="networkidle",
        )

        yield page

        await browser.close()
