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
async def test_browser_context_viewer_renders_support_value_ledger_entries() -> None:
    port = _find_free_port()
    fake_alfred = FakeAlfred()

    context_data = {
        "system_prompt": {"sections": [], "total_tokens": 0},
        "blocked_context_files": [],
        "conflicted_context_files": [],
        "disabled_sections": [],
        "warnings": [],
        "support_state": {
            "enabled": True,
            "request": {"response_mode": "execute", "arc_id": "webui_cleanup"},
            "summary": {
                "response_mode": "execute",
                "active_arc_id": "webui_cleanup",
                "active_pattern_count": 0,
                "candidate_pattern_count": 0,
                "confirmed_pattern_count": 0,
                "recent_update_event_count": 0,
                "recent_intervention_count": 0,
                "active_domain_count": 0,
                "active_arc_count": 0,
            },
            "active_runtime_state": {
                "response_mode": "execute",
                "active_arc_id": "webui_cleanup",
                "effective_support_values": {},
                "effective_relational_values": {},
                "active_patterns": [],
            },
            "learned_state": {
                "candidate_patterns_count": 0,
                "confirmed_patterns_count": 0,
                "recent_update_event_count": 0,
                "recent_intervention_count": 0,
                "candidate_patterns": [],
                "confirmed_patterns": [],
                "recent_update_events": [],
                "value_ledger_entries": [
                    {
                        "value_id": "val-1",
                        "registry": "support",
                        "dimension": "option_bandwidth",
                        "scope": {"type": "context", "id": "execute", "label": "context:execute"},
                        "value": "single",
                        "status": "active_auto",
                        "confidence": 0.81,
                        "evidence_count": 3,
                        "contradiction_count": 0,
                        "last_case_id": "case-1",
                        "updated_at": "2026-03-23T00:00:00+00:00",
                        "why": "Evidence threshold met.",
                    }
                ],
                "value_ledger_summary": {
                    "total": 1,
                    "counts_by_status": {"active_auto": 1},
                    "counts_by_registry": {"support": 1},
                },
                "recent_ledger_update_events": [
                    {
                        "event_id": "led-1",
                        "entity_type": "value",
                        "entity_id": "val-1",
                        "registry": "support",
                        "dimension_or_kind": "option_bandwidth",
                        "scope": {"type": "context", "id": "execute", "label": "context:execute"},
                        "old_status": None,
                        "new_status": "active_auto",
                        "old_value": None,
                        "new_value": "single",
                        "trigger_case_ids": ["case-1"],
                        "reason": "Evidence threshold met.",
                        "confidence": 0.82,
                        "created_at": "2026-03-23T00:00:00+00:00",
                    }
                ],
                "recent_interventions": [],
            },
            "active_domains": [],
            "active_arcs": [],
        },
        "memories": {"displayed": 0, "total": 0, "items": [], "tokens": 0},
        "session_history": {"displayed": 0, "included": 0, "total": 0, "messages": [], "tokens": 0},
        "tool_calls": {"displayed": 0, "total": 0, "items": [], "tokens": 0},
        "self_model": {
            "identity": {"name": "Alfred", "role": "Assistant"},
            "runtime": {"interface": "webui", "session_id": "browser-session", "daemon_mode": False},
            "capabilities": {"memory_enabled": True, "search_enabled": True, "tools_count": 0, "tools": []},
            "context_pressure": {"message_count": 0, "memory_count": 0, "approximate_tokens": 1},
        },
        "total_tokens": 1,
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
                await page.goto(
                    f"http://127.0.0.1:{port}/static/index.html",
                    wait_until="domcontentloaded",
                )

                await page.wait_for_function(
                    "() => document.querySelector('#connection-pill')?.classList.contains('connected')",
                    timeout=10000,
                )

                await page.fill("#message-input", "/context")
                await page.click("#send-button")

                await page.wait_for_function(
                    "() => document.querySelectorAll('context-viewer').length === 1",
                    timeout=10000,
                )

                ledger_title = page.locator("context-viewer .card-title", has_text="Value Ledger")
                assert await ledger_title.count() >= 1

                entry = page.locator("context-viewer .support-ledger-entry").first
                entry_text = await entry.inner_text()
                assert "support:option_bandwidth" in entry_text
                assert "active_auto" in entry_text
                assert "single" in entry_text

                update_title = page.locator("context-viewer .card-title", has_text="Ledger Updates")
                assert await update_title.count() >= 1

                update_row = page.locator("context-viewer .support-ledger-event").first
                update_text = await update_row.inner_text()
                assert "value support:option_bandwidth" in update_text
                assert "active_auto" in update_text

                await browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
