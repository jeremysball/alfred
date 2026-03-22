from __future__ import annotations

import asyncio
import socket
import time
import urllib.request
from pathlib import Path
from threading import Thread
from typing import cast

import pytest
import uvicorn
from fastapi.testclient import TestClient
from playwright.async_api import async_playwright

from alfred.interfaces.webui.server import create_app
from tests.webui.fakes import FakeAlfred, make_session

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
async def test_session_loaded_reconciles_partial_assistant_message_in_place() -> None:
    port = _find_free_port()
    config = uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = Thread(target=server.run, daemon=True)
    thread.start()

    try:
        await _wait_for_server(port)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            await page.goto(f"http://127.0.0.1:{port}/static/index.html", wait_until="networkidle")

            await page.evaluate(
                """
                () => {
                  const list = document.getElementById('message-list');
                  if (!list) return;

                  const userMessage = document.createElement('chat-message');
                  userMessage.setAttribute('role', 'user');
                  userMessage.setAttribute('content', 'Hello Alfred');
                  userMessage.setAttribute('timestamp', new Date().toISOString());
                  userMessage.setAttribute('data-session-message', 'true');
                  list.appendChild(userMessage);

                  window.__alfredWebUI.emitMessage({
                    type: 'chat.started',
                    payload: { messageId: 'assistant-1', role: 'assistant' },
                  });

                  window.__alfredWebUI.emitMessage({
                    type: 'chat.chunk',
                    payload: { messageId: 'assistant-1', content: 'partial stream' },
                  });

                  const assistant = document.querySelector('chat-message[message-id="assistant-1"]');
                  if (assistant) {
                    assistant.dataset.marker = 'keep-me';
                  }
                }
                """
            )

            await page.evaluate(
                """
                () => {
                  window.__alfredWebUI.emitMessage({
                    type: 'session.loaded',
                    payload: {
                      sessionId: 'session-1',
                      messages: [
                        {
                          id: 'message-0',
                          role: 'user',
                          content: 'Hello Alfred',
                          timestamp: '2026-03-21T00:00:00.000Z',
                          streaming: false,
                        },
                        {
                          id: 'assistant-1',
                          role: 'assistant',
                          content: 'partial stream, now resumed',
                          timestamp: '2026-03-21T00:00:01.000Z',
                          reasoningContent: '',
                          toolCalls: [],
                          streaming: true,
                        },
                      ],
                    },
                  });
                }
                """
            )

            data = await page.evaluate(
                """
                () => {
                  const sessionMessages = Array.from(
                    document.querySelectorAll('#message-list chat-message[data-session-message="true"]')
                  );
                  const assistant = document.querySelector(
                    '#message-list chat-message[data-session-message="true"][data-marker="keep-me"]'
                  );

                  return {
                    count: sessionMessages.length,
                    assistantStillThere: Boolean(assistant),
                    assistantContent: assistant?.getAttribute('content') || '',
                    assistantStreaming: assistant?.classList.contains('streaming') || false,
                    firstRole: sessionMessages[0]?.getAttribute('role') || '',
                    secondRole: sessionMessages[1]?.getAttribute('role') || '',
                  };
                }
                """
            )

            assert data["count"] == 2
            assert data["assistantStillThere"] is True
            assert "partial stream, now resumed" in data["assistantContent"]
            assert data["assistantStreaming"] is True
            assert data["firstRole"] == "user"
            assert data["secondRole"] == "assistant"

            await browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)


@pytest.mark.asyncio
async def test_reconnect_sees_partially_streamed_message_after_disconnect() -> None:
    fake_alfred = FakeAlfred(
        chunks=["Hello ", "partial ", "response"],
        chunk_delay=0.05,
    )
    app = create_app(alfred_instance=fake_alfred)
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        websocket.receive_json()  # connected
        websocket.receive_json()  # session.loaded
        websocket.receive_json()  # status.update

        websocket.send_json({"type": "chat.send", "payload": {"content": "resume the stream"}})

        first_chunk = None
        while first_chunk is None:
            data = websocket.receive_json()
            if data["type"] == "chat.chunk":
                first_chunk = data
            elif data["type"] in {"chat.started", "status.update"}:
                continue
            else:
                pytest.fail(f"Unexpected message type before disconnect: {data['type']}")

        assert first_chunk["payload"]["content"].startswith("Hello ")
        assert "response" not in first_chunk["payload"]["content"]
        websocket.close()

    with client.websocket_connect("/ws") as websocket:
        websocket.receive_json()  # connected
        session_loaded = websocket.receive_json()
        websocket.receive_json()  # status.update

        assert session_loaded["type"] == "session.loaded"
        payload_messages = session_loaded["payload"]["messages"]
        assistant_messages = [msg for msg in payload_messages if msg["role"] == "assistant"]
        assert assistant_messages, payload_messages
        assistant = assistant_messages[-1]
        assert assistant["content"].startswith("Hello ")
        assert assistant["streaming"] is True
        assert "partial" in assistant["content"] or assistant["content"] == "Hello "


@pytest.mark.asyncio
async def test_retry_button_replays_last_user_prompt() -> None:
    port = _find_free_port()
    fake_alfred = FakeAlfred(
        chunks=["Retry ", "response"],
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
            await page.goto(
                f"http://127.0.0.1:{port}/static/index.html",
                wait_until="networkidle",
            )

            await page.evaluate(
                """
                () => {
                  const list = document.getElementById('message-list');
                  if (!list) return;

                  const user = document.createElement('chat-message');
                  user.setAttribute('role', 'user');
                  user.setAttribute('content', 'Please regenerate this');
                  user.setAttribute('timestamp', new Date().toISOString());
                  user.setAttribute('data-session-message', 'true');
                  list.appendChild(user);

                  const assistant = document.createElement('chat-message');
                  assistant.setAttribute('role', 'assistant');
                  assistant.setAttribute('content', 'Old answer');
                  assistant.setAttribute('timestamp', new Date().toISOString());
                  assistant.setAttribute('message-id', 'assistant-old');
                  assistant.setAttribute('data-session-message', 'true');
                  list.appendChild(assistant);
                }
                """
            )

            await page.click('chat-message[message-id="assistant-old"] [data-action="retry"]')
            await page.wait_for_function(
                """
                () => window.__sentWebSocketMessages.some((message) =>
                  message.includes('"type":"chat.send"') &&
                  message.includes('"content":"Please regenerate this"')
                )
                """
            )
            await page.wait_for_function(
                """
                () => Array.from(document.querySelectorAll('#message-list chat-message[role="assistant"]'))
                  .at(-1)?.getContent?.() === 'Retry response'
                """
            )

            sent_messages = await page.evaluate("window.__sentWebSocketMessages")
            assert any('"type":"chat.send"' in message and '"content":"Please regenerate this"' in message for message in sent_messages)

            user_messages = await page.evaluate(
                """
                () => Array.from(document.querySelectorAll('#message-list chat-message[role="user"]'))
                  .map((element) => element.getAttribute('content'))
                """
            )
            assert user_messages == ["Please regenerate this", "Please regenerate this"]

            assistant_messages = await page.evaluate(
                """
                () => Array.from(
                  document.querySelectorAll('#message-list chat-message[role="assistant"]')
                ).map((element) => (
                  typeof element.getContent === 'function'
                    ? element.getContent()
                    : element.getAttribute('content') || ''
                ))
                """
            )
            assert assistant_messages[0] == "Old answer"
            assert assistant_messages[-1] == "Retry response"

            await browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
