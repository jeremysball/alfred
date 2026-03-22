#!/usr/bin/env python3
"""Test the simplified header design."""

import asyncio

from playwright.async_api import async_playwright


async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        await page.goto("http://127.0.0.1:8080")
        await page.wait_for_timeout(3000)

        await page.screenshot(path="/workspace/alfred-prd/screenshots/simplified_header.png", full_page=True)
        print("Screenshot saved")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(test())
