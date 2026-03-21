#!/usr/bin/env python3
"""Test hovering over assistant message to see action buttons."""

import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        
        await page.goto("http://127.0.0.1:8080")
        await page.wait_for_timeout(2000)
        
        # Find assistant message and hover
        messages = await page.query_selector_all("chat-message")
        for msg in messages:
            role = await msg.get_attribute("role")
            if role == "assistant":
                await msg.hover()
                await page.wait_for_timeout(500)
                break
        
        await page.screenshot(path="/workspace/alfred-prd/screenshots/hover_test.png", full_page=True)
        print("Screenshot saved")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())
