#!/usr/bin/env python3
"""Debug mobile issues - CoT and settings menu."""

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import urllib.request

from playwright.sync_api import sync_playwright


def wait_for_server(url: str, timeout: int = 30) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except:
            time.sleep(0.5)
    return False


def debug_mobile():
    """Debug mobile layout issues."""
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # Test iPhone size
        context = browser.new_context(viewport={"width": 375, "height": 667})
        page = context.new_page()

        page.goto("http://localhost:9999", wait_until="networkidle")
        time.sleep(1)

        # Set dark academia theme
        page.evaluate("localStorage.setItem('alfred-theme', 'dark-academia')")
        page.reload(wait_until="networkidle")
        time.sleep(1)

        print("\n📱 Testing iPhone layout...")

        # Inject message with reasoning
        page.evaluate("""
            const messageList = document.getElementById('message-list');
            messageList.innerHTML = '';
            
            const userMsg = document.createElement('chat-message');
            userMsg.setAttribute('role', 'user');
            userMsg.setAttribute('content', 'Test question');
            userMsg.setAttribute('timestamp', new Date().toISOString());
            messageList.appendChild(userMsg);
            
            const assistantMsg = document.createElement('chat-message');
            assistantMsg.setAttribute('role', 'assistant');
            assistantMsg.setAttribute('content', 'Test answer here');
            assistantMsg.setAttribute('timestamp', new Date().toISOString());
            messageList.appendChild(assistantMsg);
            
            // Add reasoning
            assistantMsg.appendReasoning("Step 1: Analyze\\nStep 2: Answer");
        """)

        time.sleep(0.5)

        # Check if reasoning exists
        has_reasoning = page.evaluate("() => !!document.querySelector('.reasoning-section')")
        print(f"  Reasoning visible: {has_reasoning}")

        # Screenshot before opening settings
        page.screenshot(path="/tmp/mobile_before_settings.png")
        print("  📸 /tmp/mobile_before_settings.png")

        # Try to click settings button
        print("\n  Clicking settings button...")
        try:
            page.click(".settings-toggle")
            time.sleep(0.5)
            page.screenshot(path="/tmp/mobile_settings_open.png")
            print("  📸 /tmp/mobile_settings_open.png")

            # Check if dropdown is visible
            dropdown_visible = page.evaluate("""() => {
                const dropdown = document.querySelector('.settings-dropdown');
                return dropdown && !dropdown.classList.contains('hidden');
            }""")
            print(f"  Settings dropdown visible: {dropdown_visible}")

        except Exception as e:
            print(f"  ❌ Error clicking settings: {e}")

        browser.close()


def main():
    print("🚀 Starting server...")
    proc = subprocess.Popen(
        ["uv", "run", "alfred", "webui", "--port", "9999"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd="/workspace/alfred-prd"
    )

    try:
        if not wait_for_server("http://localhost:9999", timeout=30):
            print("❌ Server failed")
            return 1

        print("✅ Server ready")
        debug_mobile()
        return 0

    finally:
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
