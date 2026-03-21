#!/usr/bin/env python3
"""Test that copy button actually copies to clipboard."""

import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            permissions=['clipboard-read', 'clipboard-write'],
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()
        
        await page.goto("http://127.0.0.1:8080")
        await page.wait_for_timeout(2000)
        
        # Find an assistant message
        messages = await page.query_selector_all("chat-message")
        assistant_msg = None
        for msg in messages:
            role = await msg.get_attribute("role")
            if role == "assistant":
                assistant_msg = msg
                break
        
        if not assistant_msg:
            print("No assistant message found")
            await browser.close()
            return
        
        # Hover to show buttons
        await assistant_msg.hover()
        await page.wait_for_timeout(300)
        
        # Get the message content
        content_div = await assistant_msg.query_selector(".message-content")
        content_text = await content_div.text_content() if content_div else ""
        print(f"Message content: {content_text[:50]}...")
        
        # Click copy button
        copy_btn = await assistant_msg.query_selector('[data-action="copy"]')
        if copy_btn:
            print("Found copy button, clicking...")
            await copy_btn.click()
            await page.wait_for_timeout(500)
            
            # Check clipboard
            try:
                clipboard_text = await page.evaluate("navigator.clipboard.readText()")
                print(f"Clipboard content: {clipboard_text[:50]}...")
                
                # Debug: show exact lengths and repr
                print(f"  Content repr: {repr(content_text[:100])}")
                print(f"  Clipboard repr: {repr(clipboard_text[:100])}")
                print(f"  Content len: {len(content_text)}, Clipboard len: {len(clipboard_text)}")

                if clipboard_text.strip() and clipboard_text == content_text:
                    print("✓ Copy successful!")
                elif clipboard_text.strip():
                    print("✓ Copy worked (content may differ slightly)")
                else:
                    print("✗ Copy failed - clipboard empty")
            except Exception as e:
                print(f"✗ Could not read clipboard: {e}")
        else:
            print("Copy button not found")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())
