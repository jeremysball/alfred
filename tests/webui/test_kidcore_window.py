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
INDEX_HTML = PROJECT_ROOT / "src/alfred/interfaces/webui/static/index.html"
WINDOW_CSS = PROJECT_ROOT / "src/alfred/interfaces/webui/static/css/themes/kidcore-homeboard.css"


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


def test_kidcore_window_markup_includes_xp_controls() -> None:
    source = INDEX_HTML.read_text()
    css = WINDOW_CSS.read_text()

    assert 'id="kidcore-homeboard-window"' in source
    assert 'id="kidcore-homeboard-titlebar"' in source
    assert 'id="kidcore-homeboard-collapse"' in source
    assert 'id="kidcore-homeboard-close"' in source
    assert 'id="kidcore-homeboard-launcher"' in source
    assert 'aria-label="Open scrapbook window"' in source
    assert 'aria-label="Collapse scrapbook window"' in source
    assert 'aria-label="Close scrapbook window"' in source

    for selector in [
        '[data-theme="kidcore-playground"] .kidcore-window',
        '[data-theme="kidcore-playground"] .kidcore-window-titlebar',
        '[data-theme="kidcore-playground"] .kidcore-window-controls',
        '[data-theme="kidcore-playground"] .kidcore-window-body',
        '[data-theme="kidcore-playground"] .kidcore-window[data-window-state="collapsed"]',
        '[data-theme="kidcore-playground"] .kidcore-homeboard-launcher',
    ]:
        assert selector in css


@pytest.mark.asyncio
async def test_kidcore_window_collapses_closes_and_restores() -> None:
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
            await page.goto(f"http://127.0.0.1:{port}/static/index.html", wait_until="networkidle")

            initial = await page.evaluate(
                """
                () => {
                  const windowEl = document.getElementById('kidcore-homeboard-window');
                  const bodyEl = document.getElementById('kidcore-homeboard');
                  return {
                    state: windowEl?.dataset.windowState || '',
                    hidden: windowEl ? windowEl.hidden : true,
                    bodyHidden: bodyEl ? bodyEl.hidden : true,
                  };
                }
                """
            )
            assert initial["state"] == "open"
            assert initial["hidden"] is False
            assert initial["bodyHidden"] is False

            await page.click('#kidcore-homeboard-collapse')
            await page.wait_for_timeout(100)
            collapsed = await page.evaluate(
                """
                () => {
                  const windowEl = document.getElementById('kidcore-homeboard-window');
                  const bodyEl = document.getElementById('kidcore-homeboard');
                  return {
                    state: windowEl?.dataset.windowState || '',
                    bodyHidden: bodyEl ? bodyEl.hidden : true,
                    bodyCollapsed: bodyEl?.dataset.windowBodyState || '',
                  };
                }
                """
            )
            assert collapsed["state"] == "collapsed"
            assert collapsed["bodyHidden"] is True
            assert collapsed["bodyCollapsed"] == "collapsed"

            await page.click('#kidcore-homeboard-collapse')
            await page.wait_for_timeout(100)
            reopened = await page.evaluate(
                """
                () => {
                  const windowEl = document.getElementById('kidcore-homeboard-window');
                  const bodyEl = document.getElementById('kidcore-homeboard');
                  return {
                    state: windowEl?.dataset.windowState || '',
                    bodyHidden: bodyEl ? bodyEl.hidden : true,
                  };
                }
                """
            )
            assert reopened["state"] == "open"
            assert reopened["bodyHidden"] is False

            await page.click('#kidcore-homeboard-close')
            await page.wait_for_timeout(100)
            closed = await page.evaluate(
                """
                () => {
                  const windowEl = document.getElementById('kidcore-homeboard-window');
                  const launcherEl = document.getElementById('kidcore-homeboard-launcher');
                  return {
                    state: windowEl?.dataset.windowState || '',
                    hidden: windowEl ? windowEl.hidden : true,
                    launcherHidden: launcherEl ? launcherEl.hidden : true,
                  };
                }
                """
            )
            assert closed["state"] == "closed"
            assert closed["hidden"] is True
            assert closed["launcherHidden"] is False

            await page.click('#kidcore-homeboard-launcher')
            await page.wait_for_timeout(100)
            restored = await page.evaluate(
                """
                () => {
                  const windowEl = document.getElementById('kidcore-homeboard-window');
                  const launcherEl = document.getElementById('kidcore-homeboard-launcher');
                  const bodyEl = document.getElementById('kidcore-homeboard');
                  return {
                    state: windowEl?.dataset.windowState || '',
                    hidden: windowEl ? windowEl.hidden : true,
                    launcherHidden: launcherEl ? launcherEl.hidden : true,
                    bodyHidden: bodyEl ? bodyEl.hidden : true,
                  };
                }
                """
            )
            assert restored["state"] == "open"
            assert restored["hidden"] is False
            assert restored["launcherHidden"] is True
            assert restored["bodyHidden"] is False

            await browser.close()
    finally:
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except TimeoutError:
                process.kill()
                await process.wait()


@pytest.mark.asyncio
async def test_kidcore_window_drags_on_desktop() -> None:
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
            await page.goto(f"http://127.0.0.1:{port}/static/index.html", wait_until="networkidle")

            before = await page.locator('#kidcore-homeboard-window').bounding_box()
            assert before is not None

            handle = page.locator('#kidcore-homeboard-titlebar')
            handle_box = await handle.bounding_box()
            assert handle_box is not None

            await page.mouse.move(handle_box["x"] + 40, handle_box["y"] + 16)
            await page.mouse.down()
            await page.mouse.move(handle_box["x"] + 160, handle_box["y"] + 110, steps=12)
            await page.mouse.up()
            await page.wait_for_timeout(100)

            after = await page.locator('#kidcore-homeboard-window').bounding_box()
            assert after is not None
            assert after["x"] != before["x"] or after["y"] != before["y"]

            await browser.close()
    finally:
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except TimeoutError:
                process.kill()
                await process.wait()


@pytest.mark.asyncio
async def test_kidcore_window_starts_collapsed_on_mobile() -> None:
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
            await page.goto(f"http://127.0.0.1:{port}/static/index.html", wait_until="networkidle")

            state = await page.evaluate(
                """
                () => {
                  const windowEl = document.getElementById('kidcore-homeboard-window');
                  const bodyEl = document.getElementById('kidcore-homeboard');
                  return {
                    state: windowEl?.dataset.windowState || '',
                    bodyHidden: bodyEl ? bodyEl.hidden : true,
                    launcherHidden: document.getElementById('kidcore-homeboard-launcher')?.hidden ?? true,
                  };
                }
                """
            )

            assert state["state"] == "collapsed"
            assert state["bodyHidden"] is True
            assert state["launcherHidden"] is True

            window_box = await page.locator('#kidcore-homeboard-window').bounding_box()
            assert window_box is not None
            assert window_box["height"] <= 84

            await browser.close()
    finally:
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except TimeoutError:
                process.kill()
                await process.wait()
