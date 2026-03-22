import asyncio

from playwright.async_api import async_playwright


async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 375, "height": 667})

        await page.goto("http://127.0.0.1:8080")
        await page.wait_for_timeout(2000)

        await page.screenshot(path="/workspace/alfred-prd/screenshots/mobile_buttons.png", full_page=True)
        print("Mobile screenshot saved")

        await browser.close()


asyncio.run(test())
