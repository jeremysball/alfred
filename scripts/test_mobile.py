#!/usr/bin/env python3
"""Test mobile responsive design."""

import subprocess
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.sync_api import sync_playwright
import urllib.request


def wait_for_server(url: str, timeout: int = 30) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except:
            time.sleep(0.5)
    return False


def test_mobile():
    """Test mobile layout at different sizes."""
    devices = [
        ("mobile_small", 375, 667, "iPhone SE"),
        ("mobile_large", 414, 896, "iPhone 11 Pro Max"),
        ("tablet", 768, 1024, "iPad"),
    ]
    
    themes = [
        ("dark-academia", "Dark Academia"),
        ("swiss-international", "Swiss International"),
        ("neumorphism", "Neumorphism"),
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        
        for theme_id, theme_name in themes:
            print(f"\n🎨 Testing {theme_name}...")
            
            for device_id, width, height, device_name in devices:
                print(f"  📱 {device_name} ({width}x{height})")
                
                context = browser.new_context(viewport={"width": width, "height": height})
                page = context.new_page()
                
                page.goto("http://localhost:9999", wait_until="networkidle")
                time.sleep(1)
                
                # Set theme
                page.evaluate(f"localStorage.setItem('alfred-theme', '{theme_id}')")
                page.reload(wait_until="networkidle")
                time.sleep(1)
                
                # Add a test message
                page.evaluate("""
                    const messageList = document.getElementById('message-list');
                    const userMsg = document.createElement('chat-message');
                    userMsg.setAttribute('role', 'user');
                    userMsg.setAttribute('content', 'Mobile test message');
                    userMsg.setAttribute('timestamp', new Date().toISOString());
                    messageList.appendChild(userMsg);
                    
                    const assistantMsg = document.createElement('chat-message');
                    assistantMsg.setAttribute('role', 'assistant');
                    assistantMsg.setAttribute('content', 'This is how it looks on mobile!');
                    assistantMsg.setAttribute('timestamp', new Date().toISOString());
                    messageList.appendChild(assistantMsg);
                """)
                
                time.sleep(0.5)
                
                # Screenshot
                page.screenshot(path=f"/tmp/mobile_{theme_id}_{device_id}.png")
                print(f"    ✓ /tmp/mobile_{theme_id}_{device_id}.png")
                
                context.close()
        
        browser.close()


def main():
    print("🚀 Starting server...")
    proc = subprocess.Popen(
        ["uv", "run", "alfred", "webui", "--port", "9999"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/workspace/alfred-prd"
    )
    
    try:
        if not wait_for_server("http://localhost:9999", timeout=30):
            print("❌ Server failed")
            return 1
        
        print("✅ Server ready")
        test_mobile()
        return 0
        
    finally:
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
