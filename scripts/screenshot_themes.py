#!/usr/bin/env python3
"""Take screenshots of all themes for preview."""

import subprocess
import time
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.sync_api import sync_playwright
import urllib.request


def wait_for_server(url: str, timeout: int = 30) -> bool:
    """Wait for server to be ready."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except:
            time.sleep(0.5)
    return False


def inject_test_message_with_reasoning(page):
    """Inject a test message with reasoning to show CoT display."""
    page.evaluate("""
        const messageList = document.getElementById('message-list');
        
        // Create user message
        const userMsg = document.createElement('chat-message');
        userMsg.setAttribute('role', 'user');
        userMsg.setAttribute('content', 'What is the capital of France?');
        userMsg.setAttribute('timestamp', new Date().toISOString());
        messageList.appendChild(userMsg);
        
        // Create assistant message with reasoning
        const assistantMsg = document.createElement('chat-message');
        assistantMsg.setAttribute('role', 'assistant');
        assistantMsg.setAttribute('content', 'The capital of France is Paris.');
        assistantMsg.setAttribute('timestamp', new Date().toISOString());
        messageList.appendChild(assistantMsg);
        
        // Add reasoning to the assistant message
        assistantMsg.appendReasoning("I need to identify the capital city of France.\\n\\nFrance is a country in Western Europe. Its capital city is well-known and is Paris.\\n\\nLet me verify: Paris is indeed the capital and largest city of France.");
        
        // Scroll to bottom
        const chatContainer = document.getElementById('chat-container');
        chatContainer.scrollTop = chatContainer.scrollHeight;
    """)


def open_settings_menu(page):
    """Click the settings menu to open the dropdown."""
    page.click(".settings-toggle")
    time.sleep(0.5)


def take_screenshots():
    """Take screenshots of each theme."""
    themes = [
        ("dark-academia", "Dark Academia"),
        ("swiss-international", "Swiss International"),
        ("neumorphism", "Neumorphism"),
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        
        for theme_id, theme_name in themes:
            print(f"\n📸 Capturing {theme_name}...")
            
            # Create new context for each theme (clean state)
            context = browser.new_context(
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            
            # Navigate and set theme via localStorage
            page.goto("http://localhost:9999")
            time.sleep(1)
            
            # Set theme
            page.evaluate(f"localStorage.setItem('alfred-theme', '{theme_id}')")
            page.reload()
            time.sleep(2)
            
            # Screenshot 1: Empty state with theme selector open
            open_settings_menu(page)
            page.screenshot(path=f"/tmp/theme_{theme_id}_selector.png")
            print(f"  ✓ Theme selector open")
            
            # Close selector
            page.keyboard.press("Escape")
            time.sleep(0.3)
            
            # Inject test message with reasoning
            inject_test_message_with_reasoning(page)
            time.sleep(0.5)
            
            # Screenshot 2: With reasoning visible
            page.screenshot(path=f"/tmp/theme_{theme_id}_reasoning.png")
            print(f"  ✓ With reasoning/CoT displayed")
            
            context.close()
        
        browser.close()


def main():
    """Main entry point."""
    print("🚀 Starting Alfred Web UI server...")
    
    # Start server
    proc = subprocess.Popen(
        ["uv", "run", "alfred", "webui", "--port", "9999"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/workspace/alfred-prd"
    )
    
    try:
        # Wait for server
        print("⏳ Waiting for server to be ready...")
        if not wait_for_server("http://localhost:9999", timeout=30):
            print("❌ Server failed to start")
            proc.terminate()
            return 1
        
        print("✅ Server ready!\n")
        
        # Take screenshots
        take_screenshots()
        
        print("\n🎉 All screenshots captured!")
        print("\nFiles saved to:")
        for theme_id, theme_name in [
            ("dark-academia", "Dark Academia"),
            ("swiss-international", "Swiss International"),
            ("neumorphism", "Neumorphism"),
        ]:
            print(f"  /tmp/theme_{theme_id}_selector.png - Theme selector")
            print(f"  /tmp/theme_{theme_id}_reasoning.png - With CoT reasoning")
        
        return 0
        
    finally:
        print("\n🛑 Stopping server...")
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
