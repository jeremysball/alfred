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
from tests.webui.fakes import FakeAlfred, make_message, make_session

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

    harness_url = f"http://127.0.0.1:{port}/harness"
    harness_html = """
    <!doctype html>
    <html>
      <body>
        <div id="message-list"></div>
        <div id="input-area"></div>
        <input id="message-input" />
        <button id="send-button"></button>
        <button id="stop-button"></button>
        <div id="connection-pill"></div>
        <div id="connection-status-anchor"></div>
        <div id="connection-status-tooltip"></div>
        <div id="chat-container"></div>
        <div id="queue-badge"></div>
        <div id="completion-menu"></div>
        <script src="/static/js/components/chat-message.js?v=5"></script>
        <script src="/static/js/websocket-client.js?v=5"></script>
        <script>
          window.alfredWebSocketClient = new AlfredWebSocketClient();
          window.alfredWebSocketClient.connect = () => {};
        </script>
        <script type="module" src="/static/js/main.js?v=23"></script>
      </body>
    </html>
    """

    async def fulfill_harness(route) -> None:
        await route.fulfill(status=200, content_type="text/html", body=harness_html)

    async def fulfill_empty_css(route) -> None:
        await route.fulfill(status=200, content_type="text/javascript", body="")

    try:
        await _wait_for_server(port)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            await page.route(harness_url, fulfill_harness)
            await page.route("**/*.css", fulfill_empty_css)
            await page.goto(harness_url, wait_until="networkidle")
            await page.wait_for_function("() => window.__alfredWebUI?.emitMessage !== undefined")

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


@pytest.mark.slow
@pytest.mark.asyncio
async def test_pull_to_refresh_shows_indicator_and_triggers_reconnect() -> None:
    port = _find_free_port()
    config = uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = Thread(target=server.run, daemon=True)
    thread.start()

    harness_url = f"http://127.0.0.1:{port}/harness"
    harness_html = """
    <!doctype html>
    <html>
      <body>
        <div id="message-list"></div>
        <div id="input-area"></div>
        <textarea id="message-input"></textarea>
        <button id="send-button"></button>
        <button id="stop-button"></button>
        <div id="connection-pill"></div>
        <div id="connection-status-anchor"></div>
        <div id="connection-status-tooltip"></div>
        <div id="chat-container" style="height: 320px; overflow: auto;"></div>
        <div id="queue-badge"></div>
        <div id="completion-menu"></div>
        <status-bar id="status-bar"></status-bar>
        <script src="/static/js/components/chat-message.js?v=5"></script>
        <script src="/static/js/websocket-client.js?v=5"></script>
        <script src="/static/js/features/mobile-gestures/pull-to-refresh.js"></script>
        <script>
          window.__connectCalls = 0;
          window.__reconnectCalls = 0;

          AlfredWebSocketClient.prototype.connect = function() {
            window.__connectCalls += 1;
            this.isConnected = true;
          };

          AlfredWebSocketClient.prototype.reconnect = function() {
            window.__reconnectCalls += 1;
            this.isConnected = true;
            window.setTimeout(() => {
              this.dispatchEvent(new CustomEvent('connected', { detail: { stubbed: true } }));
            }, 0);
          };
        </script>
        <script type="module" src="/static/js/main.js?v=23"></script>
      </body>
    </html>
    """

    async def fulfill_harness(route) -> None:
        await route.fulfill(status=200, content_type="text/html", body=harness_html)

    async def fulfill_empty_css(route) -> None:
        await route.fulfill(status=200, content_type="text/javascript", body="")

    try:
        await _wait_for_server(port)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            context = await browser.new_context(viewport={"width": 430, "height": 900}, has_touch=True)
            page = await context.new_page()
            await page.route(harness_url, fulfill_harness)
            await page.route("**/*.css", fulfill_empty_css)
            await page.goto(harness_url, wait_until="networkidle")
            await page.wait_for_function("() => window.__alfredWebUI?.emitMessage !== undefined")
            await page.wait_for_function("() => document.getElementById('pull-to-refresh-indicator') !== null")

            await page.evaluate(
                """
                () => {
                  const element = document.getElementById('chat-container');
                  if (!element) return;

                  const makeTouch = (x, y) => new Touch({
                    identifier: 1,
                    target: element,
                    clientX: x,
                    clientY: y,
                    pageX: x,
                    pageY: y,
                    screenX: x,
                    screenY: y,
                  });

                  const dispatch = (type, x, y) => {
                    const touch = makeTouch(x, y);
                    element.dispatchEvent(new TouchEvent(type, {
                      bubbles: true,
                      cancelable: true,
                      touches: type === 'touchend' ? [] : [touch],
                      targetTouches: type === 'touchend' ? [] : [touch],
                      changedTouches: [touch],
                    }));
                  };

                  dispatch('touchstart', 100, 100);
                  dispatch('touchmove', 100, 210);
                }
                """
            )

            drag_state = await page.evaluate(
                """
                () => {
                  const indicator = document.getElementById('pull-to-refresh-indicator');
                  const label = indicator?.querySelector('.pull-to-refresh-indicator__label');

                  return {
                    state: indicator?.dataset.pullState || '',
                    progress: indicator?.dataset.pullProgress || '',
                    label: label?.textContent || '',
                    opacity: indicator?.style.opacity || '',
                    reconnectCalls: window.__reconnectCalls || 0,
                  };
                }
                """
            )

            assert drag_state["state"] == "ready"
            assert drag_state["progress"] == "100"
            assert drag_state["label"] == "Release to refresh"
            assert drag_state["opacity"] == "1"
            assert drag_state["reconnectCalls"] == 0

            await page.evaluate(
                """
                () => {
                  const element = document.getElementById('chat-container');
                  if (!element) return;

                  const touch = new Touch({
                    identifier: 1,
                    target: element,
                    clientX: 100,
                    clientY: 210,
                    pageX: 100,
                    pageY: 210,
                    screenX: 100,
                    screenY: 210,
                  });

                  element.dispatchEvent(new TouchEvent('touchend', {
                    bubbles: true,
                    cancelable: true,
                    touches: [],
                    targetTouches: [],
                    changedTouches: [touch],
                  }));
                }
                """
            )

            await page.wait_for_function(
                """
                () => window.__reconnectCalls === 1 &&
                  document.getElementById('pull-to-refresh-indicator')?.dataset.pullState === 'idle'
                """
            )

            final_state = await page.evaluate(
                """
                () => {
                  const indicator = document.getElementById('pull-to-refresh-indicator');
                  return {
                    state: indicator?.dataset.pullState || '',
                    reconnectCalls: window.__reconnectCalls || 0,
                  };
                }
                """
            )

            assert final_state["state"] == "idle"
            assert final_state["reconnectCalls"] == 1

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
        websocket.receive_json()  # daemon.status
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
        websocket.receive_json()  # daemon.status
        websocket.receive_json()  # status.update

        assert session_loaded["type"] == "session.loaded"
        payload_messages = session_loaded["payload"]["messages"]
        assistant_messages = [msg for msg in payload_messages if msg["role"] == "assistant"]
        assert assistant_messages, payload_messages
        assistant = assistant_messages[-1]
        assert assistant["content"].startswith("Hello ")
        assert assistant["streaming"] is True
        assert "partial" in assistant["content"] or assistant["content"] == "Hello "


@pytest.mark.slow
@pytest.mark.asyncio
async def test_retry_button_replays_last_user_prompt() -> None:
    port = _find_free_port()
    fake_alfred = FakeAlfred(
        chunks=["Retry ", "response"],
        sessions=[make_session("session-1", messages=[make_message("user", "Please regenerate this", id="user-old")])],
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
            harness_url = f"http://127.0.0.1:{port}/harness"
            harness_html = """
            <!doctype html>
            <html>
              <body>
                <div id="message-list"></div>
                <div id="input-area"></div>
                <textarea id="message-input"></textarea>
                <button id="send-button"></button>
                <button id="stop-button"></button>
                <div id="connection-pill"></div>
                <div id="connection-status-anchor"></div>
                <div id="connection-status-tooltip"></div>
                <div id="chat-container"></div>
                <div id="queue-badge"></div>
                <completion-menu id="completion-menu"></completion-menu>
                <status-bar id="status-bar"></status-bar>
                <script src="/static/js/components/chat-message.js?v=5"></script>
                <script src="/static/js/websocket-client.js?v=5"></script>
                <script>
                  class CompletionMenuElement extends HTMLElement {
                    constructor() {
                      super();
                      this._visible = false;
                      this._items = [];
                      this.hidden = true;
                    }

                    setItems(items) {
                      this._items = Array.isArray(items) ? items : [];
                    }

                    show() {
                      this._visible = true;
                      this.hidden = false;
                    }

                    hide() {
                      this._visible = false;
                      this.hidden = true;
                    }

                    isVisible() {
                      return this._visible;
                    }

                    selectNext() {}
                    selectPrevious() {}
                    selectCurrent() {}
                  }

                  if (!customElements.get('completion-menu')) {
                    customElements.define('completion-menu', CompletionMenuElement);
                  }
                </script>
                <script type="module" src="/static/js/main.js?v=23"></script>
              </body>
            </html>
            """

            async def fulfill_harness(route) -> None:
                await route.fulfill(status=200, content_type="text/html", body=harness_html)

            async def fulfill_empty_css(route) -> None:
                await route.fulfill(status=200, content_type="text/javascript", body="")

            await page.route(harness_url, fulfill_harness)
            await page.route("**/*.css", fulfill_empty_css)
            await page.goto(harness_url, wait_until="networkidle")

            await page.evaluate(
                """
                () => {
                  const list = document.getElementById('message-list');
                  if (!list) return;

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
                  message.includes('"type":"chat.edit"') &&
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
            assert any('"type":"chat.edit"' in message and '"content":"Please regenerate this"' in message for message in sent_messages)

            user_messages = await page.evaluate(
                """
                () => Array.from(document.querySelectorAll('#message-list chat-message[role="user"]'))
                  .map((element) => element.getAttribute('content'))
                """
            )
            assert user_messages == ["Please regenerate this"]

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
            assert assistant_messages == ["Retry response"]

            await browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)


@pytest.mark.slow
@pytest.mark.asyncio
async def test_retry_button_cancels_stream_and_restarts_without_duplicate_user_prompt() -> None:
    port = _find_free_port()
    fake_alfred = FakeAlfred(
        chunks=["Retry ", "response"],
        chunk_delay=0.5,
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
            harness_url = f"http://127.0.0.1:{port}/harness"
            harness_html = """
            <!doctype html>
            <html>
              <body>
                <div id="message-list"></div>
                <div id="input-area"></div>
                <textarea id="message-input"></textarea>
                <button id="send-button"></button>
                <button id="stop-button"></button>
                <div id="connection-pill"></div>
                <div id="connection-status-anchor"></div>
                <div id="connection-status-tooltip"></div>
                <div id="chat-container"></div>
                <div id="queue-badge"></div>
                <completion-menu id="completion-menu"></completion-menu>
                <status-bar id="status-bar"></status-bar>
                <script src="/static/js/components/chat-message.js?v=5"></script>
                <script src="/static/js/websocket-client.js?v=5"></script>
                <script>
                  class CompletionMenuElement extends HTMLElement {
                    constructor() {
                      super();
                      this._visible = false;
                      this._items = [];
                      this.hidden = true;
                    }

                    setItems(items) {
                      this._items = Array.isArray(items) ? items : [];
                    }

                    show() {
                      this._visible = true;
                      this.hidden = false;
                    }

                    hide() {
                      this._visible = false;
                      this.hidden = true;
                    }

                    isVisible() {
                      return this._visible;
                    }

                    selectNext() {}
                    selectPrevious() {}
                    selectCurrent() {}
                  }

                  if (!customElements.get('completion-menu')) {
                    customElements.define('completion-menu', CompletionMenuElement);
                  }
                </script>
                <script type="module" src="/static/js/main.js?v=23"></script>
              </body>
            </html>
            """

            async def fulfill_harness(route) -> None:
                await route.fulfill(status=200, content_type="text/html", body=harness_html)

            async def fulfill_empty_css(route) -> None:
                await route.fulfill(status=200, content_type="text/javascript", body="")

            await page.route(harness_url, fulfill_harness)
            await page.route("**/*.css", fulfill_empty_css)
            await page.goto(harness_url, wait_until="networkidle")

            await page.fill("#message-input", "Please regenerate this")
            await page.click("#send-button")

            await page.wait_for_function(
                """
                () => Boolean(document.querySelector('chat-message.streaming'))
                """
            )

            await page.click('chat-message.streaming [data-action="retry"]')

            await page.wait_for_function(
                """
                () => window.__sentWebSocketMessages.some((message) =>
                  message.includes('"type":"chat.cancel"')
                )
                """
            )
            await page.wait_for_function(
                """
                () => window.__sentWebSocketMessages.some((message) =>
                  message.includes('"type":"chat.edit"') &&
                  message.includes('"content":"Please regenerate this"')
                )
                """
            )
            await page.wait_for_function(
                """
                () => Array.from(document.querySelectorAll('#message-list chat-message[role="user"]'))
                  .map((element) => element.getAttribute('content'))
                  .length === 1
                """
            )
            await page.wait_for_function(
                """
                () => Array.from(
                  document.querySelectorAll('#message-list chat-message[role="assistant"]')
                ).length === 1
                """
            )
            await page.wait_for_function(
                """
                () => Array.from(
                  document.querySelectorAll('#message-list chat-message[role="assistant"]')
                ).at(-1)?.getContent?.() === 'Retry response'
                """
            )

            sent_messages = await page.evaluate("window.__sentWebSocketMessages")
            assert any('"type":"chat.cancel"' in message for message in sent_messages)
            assert any('"type":"chat.edit"' in message and '"content":"Please regenerate this"' in message for message in sent_messages)

            user_messages = await page.evaluate(
                """
                () => Array.from(document.querySelectorAll('#message-list chat-message[role="user"]'))
                  .map((element) => element.getAttribute('content'))
                """
            )
            assert user_messages == ["Please regenerate this"]

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
            assert assistant_messages == ["Retry response"]

            await browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
