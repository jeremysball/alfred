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
async def test_browser_websocket_answers_ping_before_chat_complete() -> None:
    port = _find_free_port()
    fake_alfred = FakeAlfred(chunks=["chunk "] * 120, chunk_delay=0.01)
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
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            await page.goto(f"http://127.0.0.1:{port}/static/index.html", wait_until="domcontentloaded")

            result = await page.evaluate(
                """
                async () => {
                  const received = [];
                  const ws = new WebSocket(`ws://${window.location.host}/ws`);

                  ws.onmessage = (event) => {
                    received.push(JSON.parse(event.data));
                  };

                  await new Promise((resolve, reject) => {
                    const timeout = setTimeout(() => reject(new Error('open timeout')), 5000);
                    ws.onopen = () => {
                      clearTimeout(timeout);
                      resolve();
                    };
                    ws.onerror = () => {
                      clearTimeout(timeout);
                      reject(new Error('websocket error'));
                    };
                  });

                  async function nextMessage(expectedTypes, timeoutMs = 5000) {
                    const deadline = Date.now() + timeoutMs;
                    while (Date.now() < deadline) {
                      const index = received.findIndex((message) => expectedTypes.includes(message.type));
                      if (index !== -1) {
                        return received.splice(index, 1)[0];
                      }
                      await new Promise((resolve) => setTimeout(resolve, 10));
                    }
                    throw new Error(`timed out waiting for ${expectedTypes.join(', ')}`);
                  }

                  await nextMessage(['connected']);
                  await nextMessage(['session.loaded']);
                  await nextMessage(['daemon.status']);
                  await nextMessage(['status.update']);

                  ws.send(JSON.stringify({
                    type: 'chat.send',
                    payload: { content: 'browser keepalive check' },
                  }));
                  await nextMessage(['chat.started']);

                  ws.send(JSON.stringify({ type: 'ping' }));

                  let sawPongBeforeComplete = false;
                  while (true) {
                    const message = await nextMessage(['pong', 'chat.chunk', 'chat.complete', 'status.update'], 5000);
                    if (message.type === 'pong') {
                      sawPongBeforeComplete = true;
                      break;
                    }
                    if (message.type === 'chat.complete') {
                      break;
                    }
                  }

                  ws.close();
                  return { sawPongBeforeComplete };
                }
                """
            )

            assert result["sawPongBeforeComplete"] is True
            await browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
