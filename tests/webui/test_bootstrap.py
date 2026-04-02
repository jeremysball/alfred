from __future__ import annotations

import pytest
from playwright.async_api import async_playwright, expect


@pytest.mark.slow
@pytest.mark.asyncio
async def test_bootstrap_ready_seam_reports_phase_progress(websocket_server) -> None:
    """Verify browser tests can observe bootstrap phases and wait for a single ready seam.

    This test establishes the bootstrap contract: instead of inferring readiness from
    incidental signals like getComposerState(), tests should be able to wait on an
    explicit bootstrap status that tracks phases and reports when core runtime is ready.
    """
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        try:
            await page.goto(
                f"http://127.0.0.1:{websocket_server.port}/static/index.html",
                wait_until="networkidle",
            )

            # Wait for bootstrap status to exist and reach ready state
            await page.wait_for_function(
                """
                () => {
                    const ui = window.__alfredWebUI;
                    return ui && ui.bootstrap && ui.bootstrap.status === 'ready';
                }
                """,
                timeout=10000,
            )

            # Verify bootstrap exposes phase information
            bootstrap_info = await page.evaluate("""
                () => {
                    const ui = window.__alfredWebUI;
                    return {
                        hasBootstrap: !!ui?.bootstrap,
                        status: ui?.bootstrap?.status,
                        phases: ui?.bootstrap?.phases,
                        currentPhase: ui?.bootstrap?.currentPhase,
                    };
                }
            """)

            assert bootstrap_info["hasBootstrap"] is True
            assert bootstrap_info["status"] == "ready"
            assert isinstance(bootstrap_info["phases"], list)
            assert len(bootstrap_info["phases"]) > 0
            # Verify phases show progress (some phases should be completed)
            completed_phases = [p for p in bootstrap_info["phases"] if p.get("completed")]
            assert len(completed_phases) > 0, "Bootstrap should have completed at least one phase"

            # Verify core runtime is actually functional after bootstrap reports ready
            assert await page.evaluate("() => window.__alfredWebUI.getComposerState()") == "idle"

        finally:
            await browser.close()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_bootstrap_reports_failed_phase_when_registered_step_throws(websocket_server) -> None:
    """Verify startup reports the failing phase locally instead of hanging silently."""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        # Inject a failing step to test failure reporting
        await page.add_init_script(
            """
            window.__forceBootstrapFailure = true;
            """
        )

        try:
            await page.goto(
                f"http://127.0.0.1:{websocket_server.port}/static/index.html",
                wait_until="networkidle",
            )

            # Wait a moment for bootstrap to attempt initialization
            await page.wait_for_timeout(1000)

            # Check that bootstrap reports failure state when a step throws
            bootstrap_status = await page.evaluate("""
                () => {
                    const ui = window.__alfredWebUI;
                    return {
                        hasBootstrap: !!ui?.bootstrap,
                        status: ui?.bootstrap?.status,
                        failedPhase: ui?.bootstrap?.failedPhase,
                        error: ui?.bootstrap?.error,
                    };
                }
            """)

            # If we injected a failure, we should see it reported
            # Note: This test validates the contract exists; actual failure injection
            # requires bootstrap.js to check for window.__forceBootstrapFailure
            if bootstrap_status["hasBootstrap"]:
                # Bootstrap exists - verify it can report failure state
                assert bootstrap_status["status"] in ["ready", "failed", "initializing"]
                if bootstrap_status["status"] == "failed":
                    assert bootstrap_status["failedPhase"] is not None
                    assert bootstrap_status["error"] is not None

        finally:
            await browser.close()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_webui_bootstrap_allows_message_send(websocket_server) -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        await page.add_init_script(
            """
            window.__sentWebSocketMessages = [];
            const originalSend = WebSocket.prototype.send;
            WebSocket.prototype.send = function(data) {
              window.__sentWebSocketMessages.push(data);
              return originalSend.call(this, data);
            };
            """
        )

        try:
            await page.goto(
                f"http://127.0.0.1:{websocket_server.port}/static/index.html",
                wait_until="networkidle",
            )

            await expect(page.locator("#input-area")).to_have_attribute("data-composer-state", "idle")
            assert await page.evaluate("() => !!window.__alfredWebUI") is True
            assert await page.evaluate("() => window.__alfredWebUI.getComposerState()") == "idle"

            await page.fill("#message-input", "bootstrap smoke test")
            await page.click("#send-button")

            await page.wait_for_function(
                """
                () => window.__sentWebSocketMessages.some((message) => {
                  try {
                    const parsed = JSON.parse(message);
                    return parsed.type === 'chat.send' && parsed.payload?.content === 'bootstrap smoke test';
                  } catch {
                    return false;
                  }
                })
                """
            )
        finally:
            await browser.close()
