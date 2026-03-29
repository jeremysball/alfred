from __future__ import annotations

import asyncio
import socket
import time
import urllib.request
from threading import Thread
from typing import cast
from unittest.mock import AsyncMock, patch

import pytest
import uvicorn
from playwright.async_api import async_playwright

from alfred.interfaces.webui.server import create_app
from tests.webui.fakes import FakeAlfred


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
@pytest.mark.slow
async def test_browser_context_viewer_renders_truthful_section_counts() -> None:
    port = _find_free_port()
    fake_alfred = FakeAlfred()
    first_context_data = {
        "system_prompt": {
            "sections": [{"id": "system", "name": "SYSTEM.md", "label": "SYSTEM.md", "tokens": 12}],
            "total_tokens": 12,
        },
        "blocked_context_files": ["SOUL.md"],
        "conflicted_context_files": [
            {
                "id": "soul",
                "name": "soul",
                "label": "SOUL.md",
                "reason": "Conflicted managed template SOUL.md is blocked",
            }
        ],
        "disabled_sections": ["TOOLS"],
        "warnings": [],
        "memories": {"displayed": 0, "total": 0, "items": [], "tokens": 0},
        "session_history": {
            "count": 2,
            "displayed": 2,
            "included": 2,
            "total": 2,
            "messages": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
            ],
            "tokens": 6,
        },
        "tool_calls": {"count": 0, "items": [], "tokens": 0},
        "total_tokens": 12,
    }
    second_context_data = {
        "system_prompt": {
            "sections": [{"id": "system", "name": "SYSTEM.md", "label": "SYSTEM.md", "tokens": 12}],
            "total_tokens": 12,
        },
        "blocked_context_files": ["SOUL.md"],
        "conflicted_context_files": [
            {
                "id": "soul",
                "name": "soul",
                "label": "SOUL.md",
                "reason": "Conflicted managed template SOUL.md is blocked",
            }
        ],
        "disabled_sections": ["TOOLS"],
        "warnings": [],
        "memories": {"displayed": 0, "total": 0, "items": [], "tokens": 0},
        "session_history": {
            "count": 2,
            "displayed": 2,
            "included": 5,
            "total": 8,
            "messages": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
            ],
            "tokens": 6,
        },
        "tool_calls": {"count": 0, "items": [], "tokens": 0},
        "total_tokens": 12,
    }

    config = uvicorn.Config(
        create_app(alfred_instance=fake_alfred, debug=True),
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    thread = Thread(target=server.run, daemon=True)
    thread.start()

    try:
        await _wait_for_server(port)

        with patch(
            "alfred.context_display.get_context_display",
            AsyncMock(side_effect=[first_context_data, second_context_data]),
        ):
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch()
                page = await browser.new_page(viewport={"width": 1440, "height": 900})
                await page.goto(f"http://127.0.0.1:{port}/static/index.html", wait_until="domcontentloaded")

                await page.wait_for_function(
                    "() => document.querySelector('#connection-pill')?.classList.contains('connected')",
                    timeout=10000,
                )

                await page.fill('#message-input', '/context')
                await page.click('#send-button')
                await page.wait_for_function(
                    "() => document.querySelectorAll('context-viewer').length === 1",
                    timeout=10000,
                )

                first_viewer = page.locator('context-viewer').last
                conflicted_files = first_viewer.locator('.context-conflicted-files')
                system_header = first_viewer.locator('.context-section-header[data-section="system-prompt"]')
                system_badge = system_header.locator('.section-badge')
                session_badge = first_viewer.locator('.context-section-header[data-section="session-history"] .section-badge')
                enabled_sections = first_viewer.locator('.system-section-item.enabled')
                disabled_sections = first_viewer.locator('.system-section-item.disabled')

                await conflicted_files.wait_for(state='attached', timeout=10000)
                await system_header.click()
                await enabled_sections.first.wait_for(state='attached', timeout=10000)
                await disabled_sections.first.wait_for(state='attached', timeout=10000)

                assert (await system_badge.text_content() or "").strip() == "1 active / 1 disabled"
                assert (await session_badge.text_content() or "").strip() == "2 messages"
                assert await enabled_sections.count() == 1
                assert await disabled_sections.count() == 1

                enabled_text = await enabled_sections.first.text_content()
                disabled_text = await disabled_sections.first.text_content()
                conflicted_text = await conflicted_files.text_content()

                assert enabled_text is not None and "SYSTEM.md" in enabled_text
                assert disabled_text is not None and "TOOLS.md" in disabled_text
                assert conflicted_text is not None
                assert "Conflicted Managed Templates" in conflicted_text
                assert "SOUL.md" in conflicted_text
                assert "Conflicted managed template SOUL.md is blocked" in conflicted_text

                await page.fill('#message-input', '/context')
                await page.click('#send-button')
                await page.wait_for_function(
                    "() => document.querySelectorAll('context-viewer').length === 2",
                    timeout=10000,
                )

                second_viewer = page.locator('context-viewer').last
                second_system_badge = second_viewer.locator(
                    '.context-section-header[data-section="system-prompt"] .section-badge'
                )
                second_session_badge = second_viewer.locator(
                    '.context-section-header[data-section="session-history"] .section-badge'
                )

                assert (await second_system_badge.text_content() or "").strip() == "1 active / 1 disabled"
                assert (await second_session_badge.text_content() or "").strip() == "2 displayed / 5 included / 8 total messages"
                await browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)


@pytest.mark.asyncio
@pytest.mark.slow
async def test_browser_context_viewer_shows_compact_tool_outcomes() -> None:
    port = _find_free_port()
    fake_alfred = FakeAlfred()
    context_data = {
        "system_prompt": {"sections": [], "total_tokens": 0},
        "blocked_context_files": [],
        "conflicted_context_files": [],
        "disabled_sections": [],
        "warnings": [],
        "memories": {"displayed": 0, "total": 0, "items": [], "tokens": 0},
        "session_history": {
            "count": 0,
            "displayed": 0,
            "included": 0,
            "total": 0,
            "messages": [],
            "tokens": 0,
        },
        "tool_calls": {
            "count": 2,
            "displayed": 2,
            "total": 2,
            "items": [
                {
                    "tool_name": "bash",
                    "summary": "bash: python -V exited 0 — Python 3.14.3",
                    "tokens": 8,
                    "status": "success",
                    "arguments": {"command": "python -V"},
                    "output": "RAW_TOOL_OUTPUT_SHOULD_NOT_SHOW",
                },
                {
                    "tool_name": "write",
                    "summary": "write: created tests/module_test.py",
                    "tokens": 4,
                    "status": "success",
                    "arguments": {"path": "tests/module_test.py"},
                    "output": "RAW_WRITE_OUTPUT_SHOULD_NOT_SHOW",
                },
            ],
            "tokens": 12,
            "all_shown": True,
        },
        "total_tokens": 12,
    }

    config = uvicorn.Config(
        create_app(alfred_instance=fake_alfred, debug=True),
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    thread = Thread(target=server.run, daemon=True)
    thread.start()

    try:
        await _wait_for_server(port)

        with patch("alfred.context_display.get_context_display", AsyncMock(return_value=context_data)):
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch()
                page = await browser.new_page(viewport={"width": 1440, "height": 900})
                await page.goto(f"http://127.0.0.1:{port}/static/index.html", wait_until="domcontentloaded")

                await page.wait_for_function(
                    "() => document.querySelector('#connection-pill')?.classList.contains('connected')",
                    timeout=10000,
                )

                await page.fill('#message-input', '/context')
                await page.click('#send-button')
                await page.wait_for_function(
                    "() => document.querySelectorAll('context-viewer').length === 1",
                    timeout=10000,
                )

                viewer = page.locator('context-viewer').last
                tool_header = viewer.locator('.context-section-header[data-section="tool-calls"]')
                tool_items = viewer.locator('.tool-call-item')
                tool_summaries = viewer.locator('.tool-summary')
                tool_arguments = viewer.locator('.tool-arguments')
                tool_outputs = viewer.locator('.tool-output')

                await tool_header.click()
                await tool_items.first.wait_for(state='attached', timeout=10000)

                assert await tool_items.count() == 2
                assert await tool_summaries.count() == 2
                assert await tool_arguments.count() == 0
                assert await tool_outputs.count() == 0

                tool_text = await viewer.locator('.tool-calls-list').text_content()
                assert tool_text is not None
                assert 'bash: python -V exited 0' in tool_text
                assert 'write: created tests/module_test.py' in tool_text
                assert 'RAW_TOOL_OUTPUT_SHOULD_NOT_SHOW' not in tool_text
                assert 'RAW_WRITE_OUTPUT_SHOULD_NOT_SHOW' not in tool_text
                assert 'command:' not in tool_text
                assert 'path:' not in tool_text
                await browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)


@pytest.mark.asyncio
@pytest.mark.slow
async def test_browser_context_viewer_toggles_sections_and_refreshes() -> None:
    port = _find_free_port()
    fake_alfred = FakeAlfred()
    first_context_data = {
        "system_prompt": {
            "sections": [
                {"id": "system", "name": "SYSTEM.md", "label": "SYSTEM.md", "tokens": 12},
                {"id": "agents", "name": "AGENTS.md", "label": "AGENTS.md", "tokens": 18},
            ],
            "total_tokens": 30,
        },
        "blocked_context_files": [],
        "conflicted_context_files": [],
        "disabled_sections": [],
        "warnings": [],
        "memories": {"displayed": 0, "total": 0, "items": [], "tokens": 0},
        "session_history": {
            "count": 0,
            "displayed": 0,
            "included": 0,
            "total": 0,
            "messages": [],
            "tokens": 0,
        },
        "tool_calls": {"count": 0, "displayed": 0, "total": 0, "items": [], "tokens": 0},
        "total_tokens": 30,
    }
    second_context_data = {
        "system_prompt": {
            "sections": [
                {"id": "agents", "name": "AGENTS.md", "label": "AGENTS.md", "tokens": 18},
            ],
            "total_tokens": 18,
        },
        "blocked_context_files": [],
        "conflicted_context_files": [],
        "disabled_sections": ["SYSTEM"],
        "warnings": ["Disabled sections: SYSTEM"],
        "memories": {"displayed": 0, "total": 0, "items": [], "tokens": 0},
        "session_history": {
            "count": 0,
            "displayed": 0,
            "included": 0,
            "total": 0,
            "messages": [],
            "tokens": 0,
        },
        "tool_calls": {"count": 0, "displayed": 0, "total": 0, "items": [], "tokens": 0},
        "total_tokens": 18,
    }

    config = uvicorn.Config(
        create_app(alfred_instance=fake_alfred, debug=True),
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    thread = Thread(target=server.run, daemon=True)
    thread.start()

    try:
        await _wait_for_server(port)

        with patch(
            "alfred.context_display.get_context_display",
            AsyncMock(side_effect=[first_context_data, second_context_data]),
        ):
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch()
                page = await browser.new_page(viewport={"width": 1440, "height": 900})
                await page.goto(f"http://127.0.0.1:{port}/static/index.html", wait_until="domcontentloaded")

                await page.wait_for_function(
                    "() => document.querySelector('#connection-pill')?.classList.contains('connected')",
                    timeout=10000,
                )

                await page.fill('#message-input', '/context')
                await page.click('#send-button')
                await page.wait_for_function(
                    "() => document.querySelectorAll('context-viewer').length === 1",
                    timeout=10000,
                )

                first_viewer = page.locator('context-viewer').last
                first_system_header = first_viewer.locator('.context-section-header[data-section="system-prompt"]')
                await first_system_header.click()

                first_system_badge = first_viewer.locator(
                    '.context-section-header[data-section="system-prompt"] .section-badge'
                )
                first_system_checkbox = first_viewer.locator('input.context-toggle[data-section="system"]')
                first_enabled_sections = first_viewer.locator('.system-section-item.enabled')
                first_disabled_sections = first_viewer.locator('.system-section-item.disabled')

                await first_system_checkbox.wait_for(state='attached', timeout=10000)
                assert await first_system_checkbox.is_checked()
                assert (await first_system_badge.text_content() or '').strip() == '2 active / 0 disabled'
                assert await first_enabled_sections.count() == 2
                assert await first_disabled_sections.count() == 0

                await first_system_checkbox.evaluate("(el) => el.click()")
                await page.wait_for_function(
                    "() => document.querySelectorAll('context-viewer').length === 2",
                    timeout=10000,
                )

                second_viewer = page.locator('context-viewer').last
                second_system_header = second_viewer.locator('.context-section-header[data-section="system-prompt"]')
                await second_system_header.click()

                second_system_badge = second_viewer.locator(
                    '.context-section-header[data-section="system-prompt"] .section-badge'
                )
                second_system_checkbox = second_viewer.locator('input.context-toggle[data-section="system"]')
                second_enabled_sections = second_viewer.locator('.system-section-item.enabled')
                second_disabled_sections = second_viewer.locator('.system-section-item.disabled')

                await second_system_checkbox.wait_for(state='attached', timeout=10000)
                assert not await second_system_checkbox.is_checked()
                assert (await second_system_badge.text_content() or '').strip() == '1 active / 1 disabled'
                assert await second_enabled_sections.count() == 1
                assert await second_disabled_sections.count() == 1

                disabled_name = second_disabled_sections.first.locator('.section-name')
                assert (await disabled_name.text_content() or '').strip() == 'SYSTEM.md'
                await browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
