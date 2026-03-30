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
async def test_browser_context_viewer_uses_theme_tokens_and_exposes_full_details() -> None:
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

                await page.evaluate("""
                    () => {
                      document.documentElement.setAttribute('data-theme', 'spacejam-neocities');
                    }
                """)

                await page.fill('#message-input', '/context')
                await page.click('#send-button')
                await page.wait_for_function(
                    "() => document.querySelectorAll('context-viewer').length === 1",
                    timeout=10000,
                )

                viewer = page.locator('context-viewer').last
                system_badge = viewer.locator('.context-section-header[data-section="system-prompt"] .section-badge')
                memories_badge = viewer.locator('.context-section-header[data-section="memories"] .section-badge')
                session_badge = viewer.locator('.context-section-header[data-section="session-history"] .section-badge')
                tool_badge = viewer.locator('.context-section-header[data-section="tool-calls"] .section-badge')
                memory_items = viewer.locator('.memory-item')
                session_messages = viewer.locator('.session-message')
                tool_items = viewer.locator('.tool-call-item')
                memory_summary_mains = viewer.locator('.memory-summary-main')
                session_summary_mains = viewer.locator('.session-message-summary-main')
                tool_summary_mains = viewer.locator('.tool-call-summary-main')
                tool_arguments = viewer.locator('.tool-arguments')
                tool_outputs = viewer.locator('.tool-output')

                assert (await system_badge.text_content() or '').strip() == '2 active / 1 disabled'
                assert (await memories_badge.text_content() or '').strip() == '2 memories'
                assert (await session_badge.text_content() or '').strip() == '2 displayed / 5 included / 8 total messages'
                assert (await tool_badge.text_content() or '').strip() == '2 outcomes'

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
                await page.evaluate(
                    """
                    () => {
                      document.querySelector('context-viewer .context-section-header[data-section="tool-calls"]')?.click();
                    }
                    """
                )

                await page.wait_for_function(
                    "() => document.querySelectorAll('context-viewer .memory-item').length === 2",
                    timeout=10000,
                )
                await page.wait_for_function(
                    "() => document.querySelectorAll('context-viewer .session-message').length === 2",
                    timeout=10000,
                )
                await page.wait_for_function(
                    "() => document.querySelectorAll('context-viewer .tool-call-item').length === 2",
                    timeout=10000,
                )

                assert await memory_items.count() == 2
                assert await session_messages.count() == 2
                assert await tool_items.count() == 2
                assert await memory_summary_mains.count() == 2
                assert await session_summary_mains.count() == 2
                assert await tool_summary_mains.count() == 2
                assert await tool_arguments.count() == 2
                assert await tool_outputs.count() == 2

                first_tool_item = viewer.locator('.tool-call-item').first
                first_tool_summary = first_tool_item.locator('.tool-call-summary')

                assert await first_tool_item.get_attribute('open') is not None
                await first_tool_summary.evaluate("(element) => element.click()")
                await page.wait_for_function(
                    "() => !document.querySelector('context-viewer .tool-call-item')?.hasAttribute('open')",
                    timeout=10000,
                )
                await first_tool_summary.evaluate("(element) => element.click()")
                await page.wait_for_function(
                    "() => document.querySelector('context-viewer .tool-call-item')?.hasAttribute('open')",
                    timeout=10000,
                )

                viewer_style = await page.evaluate(
                    """
                    () => {
                      const probe = document.createElement('div');
                      probe.style.cssText = 'position: fixed; left: -9999px; top: -9999px; background: var(--surface-panel-bg); border: 1px solid var(--surface-panel-border); color: var(--surface-panel-header-text);';
                      document.body.appendChild(probe);

                      const viewer = document.querySelector('context-viewer .context-viewer');
                      const probeStyle = getComputedStyle(probe);
                      const viewerStyle = viewer ? getComputedStyle(viewer) : null;

                      return {
                        probeBg: probeStyle.backgroundColor,
                        probeBorder: probeStyle.borderTopColor,
                        probeText: probeStyle.color,
                        viewerBg: viewerStyle ? viewerStyle.backgroundColor : '',
                        viewerBorder: viewerStyle ? viewerStyle.borderTopColor : '',
                        viewerText: viewerStyle ? viewerStyle.color : '',
                      };
                    }
                    """
                )

                assert viewer_style['viewerBg'] == viewer_style['probeBg']
                assert viewer_style['viewerBorder'] == viewer_style['probeBorder']
                assert viewer_style['viewerText'] == viewer_style['probeText']

                tool_surface_style = await page.evaluate(
                    """
                    () => {
                      const viewer = document.querySelector('context-viewer .context-viewer');
                      const toolItem = viewer?.querySelector('.tool-call-item');
                      const memoryItem = viewer?.querySelector('.memory-item');
                      const sessionItem = viewer?.querySelector('.session-message');

                      if (!viewer || !toolItem || !memoryItem || !sessionItem) {
                        return null;
                      }

                      const metrics = (element, selector) => {
                        const target = selector ? element.querySelector(selector) : element;
                        if (!target) {
                          return null;
                        }

                        const style = getComputedStyle(target);
                        return {
                          alignItems: style.alignItems,
                          backgroundColor: style.backgroundColor,
                          borderLeftWidth: style.borderLeftWidth,
                          borderRadius: style.borderRadius,
                          color: style.color,
                          display: style.display,
                          flexDirection: style.flexDirection,
                          fontFamily: style.fontFamily,
                          fontSize: style.fontSize,
                          gap: style.gap,
                          lineHeight: style.lineHeight,
                          paddingBottom: style.paddingBottom,
                          paddingLeft: style.paddingLeft,
                          paddingRight: style.paddingRight,
                          paddingTop: style.paddingTop,
                        };
                      };

                      return {
                        toolCard: metrics(toolItem),
                        memoryCard: metrics(memoryItem),
                        sessionCard: metrics(sessionItem),
                        toolSummary: metrics(toolItem, '.tool-call-summary'),
                        memorySummary: metrics(memoryItem, '.memory-summary'),
                        sessionSummary: metrics(sessionItem, '.session-message-summary'),
                        toolSummaryMain: metrics(toolItem, '.tool-call-summary-main'),
                        memorySummaryMain: metrics(memoryItem, '.memory-summary-main'),
                        sessionSummaryMain: metrics(sessionItem, '.session-message-summary-main'),
                        toolBody: metrics(toolItem, '.tool-call-body'),
                        memoryBody: metrics(memoryItem, '.memory-body'),
                        sessionBody: metrics(sessionItem, '.session-message-body'),
                        toolContent: metrics(toolItem, '.tool-output'),
                        memoryContent: metrics(memoryItem, '.memory-content'),
                        sessionContent: metrics(sessionItem, '.message-content'),
                      };
                    }
                    """
                )

                assert tool_surface_style is not None

                assert tool_surface_style['toolCard']['backgroundColor'] == tool_surface_style['memoryCard']['backgroundColor'] == tool_surface_style['sessionCard']['backgroundColor']
                assert tool_surface_style['toolCard']['borderRadius'] == tool_surface_style['memoryCard']['borderRadius'] == tool_surface_style['sessionCard']['borderRadius']
                assert tool_surface_style['toolCard']['borderLeftWidth'] == tool_surface_style['memoryCard']['borderLeftWidth'] == tool_surface_style['sessionCard']['borderLeftWidth'] == '3px'
                assert tool_surface_style['toolCard']['display'] == tool_surface_style['memoryCard']['display'] == tool_surface_style['sessionCard']['display'] == 'block'
                assert tool_surface_style['toolCard']['paddingTop'] == tool_surface_style['memoryCard']['paddingTop'] == tool_surface_style['sessionCard']['paddingTop'] == '0px'
                assert tool_surface_style['toolCard']['paddingBottom'] == tool_surface_style['memoryCard']['paddingBottom'] == tool_surface_style['sessionCard']['paddingBottom'] == '0px'
                assert tool_surface_style['toolCard']['paddingLeft'] == tool_surface_style['memoryCard']['paddingLeft'] == tool_surface_style['sessionCard']['paddingLeft'] == '0px'
                assert tool_surface_style['toolCard']['paddingRight'] == tool_surface_style['memoryCard']['paddingRight'] == tool_surface_style['sessionCard']['paddingRight'] == '0px'

                assert tool_surface_style['toolSummary']['backgroundColor'] == tool_surface_style['memorySummary']['backgroundColor'] == tool_surface_style['sessionSummary']['backgroundColor']
                assert tool_surface_style['toolSummary']['color'] == tool_surface_style['memorySummary']['color'] == tool_surface_style['sessionSummary']['color']
                assert tool_surface_style['toolSummary']['display'] == tool_surface_style['memorySummary']['display'] == tool_surface_style['sessionSummary']['display'] == 'flex'
                assert tool_surface_style['toolSummary']['flexDirection'] == tool_surface_style['memorySummary']['flexDirection'] == tool_surface_style['sessionSummary']['flexDirection'] == 'column'
                assert tool_surface_style['toolSummary']['alignItems'] == tool_surface_style['memorySummary']['alignItems'] == tool_surface_style['sessionSummary']['alignItems'] == 'stretch'
                assert tool_surface_style['toolSummary']['gap'] == tool_surface_style['memorySummary']['gap'] == tool_surface_style['sessionSummary']['gap']
                assert tool_surface_style['toolSummary']['paddingTop'] == tool_surface_style['memorySummary']['paddingTop'] == tool_surface_style['sessionSummary']['paddingTop']
                assert tool_surface_style['toolSummary']['paddingBottom'] == tool_surface_style['memorySummary']['paddingBottom'] == tool_surface_style['sessionSummary']['paddingBottom']
                assert tool_surface_style['toolSummary']['paddingLeft'] == tool_surface_style['memorySummary']['paddingLeft'] == tool_surface_style['sessionSummary']['paddingLeft']
                assert tool_surface_style['toolSummary']['paddingRight'] == tool_surface_style['memorySummary']['paddingRight'] == tool_surface_style['sessionSummary']['paddingRight']

                assert tool_surface_style['toolSummaryMain']['display'] == tool_surface_style['memorySummaryMain']['display'] == tool_surface_style['sessionSummaryMain']['display'] == 'flex'
                assert tool_surface_style['toolSummaryMain']['alignItems'] == tool_surface_style['memorySummaryMain']['alignItems'] == tool_surface_style['sessionSummaryMain']['alignItems'] == 'center'
                assert tool_surface_style['toolSummaryMain']['gap'] == tool_surface_style['memorySummaryMain']['gap'] == tool_surface_style['sessionSummaryMain']['gap']

                assert tool_surface_style['toolBody']['display'] == tool_surface_style['memoryBody']['display'] == tool_surface_style['sessionBody']['display'] == 'flex'
                assert tool_surface_style['toolBody']['flexDirection'] == tool_surface_style['memoryBody']['flexDirection'] == tool_surface_style['sessionBody']['flexDirection'] == 'column'
                assert tool_surface_style['toolBody']['gap'] == tool_surface_style['memoryBody']['gap'] == tool_surface_style['sessionBody']['gap']
                assert tool_surface_style['toolBody']['paddingTop'] == tool_surface_style['memoryBody']['paddingTop'] == tool_surface_style['sessionBody']['paddingTop']
                assert tool_surface_style['toolBody']['paddingBottom'] == tool_surface_style['memoryBody']['paddingBottom'] == tool_surface_style['sessionBody']['paddingBottom']
                assert tool_surface_style['toolBody']['paddingLeft'] == tool_surface_style['memoryBody']['paddingLeft'] == tool_surface_style['sessionBody']['paddingLeft']
                assert tool_surface_style['toolBody']['paddingRight'] == tool_surface_style['memoryBody']['paddingRight'] == tool_surface_style['sessionBody']['paddingRight']

                assert tool_surface_style['toolContent']['backgroundColor'] == tool_surface_style['memoryContent']['backgroundColor'] == tool_surface_style['sessionContent']['backgroundColor']
                assert tool_surface_style['toolContent']['fontFamily'] == tool_surface_style['memoryContent']['fontFamily'] == tool_surface_style['sessionContent']['fontFamily']
                assert tool_surface_style['toolContent']['fontSize'] == tool_surface_style['memoryContent']['fontSize'] == tool_surface_style['sessionContent']['fontSize']
                assert tool_surface_style['toolContent']['lineHeight'] == tool_surface_style['memoryContent']['lineHeight'] == tool_surface_style['sessionContent']['lineHeight']
                assert tool_surface_style['toolContent']['color'] == tool_surface_style['memoryContent']['color'] == tool_surface_style['sessionContent']['color']

                memory_text = await viewer.locator('.memory-item').first.text_content()
                session_text = await viewer.locator('.session-message').first.text_content()
                tool_text = await viewer.locator('.tool-calls-list').text_content()

                assert memory_text is not None
                assert long_memory in memory_text
                assert session_text is not None
                assert long_session_message in session_text
                assert tool_text is not None
                assert 'Line one of output' in tool_text
                assert 'Line three of output that would normally be truncated in a cramped sheet.' in tool_text
                assert '"command": "python -V"' in tool_text
                assert '"path": "tests/module_test.py"' in tool_text
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
