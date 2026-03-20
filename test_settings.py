#!/usr/bin/env python3
"""Test the settings menu visibility."""

import asyncio
from playwright.async_api import async_playwright

async def test_settings():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        
        await page.goto("http://127.0.0.1:8080")
        await page.wait_for_timeout(2000)
        
        # Click the settings button
        await page.click(".settings-toggle")
        await page.wait_for_timeout(500)
        
        # Take screenshot
        await page.screenshot(path="/workspace/alfred-prd/screenshots/settings_menu.png", full_page=True)
        print("Screenshot saved")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_settings())
