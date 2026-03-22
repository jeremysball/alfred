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


@pytest.mark.slow
@pytest.mark.asyncio
async def test_scrapbook_toolbar_filters_guestbook_entries_and_persists_updates() -> None:
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
            await page.add_init_script("localStorage.setItem('alfred-theme', 'spacejam-neocities');")
            await page.goto(
                f"http://127.0.0.1:{port}/static/index.html",
                wait_until="networkidle",
            )

            controls = await page.evaluate(
                """
                () => ({
                  searchInputExists: Boolean(document.querySelector('#kidcore-homeboard-search')),
                  exportButtonExists: Boolean(document.querySelector('#kidcore-homeboard-export')),
                  clearButtonExists: Boolean(document.querySelector('#kidcore-homeboard-clear-search')),
                  updatesTabExists: Boolean(document.querySelector('[data-kidcore-tab="updates"]')),
                })
                """
            )
            assert controls["searchInputExists"] is True
            assert controls["exportButtonExists"] is True
            assert controls["clearButtonExists"] is True
            assert controls["updatesTabExists"] is True

            await page.click('[data-kidcore-tab="guestbook"]')
            await page.fill("#kidcore-guestbook-name", "Moonbeam")
            await page.fill("#kidcore-guestbook-message", "hello from the glitter comet")
            await page.click("#kidcore-guestbook-submit")
            await page.wait_for_timeout(120)

            await page.fill("#kidcore-homeboard-search", "Moonbeam")
            await page.wait_for_timeout(120)
            filtered = await page.evaluate(
                """
                () => {
                  const entries = Array.from(document.querySelectorAll('#kidcore-guestbook-entries .kidcore-guestbook-entry'));
                  const visibleEntries = entries.filter((entry) => !entry.hidden);
                  return {
                    visibleCount: visibleEntries.length,
                    text: visibleEntries.map((entry) => entry.textContent || '').join('\\n'),
                    summary: document.querySelector('#kidcore-homeboard-search-summary')?.textContent || '',
                  };
                }
                """
            )
            assert filtered["visibleCount"] == 1
            assert "Moonbeam" in filtered["text"]
            assert "match" in filtered["summary"].lower()

            await page.click("#kidcore-homeboard-clear-search")
            await page.wait_for_timeout(80)

            await page.click('[data-kidcore-tab="updates"]')
            await page.fill("#kidcore-update-title", "retro tools")
            await page.fill("#kidcore-update-message", "search, nav, export, and notes are alive")
            await page.click("#kidcore-update-submit")
            await page.wait_for_timeout(120)

            updates = await page.evaluate(
                """
                () => ({
                  count: document.querySelectorAll('#kidcore-updates-list .kidcore-update-entry').length,
                  text: Array.from(document.querySelectorAll('#kidcore-updates-list .kidcore-update-entry'))
                    .map((entry) => entry.textContent || '')
                    .join('\\n'),
                  storage: localStorage.getItem('alfred-kidcore-updates') || '',
                })
                """
            )
            assert updates["count"] >= 1
            assert "retro tools" in updates["text"]
            assert "search, nav, export, and notes are alive" in updates["storage"]

            await page.reload(wait_until="networkidle")
            await page.click('[data-kidcore-tab="updates"]')
            await page.wait_for_timeout(120)
            persisted = await page.evaluate(
                """
                () => ({
                  text: Array.from(document.querySelectorAll('#kidcore-updates-list .kidcore-update-entry'))
                    .map((entry) => entry.textContent || '')
                    .join('\\n'),
                })
                """
            )
            assert "retro tools" in persisted["text"]

            await browser.close()
    finally:
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except TimeoutError:
                process.kill()
                await process.wait()
