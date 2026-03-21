import asyncio
import socket
import subprocess
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
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        await _wait_for_server(port)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            await page.add_init_script(
                "localStorage.setItem('alfred-theme', 'kidcore-playground');"
            )
            await page.goto(
                f"http://127.0.0.1:{port}/static/index.html",
                wait_until="networkidle",
            )
            await page.click('button[aria-label="Settings"]')
            await page.wait_for_timeout(150)

            data = await page.evaluate(
                """
                () => {
                  const body = getComputedStyle(document.body);
                  const header = getComputedStyle(document.querySelector('.app-header h1'));
                  const active = document.querySelector('.theme-option.active[data-theme="kidcore-playground"]');

                  return {
                    theme: document.documentElement.getAttribute('data-theme'),
                    fontFamily: body.fontFamily,
                    backgroundImage: body.backgroundImage,
                    headerColor: header.color,
                    activeText: active?.querySelector('.theme-name')?.textContent || '',
                  };
                }
                """
            )

            assert data["theme"] == "kidcore-playground"
            assert "Comic Sans" in data["fontFamily"] or "Trebuchet" in data["fontFamily"]
            assert "radial-gradient" in data["backgroundImage"]
            assert data["activeText"] == "Kidcore Playground"
            assert data["headerColor"]

            await page.reload(wait_until="networkidle")
            persisted = await page.evaluate(
                """
                () => {
                  const active = document.querySelector('.theme-option.active[data-theme="kidcore-playground"]');
                  return {
                    theme: document.documentElement.getAttribute('data-theme'),
                    activeText: active?.querySelector('.theme-name')?.textContent || '',
                  };
                }
                """
            )

            assert persisted["theme"] == "kidcore-playground"
            assert persisted["activeText"] == "Kidcore Playground"

            await browser.close()
    finally:
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except TimeoutError:
                process.kill()
                await process.wait()
