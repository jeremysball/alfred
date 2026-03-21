#!/usr/bin/env python3
"""Test settings menu on mobile."""

import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        
        # Test mobile viewport
        context = await browser.new_context(viewport={"width": 375, "height": 667})
        page = await context.new_page()
        
        await page.goto("http://127.0.0.1:8080")
        await page.wait_for_timeout(2000)
        
        # Take screenshot before clicking
        await page.screenshot(path="/workspace/alfred-prd/screenshots/settings_before.png")
        
        # Click settings button
        settings_btn = await page.wait_for_selector(".settings-toggle")
        print("Settings button found:", settings_btn is not None)
        
        # Try clicking
        await settings_btn.click()
        await page.wait_for_timeout(1000)
        
        # Take screenshot after clicking
        await page.screenshot(path="/workspace/alfred-prd/screenshots/settings_after.png")
        
        # Check if dropdown is visible
        dropdown = await page.query_selector(".settings-dropdown:not(.hidden)")
        print("Dropdown visible:", dropdown is not None)
        
        await browser.close()
        print("Test complete!")

if __name__ == "__main__":
    asyncio.run(test())
