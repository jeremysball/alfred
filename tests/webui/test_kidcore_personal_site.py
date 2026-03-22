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
THEME_CSS = PROJECT_ROOT / "src/alfred/interfaces/webui/static/css/themes/kidcore-homeboard.css"


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


def test_kidcore_source_exposes_fake_personal_site_panels() -> None:
    index_source = INDEX_HTML.read_text()
    theme_source = THEME_CSS.read_text()

    assert "kidcore-banner" not in index_source
    assert "kidcore-homeboard" in index_source
    assert "kidcore-guestbook-panel" in index_source
    assert "kidcore-webring-panel" in index_source
    assert "kidcore-links-panel" in index_source
    assert "kidcore-updates-panel" in index_source
    assert "kidcore-homeboard-search" in index_source
    assert "kidcore-homeboard-export" in index_source
    assert "kidcore-sfx-toggle" in index_source
    assert "kidcore-music-play" in index_source
    assert "kidcore-music-mute" in index_source

    for selector in [
        '[data-theme="kidcore-playground"] .kidcore-homeboard',
        '[data-theme="kidcore-playground"] .kidcore-homeboard-tabs',
        '[data-theme="kidcore-playground"] .kidcore-homeboard-toolbar',
        '[data-theme="kidcore-playground"] .kidcore-homeboard-panel',
        '[data-theme="kidcore-playground"] .kidcore-homeboard-panel.active',
        '[data-theme="kidcore-playground"] .kidcore-guestbook-entry',
        '[data-theme="kidcore-playground"] .kidcore-webring-card',
        '[data-theme="kidcore-playground"] .kidcore-link-card',
        '[data-theme="kidcore-playground"] .kidcore-updates-panel',
        '[data-theme="kidcore-playground"] .kidcore-sfx-toggle',
    ]:
        assert selector in theme_source


@pytest.mark.asyncio
async def test_kidcore_homeboard_tabs_switch_between_fake_panels() -> None:
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

            await page.click('[data-kidcore-tab="guestbook"]')
            await page.wait_for_timeout(120)
            guestbook = await page.evaluate(
                """
                () => {
                  const panel = document.getElementById('kidcore-guestbook-panel');
                  const firstEntry = panel?.querySelector('.kidcore-guestbook-entry .kidcore-entry-message');
                  return {
                    active: panel?.classList.contains('active') || false,
                    hidden: panel ? panel.hidden : true,
                    text: firstEntry?.textContent || '',
                  };
                }
                """
            )
            assert guestbook["active"] is True
            assert guestbook["hidden"] is False
            assert guestbook["text"]

            await page.click('[data-kidcore-tab="webring"]')
            await page.wait_for_timeout(120)
            webring = await page.evaluate(
                """
                () => {
                  const panel = document.getElementById('kidcore-webring-panel');
                  return {
                    active: panel?.classList.contains('active') || false,
                    hidden: panel ? panel.hidden : true,
                    title: document.getElementById('kidcore-webring-title')?.textContent || '',
                    description: document.getElementById('kidcore-webring-description')?.textContent || '',
                  };
                }
                """
            )
            assert webring["active"] is True
            assert webring["hidden"] is False
            assert webring["title"]
            assert webring["description"]

            await page.click('[data-kidcore-tab="links"]')
            await page.wait_for_timeout(120)
            links = await page.evaluate(
                """
                () => {
                  const panel = document.getElementById('kidcore-links-panel');
                  return {
                    active: panel?.classList.contains('active') || false,
                    hidden: panel ? panel.hidden : true,
                    title: document.getElementById('kidcore-links-title')?.textContent || '',
                    url: document.getElementById('kidcore-links-url')?.textContent || '',
                    buttons: Array.from(document.querySelectorAll('[data-kidcore-link]')).length,
                  };
                }
                """
            )
            assert links["active"] is True
            assert links["hidden"] is False
            assert links["title"]
            assert links["url"]
            assert links["buttons"] >= 3

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
async def test_kidcore_guestbook_persists_entries_in_local_storage() -> None:
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
                  localStorage.removeItem('alfred-kidcore-guestbook');
                  localStorage.removeItem('alfred-kidcore-homeboard');
                }
                """
            )
            await page.reload(wait_until="networkidle")
            await page.click('[data-kidcore-tab="guestbook"]')
            await page.fill("#kidcore-guestbook-name", "Moonbeam")
            await page.fill("#kidcore-guestbook-message", "hello from the glitter pond")
            await page.click("#kidcore-guestbook-submit")
            await page.wait_for_timeout(120)

            signed = await page.evaluate(
                """
                () => ({
                  entries: Array.from(document.querySelectorAll('#kidcore-guestbook-entries .kidcore-entry-message'))
                    .map((node) => node.textContent || ''),
                  storage: localStorage.getItem('alfred-kidcore-guestbook') || '',
                })
                """
            )

            assert any("hello from the glitter pond" in entry for entry in signed["entries"])
            assert "Moonbeam" in signed["storage"]
            assert "hello from the glitter pond" in signed["storage"]

            await page.reload(wait_until="networkidle")
            await page.click('[data-kidcore-tab="guestbook"]')
            await page.wait_for_timeout(120)
            persisted = await page.evaluate(
                """
                () => Array.from(document.querySelectorAll('#kidcore-guestbook-entries .kidcore-entry-message'))
                  .map((node) => node.textContent || '')
                """
            )
            assert any("hello from the glitter pond" in entry for entry in persisted)

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
async def test_kidcore_music_and_sfx_controls_are_independent() -> None:
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

            await page.click("#kidcore-music-play")
            await page.wait_for_timeout(120)
            music_started = await page.evaluate(
                """
                () => ({
                  musicPlaying: window.kidcoreAudioManager?.isMusicPlaying ?? false,
                  musicMuted: window.kidcoreAudioManager?.isMusicMuted ?? true,
                  sfxMuted: window.kidcoreAudioManager?.isSfxMuted ?? true,
                  musicStatus: document.getElementById('kidcore-music-status')?.textContent || '',
                  sfxStatus: document.getElementById('kidcore-sfx-status')?.textContent || '',
                })
                """
            )
            assert music_started["musicPlaying"] is True
            assert music_started["musicMuted"] is False
            assert music_started["sfxMuted"] is False
            assert music_started["musicStatus"]
            assert music_started["sfxStatus"]

            await page.click("#kidcore-sfx-toggle")
            await page.wait_for_timeout(120)
            muted_sfx = await page.evaluate(
                """
                () => ({
                  musicPlaying: window.kidcoreAudioManager?.isMusicPlaying ?? false,
                  musicMuted: window.kidcoreAudioManager?.isMusicMuted ?? true,
                  sfxMuted: window.kidcoreAudioManager?.isSfxMuted ?? false,
                  musicState: document.querySelector('.kidcore-audio-controls')?.dataset.musicState || '',
                  sfxState: document.querySelector('.kidcore-audio-controls')?.dataset.sfxState || '',
                })
                """
            )
            assert muted_sfx["musicPlaying"] is True
            assert muted_sfx["musicMuted"] is False
            assert muted_sfx["sfxMuted"] is True
            assert muted_sfx["musicState"] == "playing"
            assert muted_sfx["sfxState"] == "muted"

            await page.click("#kidcore-music-mute")
            await page.wait_for_timeout(120)
            music_muted = await page.evaluate(
                """
                () => ({
                  musicPlaying: window.kidcoreAudioManager?.isMusicPlaying ?? true,
                  musicMuted: window.kidcoreAudioManager?.isMusicMuted ?? false,
                  sfxMuted: window.kidcoreAudioManager?.isSfxMuted ?? false,
                  musicState: document.querySelector('.kidcore-audio-controls')?.dataset.musicState || '',
                  sfxState: document.querySelector('.kidcore-audio-controls')?.dataset.sfxState || '',
                })
                """
            )
            assert music_muted["musicPlaying"] is False
            assert music_muted["musicMuted"] is True
            assert music_muted["sfxMuted"] is True
            assert music_muted["musicState"] == "muted"
            assert music_muted["sfxState"] == "muted"

            await browser.close()
    finally:
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except TimeoutError:
                process.kill()
                await process.wait()
