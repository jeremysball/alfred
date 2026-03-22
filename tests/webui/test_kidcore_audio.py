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
INDEX_HTML = PROJECT_ROOT / "src/alfred/interfaces/webui/static/index.html"
MAIN_JS = PROJECT_ROOT / "src/alfred/interfaces/webui/static/js/main.js"


def test_audio_manager_exposes_separate_music_and_sfx_controls() -> None:
    assert AUDIO_MANAGER.exists(), "audio-manager.js is missing"

    source = AUDIO_MANAGER.read_text()

    assert "class KidcoreAudioManager" in source
    assert "startMusic" in source
    assert "stopMusic" in source
    assert "setMusicMuted" in source
    assert "setSfxMuted" in source
    assert "muteMusic" in source
    assert "toggleSfxMute" in source
    assert "playEffect" in source
    assert "autoplay" not in source.lower()


def test_index_includes_kidcore_audio_controls_and_scripts() -> None:
    source = INDEX_HTML.read_text()

    assert "/static/js/audio-manager.js?v=3" in source
    assert "/static/js/kidcore-homeboard.js?v=3" in source
    assert "kidcore-audio-controls" in source
    assert 'id="kidcore-music-play"' in source
    assert 'id="kidcore-music-mute"' in source
    assert 'id="kidcore-sfx-toggle"' in source
    assert "kidcore-homeboard" in source


def test_main_wires_kidcore_audio_to_core_interactions() -> None:
    source = MAIN_JS.read_text()

    assert "kidcoreAudioManager" in source
    assert "playKidcoreSend()" in source
    assert "playKidcoreSuccess()" in source
    assert "playKidcoreError()" in source
    assert "playKidcoreClick()" in source
    assert "kidcoreMusicPlayButton" in source
    assert "kidcoreSfxToggleButton" in source


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


@pytest.mark.slow
@pytest.mark.asyncio
async def test_kidcore_audio_controls_toggle_music_and_sfx_independently() -> None:
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

            await page.evaluate(
                """
                () => {
                  const audio = window.kidcoreAudioManager;
                  window.__kidcoreAudioCalls = {
                    startMusic: 0,
                    muteMusic: 0,
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

            await page.click("#kidcore-music-play")
            await page.wait_for_timeout(100)
            await page.locator("#message-input").fill("glitter check")
            await page.click("#send-button")
            await page.wait_for_timeout(100)
            await page.click("#kidcore-sfx-toggle")
            await page.wait_for_timeout(100)
            await page.click("#kidcore-music-mute")
            await page.wait_for_timeout(100)

            data = await page.evaluate(
                """
                () => ({
                  theme: document.documentElement.getAttribute('data-theme'),
                  calls: window.__kidcoreAudioCalls,
                  musicMuted: window.kidcoreAudioManager.isMusicMuted,
                  sfxMuted: window.kidcoreAudioManager.isSfxMuted,
                  musicPlaying: window.kidcoreAudioManager.isMusicPlaying,
                  musicStatus: document.getElementById('kidcore-music-status')?.textContent || '',
                  sfxStatus: document.getElementById('kidcore-sfx-status')?.textContent || '',
                  musicState: document.querySelector('.kidcore-audio-controls')?.dataset.musicState || '',
                  sfxState: document.querySelector('.kidcore-audio-controls')?.dataset.sfxState || '',
                  playButtonText: document.querySelector('#kidcore-sfx-toggle')?.textContent || '',
                })
                """
            )

            assert data["theme"] == "kidcore-playground"
            assert data["calls"]["startMusic"] == 1
            assert data["calls"]["muteMusic"] == 1
            assert data["calls"]["playClick"] >= 2
            assert data["calls"]["playSend"] == 1
            assert data["musicMuted"] is True
            assert data["sfxMuted"] is True
            assert data["musicPlaying"] is False
            assert data["musicStatus"] == "Muted"
            assert data["sfxStatus"] == "Muted"
            assert data["musicState"] == "muted"
            assert data["sfxState"] == "muted"
            assert "Off" in data["playButtonText"]

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
            await page.add_init_script("localStorage.setItem('alfred-theme', 'dark-academia');")
            await page.goto(
                f"http://127.0.0.1:{port}/static/index.html",
                wait_until="networkidle",
            )

            data = await page.evaluate(
                """
                () => {
                  const controls = document.querySelector('.kidcore-audio-controls');
                  const styles = controls ? getComputedStyle(controls) : null;
                  const homeboard = document.querySelector('#kidcore-homeboard');
                  const homeboardStyle = homeboard ? getComputedStyle(homeboard) : null;
                  return {
                    theme: document.documentElement.getAttribute('data-theme'),
                    controlsDisplay: styles?.display || null,
                    controlsVisibility: styles?.visibility || null,
                    controlsOffsetParent: Boolean(controls?.offsetParent),
                    homeboardDisplay: homeboardStyle?.display || null,
                    homeboardOffsetParent: Boolean(homeboard?.offsetParent),
                  };
                }
                """
            )

            assert data["theme"] == "dark-academia"
            assert data["controlsDisplay"] == "none"
            assert data["controlsOffsetParent"] is False
            assert data["homeboardDisplay"] == "none"
            assert data["homeboardOffsetParent"] is False

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
async def test_kidcore_streaming_chunks_bounce_and_sound() -> None:
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

            await page.evaluate(
                """
                () => {
                  const audio = window.kidcoreAudioManager;
                  window.__kidcoreAudioCalls = {
                    playChunk: 0,
                    playMessageComplete: 0,
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

            await page.locator("#message-input").fill("glue shimmer")
            await page.click("#send-button")
            await page.wait_for_timeout(50)

            await page.evaluate(
                """
                () => {
                  window.__alfredWebUI.emitMessage({ type: 'chat.started' });
                  window.__alfredWebUI.emitMessage({
                    type: 'chat.chunk',
                    payload: { content: 'glue ' },
                  });
                  window.__alfredWebUI.emitMessage({
                    type: 'chat.chunk',
                    payload: { content: 'shimmer' },
                  });
                }
                """
            )

            during_stream = await page.evaluate(
                """
                () => {
                  const assistant = document.querySelector('chat-message.glue-shimmer');
                  const bubble = assistant?.querySelector('.message-bubble');
                  return {
                    theme: document.documentElement.getAttribute('data-theme'),
                    calls: window.__kidcoreAudioCalls,
                    hasAssistant: Boolean(assistant),
                    hasGlueClass: Boolean(assistant?.classList.contains('glue-shimmer')),
                    bubbleText: bubble?.textContent || '',
                    animationName: bubble ? getComputedStyle(bubble).animationName : '',
                  };
                }
                """
            )

            assert during_stream["theme"] == "kidcore-playground"
            assert during_stream["calls"]["playSend"] == 1
            assert during_stream["calls"]["playChunk"] == 2
            assert during_stream["hasAssistant"] is True
            assert during_stream["hasGlueClass"] is True
            assert "glue shimmer" in during_stream["bubbleText"].lower()
            assert during_stream["animationName"] != "none"

            await page.evaluate(
                """
                () => {
                  window.__alfredWebUI.emitMessage({ type: 'chat.complete' });
                }
                """
            )
            await page.wait_for_timeout(50)

            done = await page.evaluate(
                """
                () => ({
                  calls: window.__kidcoreAudioCalls,
                  assistantStillStreaming: Boolean(document.querySelector('chat-message.glue-shimmer.streaming')),
                  readyText: document.getElementById('kidcore-music-status')?.textContent || '',
                })
                """
            )

            assert done["calls"]["playMessageComplete"] == 1
            assert done["assistantStillStreaming"] is False
            assert done["readyText"] in {"Ready", "Playing", "Muted"}

            await browser.close()
    finally:
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except TimeoutError:
                process.kill()
                await process.wait()


def test_audio_manager_uses_web_audio_and_special_effect_files() -> None:
    source = AUDIO_MANAGER.read_text()

    assert "AudioContext" in source or "webkitAudioContext" in source
    assert "playChunk" in source
    assert "playMessageComplete" in source
    assert "setMusicMuted" in source
    assert "setSfxMuted" in source
    assert "success.mp3" in source
    assert "error.mp3" in source
