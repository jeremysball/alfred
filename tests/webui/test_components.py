from __future__ import annotations

import asyncio
import socket
import time
import urllib.request
from pathlib import Path
from typing import cast

import pytest
from playwright.async_api import async_playwright

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


async def _launch_webui(port: int) -> asyncio.subprocess.Process:
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
    await _wait_for_server(port)
    return process


async def _stop_process(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return

    process.terminate()
    try:
        await asyncio.wait_for(process.wait(), timeout=10)
    except TimeoutError:
        process.kill()
        await process.wait()


@pytest.mark.asyncio
async def test_status_bar_renders_live_updates_in_browser() -> None:
    port = _find_free_port()
    process = await _launch_webui(port)

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            await page.goto(
                f"http://127.0.0.1:{port}/static/index.html",
                wait_until="networkidle",
            )

            await page.evaluate(
                """
                () => {
                  const statusBar = document.querySelector('#status-bar');
                  if (!statusBar) return;
                  statusBar.setModel('kimi-k2');
                  statusBar.setTokens(1200, 3456, 78, 9, 4567);
                  statusBar.setQueue(3);
                  statusBar.setStreaming(true);
                }
                """
            )
            await page.wait_for_timeout(160)

            data = await page.evaluate(
                """
                () => {
                  const statusBar = document.querySelector('#status-bar');
                  const streaming = statusBar?.querySelector('.streaming-section');
                  const throbber = statusBar?.querySelector('.throbber');
                  const model = statusBar?.querySelector('.model-name');
                  const tokens = statusBar?.querySelector('.tokens-display');
                  const queue = statusBar?.querySelector('.queue-count');

                  return {
                    model: model?.textContent || '',
                    tokens: tokens?.textContent || '',
                    queue: queue?.textContent || '',
                    streamingActive: streaming?.classList.contains('active') || false,
                    streamingText: streaming?.querySelector('.streaming-text')?.textContent || '',
                    throbber: throbber?.textContent || '',
                  };
                }
                """
            )

            assert data["model"] == "kimi-k2"
            assert data["tokens"] == "In: 1.2k | Out: 3.5k | Cache: 78 | Reason: 9"
            assert data["queue"] == "3"
            assert data["streamingActive"] is True
            assert data["streamingText"] == "Thinking..."
            assert data["throbber"]

            await page.evaluate(
                """
                () => {
                  const statusBar = document.querySelector('#status-bar');
                  statusBar?.setStreaming(false);
                }
                """
            )
            await page.wait_for_timeout(120)

            stopped = await page.evaluate(
                """
                () => {
                  const statusBar = document.querySelector('#status-bar');
                  const streaming = statusBar?.querySelector('.streaming-section');
                  return {
                    streamingActive: streaming?.classList.contains('active') || false,
                    streamingHidden: streaming?.classList.contains('hidden') || false,
                  };
                }
                """
            )

            assert stopped["streamingActive"] is False
            assert stopped["streamingHidden"] is True

            await browser.close()
    finally:
        await _stop_process(process)


@pytest.mark.asyncio
async def test_toast_container_shows_and_dismisses_toasts_in_browser() -> None:
    port = _find_free_port()
    process = await _launch_webui(port)

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            await page.goto(
                f"http://127.0.0.1:{port}/static/index.html",
                wait_until="networkidle",
            )

            toast_id = await page.evaluate(
                """
                () => {
                  const container = document.querySelector('#toast-container');
                  if (!container) return null;
                  return container.show('Sparkle parade ready', 'success', 0);
                }
                """
            )

            assert isinstance(toast_id, int)
            await page.wait_for_timeout(120)

            shown = await page.evaluate(
                """
                () => {
                  const toast = document.querySelector('#toast-container .toast-success');
                  return {
                    exists: Boolean(toast),
                    text: toast?.textContent || '',
                    classes: toast?.className || '',
                    toastId: toast?.getAttribute('data-toast-id') || '',
                    enter: toast?.classList.contains('toast-enter') || false,
                  };
                }
                """
            )

            assert shown["exists"] is True
            assert "Sparkle parade ready" in shown["text"]
            assert "toast-success" in shown["classes"]
            assert shown["toastId"] == str(toast_id)
            assert shown["enter"] is True

            await page.evaluate(
                """
                (toastId) => {
                  const container = document.querySelector('#toast-container');
                  container?.dismiss(toastId);
                }
                """,
                toast_id,
            )
            await page.wait_for_timeout(350)

            dismissed = await page.evaluate(
                """
                () => ({
                  count: document.querySelectorAll('#toast-container .toast').length,
                })
                """
            )

            assert dismissed["count"] == 0

            await browser.close()
    finally:
        await _stop_process(process)


@pytest.mark.asyncio
async def test_tool_call_component_toggles_and_updates_in_browser() -> None:
    port = _find_free_port()
    process = await _launch_webui(port)

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            await page.goto(
                f"http://127.0.0.1:{port}/static/index.html",
                wait_until="networkidle",
            )

            await page.evaluate(
                """
                () => {
                  const toolCall = document.createElement('tool-call');
                  toolCall.id = 'browser-tool-call';
                  toolCall.setAttribute('tool-call-id', 'call_abc123');
                  toolCall.setAttribute('tool-name', 'read_file');
                  toolCall.setAttribute('arguments', JSON.stringify({ path: '/tmp/demo.txt' }));
                  toolCall.setAttribute('output', 'File contents here');
                  toolCall.setAttribute('status', 'running');
                  toolCall.setAttribute('expanded', 'false');
                  document.body.appendChild(toolCall);
                }
                """
            )
            await page.wait_for_timeout(120)

            collapsed = await page.evaluate(
                """
                () => {
                  const toolCall = document.querySelector('#browser-tool-call');
                  const box = toolCall?.querySelector('.tool-call');
                  return {
                    toolName: toolCall?.querySelector('.tool-name')?.textContent || '',
                    status: toolCall?.querySelector('.tool-status')?.textContent || '',
                    expanded: toolCall?.getAttribute('expanded') || '',
                    collapsedClass: box?.className || '',
                    outputText: toolCall?.querySelector('.tool-output')?.textContent || '',
                  };
                }
                """
            )

            assert collapsed["toolName"] == "read_file"
            assert collapsed["status"] == "running"
            assert collapsed["expanded"] == "false"
            assert "collapsed" in collapsed["collapsedClass"]
            assert "File contents here" in collapsed["outputText"]

            await page.evaluate(
                """
                () => {
                  const toolCall = document.querySelector('#browser-tool-call');
                  toolCall?.setStatus('success');
                  toolCall?.appendOutput('\\nMore output');
                }
                """
            )
            await page.wait_for_timeout(120)

            updated = await page.evaluate(
                """
                () => {
                  const toolCall = document.querySelector('#browser-tool-call');
                  const box = toolCall?.querySelector('.tool-call');
                  return {
                    status: toolCall?.querySelector('.tool-status')?.textContent || '',
                    outputText: toolCall?.querySelector('.tool-output')?.textContent || '',
                    collapsedClass: box?.className || '',
                  };
                }
                """
            )

            assert updated["status"] == "success"
            assert "More output" in updated["outputText"]
            assert "success" in updated["collapsedClass"]

            await page.click("#browser-tool-call .tool-header")
            await page.wait_for_timeout(80)

            expanded = await page.evaluate(
                """
                () => {
                  const toolCall = document.querySelector('#browser-tool-call');
                  const box = toolCall?.querySelector('.tool-call');
                  return {
                    expanded: toolCall?.getAttribute('expanded') || '',
                    expandedClass: box?.className || '',
                    toggle: toolCall?.querySelector('.tool-toggle')?.textContent || '',
                  };
                }
                """
            )

            assert expanded["expanded"] == "true"
            assert "expanded" in expanded["expandedClass"]
            assert expanded["toggle"] == "▼"

            await browser.close()
    finally:
        await _stop_process(process)
