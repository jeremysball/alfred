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
async def test_browser_context_viewer_preserves_scroll_when_toggling_tool_activity() -> None:
    port = _find_free_port()
    fake_alfred = FakeAlfred()
    long_memory = (
        "Remember that the context sheet should use the same panel language as the rest of the UI, "
        "and that long content must stay readable without ellipses or clipped cards."
    )
    long_session_message = (
        "The session preview needs to tell the truth about what is shown, what is included, and what is total. "
        "The user should not have to guess whether the sheet is hiding anything."
    )
    long_tool_output = (
        "Line one of output\n"
        "Line two of output with a little more detail\n"
        "Line three of output that would normally be truncated in a cramped sheet."
    )
    context_data = {
        "system_prompt": {
            "sections": [
                {"id": "system", "name": "SYSTEM.md", "label": "SYSTEM.md", "tokens": 12},
                {"id": "agents", "name": "AGENTS.md", "label": "AGENTS.md", "tokens": 18},
            ],
            "total_tokens": 30,
        },
        "blocked_context_files": [],
        "conflicted_context_files": [],
        "disabled_sections": ["TOOLS"],
        "warnings": [],
        "memories": {
            "displayed": 2,
            "total": 2,
            "displayed_tokens": 34,
            "items": [
                {
                    "content": long_memory,
                    "preview": long_memory[:120],
                    "role": "user",
                    "timestamp": "2026-03-29",
                    "tokens": 34,
                },
                {
                    "content": "A second memory that confirms the sheet should keep full output visible.",
                    "preview": "A second memory that confirms the sheet should keep full output visible.",
                    "role": "assistant",
                    "timestamp": "2026-03-29",
                    "tokens": 17,
                },
            ],
            "tokens": 51,
            "all_shown": True,
        },
        "session_history": {
            "count": 2,
            "displayed": 2,
            "displayed_tokens": 30,
            "included": 5,
            "included_tokens": 78,
            "total": 8,
            "messages": [
                {"role": "user", "content": long_session_message},
                {"role": "assistant", "content": "A short acknowledgement that still needs to be visible."},
            ],
            "tokens": 78,
        },
        "self_model": {
            "identity": {"name": "Alfred", "role": "Assistant"},
            "runtime": {"interface": "cli", "session_id": "browser-session", "daemon_mode": False},
            "capabilities": {"memory_enabled": True, "search_enabled": True, "tools_count": 4, "tools": ["read", "write", "bash"]},
            "context_pressure": {"message_count": 8, "memory_count": 2, "approximate_tokens": 482},
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
                    "output": long_tool_output,
                },
                {
                    "tool_name": "write",
                    "summary": "write: created tests/module_test.py",
                    "tokens": 4,
                    "status": "success",
                    "arguments": {"path": "tests/module_test.py"},
                    "output": "Created tests/module_test.py successfully.",
                },
            ],
            "tokens": 12,
            "displayed_tokens": 12,
            "all_shown": True,
        },
        "total_tokens": 171,
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

                await page.evaluate(
                    """
                    () => {
                      document.documentElement.setAttribute('data-theme', 'spacejam-neocities');
                    }
                    """
                )

                await page.fill('#message-input', '/context')
                await page.click('#send-button')
                await page.wait_for_function(
                    "() => document.querySelectorAll('context-viewer').length === 1",
                    timeout=10000,
                )

                viewer = page.locator('context-viewer').last.locator('.context-viewer')
                tool_section_header = page.locator(
                    'context-viewer .context-section-header[data-section="tool-calls"]'
                )

                await page.evaluate(
                    """
                    () => {
                      document.querySelector('context-viewer .context-section-header[data-section="memories"]')?.click();
                    }
                    """
                )
                await page.evaluate(
                    """
                    () => {
                      document.querySelector('context-viewer .context-section-header[data-section="session-history"]')?.click();
                    }
                    """
                )
                await tool_section_header.evaluate("(element) => element.click()")

                await page.wait_for_function(
                    "() => document.querySelectorAll('context-viewer .tool-call-item').length === 2",
                    timeout=10000,
                )

                await viewer.evaluate(
                    """
                    (element) => {
                      element.scrollTop = Math.floor(element.scrollHeight / 3);
                    }
                    """
                )
                scroll_top_before = await viewer.evaluate("(element) => element.scrollTop")

                await tool_section_header.evaluate("(element) => element.click()")
                await page.wait_for_function(
                    "() => document.querySelectorAll('context-viewer .tool-call-item').length === 0",
                    timeout=10000,
                )
                await page.wait_for_timeout(100)
                scroll_top_after_collapse = await viewer.evaluate("(element) => element.scrollTop")
                assert abs(scroll_top_after_collapse - scroll_top_before) < 50

                await tool_section_header.evaluate("(element) => element.click()")
                await page.wait_for_function(
                    "() => document.querySelectorAll('context-viewer .tool-call-item').length === 2",
                    timeout=10000,
                )
                await page.wait_for_timeout(100)
                scroll_top_after_expand = await viewer.evaluate("(element) => element.scrollTop")
                assert abs(scroll_top_after_expand - scroll_top_before) < 50

                first_tool_item = page.locator('context-viewer .tool-call-item').first
                first_tool_summary = first_tool_item.locator('.tool-call-summary')

                assert await first_tool_item.get_attribute('open') is not None
                await first_tool_summary.evaluate("(element) => element.click()")
                await page.wait_for_function(
                    "() => !document.querySelector('context-viewer .tool-call-item')?.hasAttribute('open')",
                    timeout=10000,
                )
                await page.wait_for_timeout(50)
                scroll_top_after_item_collapse = await viewer.evaluate("(element) => element.scrollTop")
                assert abs(scroll_top_after_item_collapse - scroll_top_before) < 50

                await first_tool_summary.evaluate("(element) => element.click()")
                await page.wait_for_function(
                    "() => document.querySelector('context-viewer .tool-call-item')?.hasAttribute('open')",
                    timeout=10000,
                )
                await page.wait_for_timeout(50)
                scroll_top_after_item_expand = await viewer.evaluate("(element) => element.scrollTop")
                assert abs(scroll_top_after_item_expand - scroll_top_before) < 50

                await browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
