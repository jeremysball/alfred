#!/usr/bin/env python3
"""Test message actions in the Web UI."""

import asyncio
from playwright.async_api import async_playwright

async def test_message_actions():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        
        # Clear localStorage to ensure fresh state
        await page.goto("http://127.0.0.1:8080")
        await page.evaluate('''() => {
            localStorage.clear();
        }''')
        await page.reload()
        await page.wait_for_timeout(3000)
        
        # Take screenshot of initial state
        await page.screenshot(path="/workspace/alfred-prd/screenshots/message_actions_01.png", full_page=True)
        print("✓ Screenshot 1: Initial state")
        
        # Type and send a message
        textarea = await page.wait_for_selector("#message-input")
        await textarea.fill("Test message with new actions")
        await page.click("#send-button")
        await page.wait_for_timeout(2000)
        
        # Take screenshot showing the sent message
        await page.screenshot(path="/workspace/alfred-prd/screenshots/message_actions_02.png", full_page=True)
        print("✓ Screenshot 2: After sending message")
        
        # Hover over assistant message to show actions
        messages = await page.query_selector_all("chat-message")
        if len(messages) > 0:
            # Hover over the last assistant message
            for msg in reversed(messages):
                role = await msg.get_attribute("role")
                if role == "assistant":
                    await msg.hover()
                    await page.wait_for_timeout(500)
                    await page.screenshot(path="/workspace/alfred-prd/screenshots/message_actions_03.png", full_page=True)
                    print("✓ Screenshot 3: Hovering over assistant message")
                    break
        
        # Mobile view
        mobile = await browser.new_context(viewport={"width": 375, "height": 667})
        mobile_page = await mobile.new_page()
        await mobile_page.goto("http://127.0.0.1:8080")
        await mobile_page.wait_for_timeout(3000)
        await mobile_page.screenshot(path="/workspace/alfred-prd/screenshots/message_actions_mobile.png", full_page=True)
        print("✓ Screenshot 4: Mobile view")
        
        await browser.close()
        print("\n✅ All screenshots saved to /workspace/alfred-prd/screenshots/")

if __name__ == "__main__":
    asyncio.run(test_message_actions())
