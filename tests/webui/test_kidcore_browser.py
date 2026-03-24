import asyncio
import socket
import time
import urllib.request
from pathlib import Path
from typing import cast

import pytest
from playwright.async_api import async_playwright

from alfred.cron.daemon import DaemonManager

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


@pytest.mark.slow
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
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )

    try:
        await _wait_for_server(port)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            await page.add_init_script("localStorage.setItem('alfred-theme', 'kidcore-playground');")
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
                  const homeboard = document.querySelector('#kidcore-homeboard');
                  const homeboardStyle = homeboard ? getComputedStyle(homeboard) : null;
                  const guestbookPanel = document.querySelector('#kidcore-guestbook-panel');
                  const activeTab = document.querySelector('.kidcore-homeboard-tab.active');
                  const messageBubble = document.querySelector('.message.assistant .message-bubble');
                  const messageBubbleStyle = messageBubble ? getComputedStyle(messageBubble) : null;
                  const messageInput = getComputedStyle(document.querySelector('.message-input'));
                  const sendButton = getComputedStyle(document.querySelector('.send-button'));

                  return {
                    theme: document.documentElement.getAttribute('data-theme'),
                    fontFamily: body.fontFamily,
                    backgroundImage: body.backgroundImage,
                    headerColor: header.color,
                    homeboardHidden: homeboard ? homeboard.hidden : true,
                    homeboardDisplay: homeboardStyle?.display || '',
                    guestbookActive: guestbookPanel?.classList.contains('active') || false,
                    activeText: activeTab?.textContent || '',
                    note: document.querySelector('.kidcore-site-note')?.textContent || '',
                    bannerExists: Boolean(document.querySelector('.kidcore-banner')),
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
            assert "Georgia" in data["fontFamily"] or "Times" in data["fontFamily"]
            assert "radial-gradient" in data["backgroundImage"]
            assert data["headerColor"]
            assert data["homeboardHidden"] is False
            assert data["homeboardDisplay"] != "none"
            assert data["guestbookActive"] is True
            assert data["activeText"] == "guestbook"
            assert "guestbooks" in data["note"].lower()
            assert data["bannerExists"] is False
            assert data["messageBubbleBackground"]
            assert data["messageBubbleBorder"] != "0px"
            assert data["messageInputBackground"] != "rgba(0, 0, 0, 0)"
            assert data["sendButtonBackground"] != "none"

            await page.reload(wait_until="networkidle")
            persisted = await page.evaluate(
                """
                () => ({
                  theme: document.documentElement.getAttribute('data-theme'),
                  homeboardHidden: document.querySelector('#kidcore-homeboard')?.hidden ?? true,
                })
                """
            )

            assert persisted["theme"] == "kidcore-playground"
            assert persisted["homeboardHidden"] is False

            await browser.close()
    finally:
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except TimeoutError:
                process.kill()
                await process.wait()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_kidcore_connection_status_tooltip_reports_daemon_and_websocket_state() -> None:
    port = _find_free_port()
    process = await asyncio.create_subprocess_exec(
        "uv",
        "run",
        "alfred",
        "webui",
        "--port",
        str(port),
        cwd=PROJECT_ROOT,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )

    try:
        await _wait_for_server(port)

        daemon_manager = DaemonManager()
        expected_daemon_status = "running" if daemon_manager.is_running() else "stopped"
        expected_daemon_pid = daemon_manager.read_pid()

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            await page.add_init_script("localStorage.setItem('alfred-theme', 'kidcore-playground');")
            await page.goto(
                f"http://127.0.0.1:{port}/static/index.html",
                wait_until="networkidle",
            )

            anchor = page.locator("#connection-status-anchor")
            tooltip = page.locator("#connection-status-tooltip")
            pill = page.locator("#connection-pill")

            initial = await pill.evaluate(
                """
                (element) => {
                  const styles = getComputedStyle(element);
                  return {
                    cursor: styles.cursor,
                    boxShadow: styles.boxShadow,
                  };
                }
                """
            )
            assert initial["cursor"] == "help"

            assert await tooltip.is_hidden()

            anchor_box = await anchor.bounding_box()
            assert anchor_box is not None
            await page.mouse.move(
                anchor_box["x"] + (anchor_box["width"] / 2),
                anchor_box["y"] + (anchor_box["height"] / 2),
            )

            await page.wait_for_function(
                """
                () => {
                  const tooltip = document.querySelector('#connection-status-tooltip');
                  if (!tooltip) return false;
                  return getComputedStyle(tooltip).visibility === 'visible';
                }
                """
            )

            tooltip_text = (await tooltip.text_content() or "").strip()
            assert f"Daemon: {expected_daemon_status}" in tooltip_text
            if expected_daemon_pid is not None:
                assert f"PID: {expected_daemon_pid}" in tooltip_text
            assert "WebSocket: connected" in tooltip_text
            assert "Web UI:" in tooltip_text
            assert "Reconnect attempts:" in tooltip_text
            assert "Last close:" in tooltip_text
            assert "Keepalive:" in tooltip_text
            assert "Debug:" in tooltip_text

            portal_data = await page.evaluate(
                """
                () => {
                  const root = document.getElementById('connection-status-portal-root');
                  const tooltip = document.querySelector('#connection-status-tooltip');
                  return {
                    rootParent: root?.parentElement?.tagName || '',
                    rootChildren: root?.children.length || 0,
                    tooltipParent: tooltip?.parentElement?.id || '',
                    layout: root?.dataset.layout || '',
                    open: root?.dataset.open || '',
                  };
                }
                """
            )
            assert portal_data["rootParent"] == "BODY"
            assert portal_data["rootChildren"] == 2
            assert portal_data["tooltipParent"] == "connection-status-portal-root"
            assert portal_data["layout"] == "popover"
            assert portal_data["open"] == "true"

            hovered = await pill.evaluate(
                """
                (element) => {
                  const styles = getComputedStyle(element);
                  return {
                    boxShadow: styles.boxShadow,
                    transform: styles.transform,
                  };
                }
                """
            )
            assert hovered["boxShadow"] != initial["boxShadow"]

            await browser.close()
    finally:
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except TimeoutError:
                process.kill()
                await process.wait()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_kidcore_connection_status_uses_bottom_sheet_on_mobile() -> None:
    port = _find_free_port()
    process = await asyncio.create_subprocess_exec(
        "uv",
        "run",
        "alfred",
        "webui",
        "--port",
        str(port),
        cwd=PROJECT_ROOT,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )

    try:
        await _wait_for_server(port)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 390, "height": 844})
            await page.add_init_script("localStorage.setItem('alfred-theme', 'kidcore-playground');")
            await page.goto(
                f"http://127.0.0.1:{port}/static/index.html",
                wait_until="networkidle",
            )

            anchor = page.locator("#connection-status-anchor")
            overlay = page.locator("#connection-status-portal-root .connection-status-overlay")

            await anchor.focus()
            await page.keyboard.press('Enter')
            await page.wait_for_function(
                """
                () => {
                  const root = document.getElementById('connection-status-portal-root');
                  const tooltip = document.querySelector('#connection-status-tooltip');
                  return root?.dataset.open === 'true'
                    && root?.dataset.layout === 'sheet'
                    && tooltip
                    && getComputedStyle(tooltip).visibility === 'visible';
                }
                """
            )
            await page.wait_for_timeout(100)

            data = await page.evaluate(
                """
                () => {
                  const root = document.getElementById('connection-status-portal-root');
                  const tooltip = document.querySelector('#connection-status-tooltip');
                  const overlay = root?.querySelector('.connection-status-overlay');
                  const rect = tooltip?.getBoundingClientRect();
                  return {
                    rootParent: root?.parentElement?.tagName || '',
                    rootChildren: root?.children.length || 0,
                    tooltipParent: tooltip?.parentElement?.id || '',
                    layout: root?.dataset.layout || '',
                    open: root?.dataset.open || '',
                    overlayVisible: overlay ? getComputedStyle(overlay).display !== 'none' : false,
                    tooltipLeft: rect ? Math.round(rect.left) : null,
                    tooltipRight: rect ? Math.round(window.innerWidth - rect.right) : null,
                    tooltipBottom: rect ? Math.round(window.innerHeight - rect.bottom) : null,
                  };
                }
                """
            )

            assert data["rootParent"] == "BODY"
            assert data["rootChildren"] == 2
            assert data["tooltipParent"] == "connection-status-portal-root"
            assert data["layout"] == "sheet"
            assert data["open"] == "true"
            assert data["overlayVisible"] is True
            assert 0 <= data["tooltipLeft"] <= 4
            assert 0 <= data["tooltipRight"] <= 4
            assert 0 <= data["tooltipBottom"] <= 4

            await overlay.click(position={"x": 10, "y": 10})
            await page.wait_for_function(
                """
                () => {
                  const root = document.getElementById('connection-status-portal-root');
                  return root?.dataset.open === 'false';
                }
                """
            )
            assert await overlay.is_hidden()

            await browser.close()
    finally:
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except TimeoutError:
                process.kill()
                await process.wait()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_kidcore_playground_theme_survives_narrow_viewport() -> None:
    port = _find_free_port()
    process = await asyncio.create_subprocess_exec(
        "uv",
        "run",
        "alfred",
        "webui",
        "--port",
        str(port),
        cwd=PROJECT_ROOT,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )

    try:
        await _wait_for_server(port)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 390, "height": 844})
            await page.add_init_script("localStorage.setItem('alfred-theme', 'kidcore-playground');")
            await page.goto(
                f"http://127.0.0.1:{port}/static/index.html",
                wait_until="networkidle",
            )

            await page.evaluate(
                """
                () => {
                  const list = document.querySelector('#message-list');
                  if (!list) return;

                  for (let index = 0; index < 20; index += 1) {
                    const message = document.createElement('div');
                    message.className = 'message user';
                    message.innerHTML = `
                      <div class="message-bubble">
                        <div class="message-content">mobile filler ${index}</div>
                      </div>
                    `;
                    list.appendChild(message);
                  }
                }
                """
            )
            await page.wait_for_timeout(100)

            header = await page.locator(".app-header").bounding_box()
            homeboard_window = await page.locator("#kidcore-homeboard-window").bounding_box()
            homeboard_body = await page.locator("#kidcore-homeboard").bounding_box()
            music_play = await page.locator("#kidcore-music-play").bounding_box()
            music_mute = await page.locator("#kidcore-music-mute").bounding_box()
            sfx_toggle = await page.locator("#kidcore-sfx-toggle").bounding_box()
            composer = await page.locator("#message-input").bounding_box()
            send_button = await page.locator("#send-button").bounding_box()
            connection_pill = await page.locator("#connection-pill").bounding_box()
            connection_text = (await page.locator("#connection-pill").text_content() or "").strip()

            assert header is not None
            assert homeboard_window is not None
            assert homeboard_body is None
            assert music_play is not None
            assert music_mute is not None
            assert sfx_toggle is not None
            assert composer is not None
            assert send_button is not None

            assert header["width"] <= 390.5
            assert header["height"] <= 200
            assert homeboard_window["width"] <= 390.5
            assert homeboard_window["height"] <= 90
            assert music_play["x"] >= 0
            assert music_play["x"] + music_play["width"] <= 390.5
            assert music_mute["x"] >= 0
            assert music_mute["x"] + music_mute["width"] <= 390.5
            assert sfx_toggle["x"] >= 0
            assert sfx_toggle["x"] + sfx_toggle["width"] <= 390.5
            assert composer["x"] >= 0
            assert composer["x"] + composer["width"] <= 390.5
            assert send_button["x"] >= 0
            assert send_button["x"] + send_button["width"] <= 390.5
            assert connection_pill is not None
            assert connection_text == "●"
            assert abs(connection_pill["width"] - connection_pill["height"]) <= 1.0

            scroll_metrics = await page.evaluate(
                """
                () => {
                  const chat = document.querySelector('#chat-container');
                  if (!chat) return { scrollTop: 0, scrollHeight: 0, clientHeight: 0 };
                  // Disable smooth scrolling so the test can observe the final position immediately.
                  chat.style.scrollBehavior = 'auto';
                  chat.scrollTop = chat.scrollHeight;
                  return {
                    scrollTop: chat.scrollTop,
                    scrollHeight: chat.scrollHeight,
                    clientHeight: chat.clientHeight,
                  };
                }
                """
            )

            assert scroll_metrics["scrollHeight"] > scroll_metrics["clientHeight"]
            assert scroll_metrics["scrollTop"] > 0

            await browser.close()
    finally:
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except TimeoutError:
                process.kill()
                await process.wait()
