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
AUDIO_MANAGER = PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/audio-manager.js"


def test_audio_manager_exists_and_requires_explicit_start() -> None:
    assert AUDIO_MANAGER.exists(), "audio-manager.js is missing"

    source = AUDIO_MANAGER.read_text()

    assert "class KidcoreAudioManager" in source
    assert "startMusic" in source
    assert "stopMusic" in source
    assert "mute" in source or "setMuted" in source
    assert "playEffect" in source
    assert "autoplay" not in source.lower()


def test_index_includes_kidcore_audio_controls_and_script() -> None:
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/index.html").read_text()

    assert '/static/js/audio-manager.js?v=3' in source
    assert 'kidcore-audio-controls' in source
    assert 'id="kidcore-audio-play"' in source
    assert 'id="kidcore-audio-mute"' in source


def test_main_wires_kidcore_audio_to_core_interactions() -> None:
    source = (PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/main.js").read_text()

    assert "kidcoreAudioManager" in source
    assert "playKidcoreSend()" in source
    assert "playKidcoreSuccess()" in source
    assert "playKidcoreError()" in source
    assert "playKidcoreClick()" in source


def test_kidcore_audio_assets_exist() -> None:
    audio_dir = PROJECT_ROOT / "src/alfred/interfaces/webui/static/audio"
    assert audio_dir.exists(), "audio directory is missing"

    for filename in [
        "kidcore-loop.mp3",
        "click.mp3",
        "send.mp3",
        "success.mp3",
        "error.mp3",
    ]:
        assert (audio_dir / filename).exists(), f"Missing kidcore audio asset: {filename}"


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
async def test_kidcore_audio_browser_controls_work() -> None:
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
            await page.add_init_script(
                "localStorage.setItem('alfred-theme', 'kidcore-playground');"
            )
            await page.goto(
                f"http://127.0.0.1:{port}/static/index.html",
                wait_until="networkidle",
            )

            await page.evaluate(
                """
                () => {
                  const audio = window.kidcoreAudioManager;
                  window.__kidcoreAudioCalls = {
                    startMusic: 0,
                    mute: 0,
                    playClick: 0,
                    playSend: 0,
                  };

                  for (const method of Object.keys(window.__kidcoreAudioCalls)) {
                    const original = audio[method].bind(audio);
                    audio[method] = (...args) => {
                      window.__kidcoreAudioCalls[method] += 1;
                      return original(...args);
                    };
                  }
                }
                """
            )

            await page.click('#kidcore-audio-play')
            await page.wait_for_timeout(100)

            started = await page.evaluate(
                """
                () => ({
                  isMuted: window.kidcoreAudioManager.isMuted,
                  isMusicPlaying: window.kidcoreAudioManager.isMusicPlaying,
                  calls: window.__kidcoreAudioCalls,
                })
                """
            )
            assert started["calls"]["startMusic"] == 1
            assert started["calls"]["playClick"] == 1
            assert started["isMuted"] is False
            assert started["isMusicPlaying"] is True

            await page.locator('#message-input').fill('glitter check')
            await page.click('#send-button')
            await page.wait_for_timeout(100)

            await page.click('#kidcore-audio-mute')
            await page.wait_for_timeout(100)

            data = await page.evaluate(
                """
                () => {
                  const messages = Array.from(
                    document.querySelectorAll('.message.user .message-content'),
                    (node) => node.textContent || ''
                  );
                  return {
                    theme: document.documentElement.getAttribute('data-theme'),
                    calls: window.__kidcoreAudioCalls,
                    isMuted: window.kidcoreAudioManager.isMuted,
                    isMusicPlaying: window.kidcoreAudioManager.isMusicPlaying,
                    userMessages: messages,
                    messageCount: document.querySelectorAll('.message.user').length,
                  };
                }
                """
            )

            assert data["theme"] == "kidcore-playground"
            assert data["calls"]["mute"] == 1
            assert data["calls"]["playClick"] == 2
            assert data["calls"]["playSend"] == 1
            assert data["isMuted"] is True
            assert data["isMusicPlaying"] is False
            assert "glitter check" in data["userMessages"]
            assert data["messageCount"] >= 1

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
async def test_kidcore_audio_controls_hide_outside_kidcore_theme() -> None:
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
            await page.add_init_script(
                "localStorage.setItem('alfred-theme', 'dark-academia');"
            )
            await page.goto(
                f"http://127.0.0.1:{port}/static/index.html",
                wait_until="networkidle",
            )

            data = await page.evaluate(
                """
                () => {
                  const controls = document.querySelector('.kidcore-audio-controls');
                  const styles = controls ? getComputedStyle(controls) : null;
                  return {
                    theme: document.documentElement.getAttribute('data-theme'),
                    exists: Boolean(controls),
                    display: styles?.display || null,
                    visibility: styles?.visibility || null,
                    offsetParent: Boolean(controls?.offsetParent),
                  };
                }
                """
            )

            assert data["theme"] == "dark-academia"
            assert data["exists"] is True
            assert data["display"] == "none"
            assert data["offsetParent"] is False

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
async def test_kidcore_audio_play_resumes_after_mute() -> None:
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
            await page.add_init_script(
                "localStorage.setItem('alfred-theme', 'kidcore-playground');"
            )
            await page.goto(
                f"http://127.0.0.1:{port}/static/index.html",
                wait_until="networkidle",
            )

            await page.evaluate(
                """
                () => {
                  const audio = window.kidcoreAudioManager;
                  window.__kidcoreAudioCalls = {
                    startMusic: 0,
                    mute: 0,
                    playClick: 0,
                    playSend: 0,
                  };

                  for (const method of Object.keys(window.__kidcoreAudioCalls)) {
                    const original = audio[method].bind(audio);
                    audio[method] = (...args) => {
                      window.__kidcoreAudioCalls[method] += 1;
                      return original(...args);
                    };
                  }
                }
                """
            )

            await page.click('#kidcore-audio-play')
            await page.wait_for_timeout(100)
            await page.click('#kidcore-audio-mute')
            await page.wait_for_timeout(100)
            await page.click('#kidcore-audio-play')
            await page.wait_for_timeout(100)

            data = await page.evaluate(
                """
                () => ({
                  theme: document.documentElement.getAttribute('data-theme'),
                  calls: window.__kidcoreAudioCalls,
                  isMuted: window.kidcoreAudioManager.isMuted,
                  isMusicPlaying: window.kidcoreAudioManager.isMusicPlaying,
                  playButtonText: document.querySelector('#kidcore-audio-play')?.textContent || '',
                  muteButtonText: document.querySelector('#kidcore-audio-mute')?.textContent || '',
                })
                """
            )

            assert data["theme"] == "kidcore-playground"
            assert data["calls"]["startMusic"] == 2
            assert data["calls"]["mute"] == 1
            assert data["isMuted"] is False
            assert data["isMusicPlaying"] is True
            assert "Play" in data["playButtonText"]
            assert "Mute" in data["muteButtonText"]

            await browser.close()
    finally:
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except TimeoutError:
                process.kill()
                await process.wait()
