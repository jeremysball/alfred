#!/usr/bin/env python3
"""Test Web UI using Playwright."""

import asyncio
import subprocess

from playwright.async_api import async_playwright


async def test_webui():
    """Test the Web UI."""
    # Start the Web UI server
    print("Starting Web UI server...")
    proc = subprocess.Popen(
        ["uv", "run", "alfred", "webui", "--port", "8888"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to start
    await asyncio.sleep(5)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()

            # Navigate to Web UI
            print("Navigating to Web UI...")
            await page.goto("http://localhost:8888")
            await asyncio.sleep(2)

            # Check if connected
            print("Checking connection status...")
            connection_pill = await page.locator("#connection-pill").text_content()
            print(f"Connection pill: {connection_pill}")

            # Take screenshot
            await page.screenshot(path="/tmp/webui_initial.png")
            print("Screenshot saved to /tmp/webui_initial.png")

            # Test status bar
            print("Checking status bar...")
            status_bar = await page.locator("status-bar").is_visible()
            print(f"Status bar visible: {status_bar}")

            # Get status bar content
            status_content = await page.locator("status-bar").inner_html()
            print(f"Status bar HTML: {status_content[:500]}")

            # Test command
            print("\nTesting /new command...")
            input_field = page.locator("#message-input")
            await input_field.fill("/new")
            await asyncio.sleep(0.5)

            # Take screenshot before sending
            await page.screenshot(path="/tmp/webui_command_typed.png")

            # Send command
            await input_field.press("Enter")
            await asyncio.sleep(3)

            # Take screenshot after command
            await page.screenshot(path="/tmp/webui_after_command.png")
            print("Screenshot saved to /tmp/webui_after_command.png")

            # Check for messages
            messages = await page.locator("chat-message").count()
            print(f"Number of messages: {messages}")

            # Get last message content
            if messages > 0:
                last_msg = await page.locator("chat-message").last.inner_text()
                print(f"Last message: {last_msg[:200]}")

            # Check browser console logs
            print("\nChecking browser console...")
            logs = await page.evaluate("() => { return window.consoleLogs || []; }")
            print(f"Console logs: {logs}")

            await browser.close()

    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    asyncio.run(test_webui())
