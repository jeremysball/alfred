#!/usr/bin/env python3
"""Take comparison screenshots of all themes side by side."""

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


def take_comparison():
    """Take screenshots of each theme's settings menu."""
    themes = [
        ("dark-academia", "Dark Academia"),
        ("swiss-international", "Swiss International"),
        ("neumorphism", "Neumorphism"),
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        
        for theme_id, theme_name in themes:
            print(f"\n📸 Capturing {theme_name} settings menu...")
            
            context = browser.new_context(
                viewport={"width": 1280, "height": 600}
            )
            page = context.new_page()
            
            # Navigate with cache disabled
            page.goto("http://localhost:9999", wait_until="networkidle")
            time.sleep(1)
            
            # Set theme
            page.evaluate(f"localStorage.setItem('alfred-theme', '{theme_id}')")
            page.reload(wait_until="networkidle")
            time.sleep(2)
            
            # Open settings menu
            page.click(".settings-toggle")
            time.sleep(0.5)
            
            # Screenshot just the menu area
            page.screenshot(path=f"/tmp/settings_{theme_id}.png")
            print(f"  ✓ /tmp/settings_{theme_id}.png")
            
            context.close()
        
        browser.close()


def main():
    print("🚀 Starting Alfred Web UI server...")
    
    proc = subprocess.Popen(
        ["uv", "run", "alfred", "webui", "--port", "9999"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/workspace/alfred-prd"
    )
    
    try:
        print("⏳ Waiting for server...")
        if not wait_for_server("http://localhost:9999", timeout=30):
            print("❌ Server failed")
            proc.terminate()
            return 1
        
        print("✅ Server ready!")
        take_comparison()
        
        print("\n🎉 Screenshots saved:")
        print("  /tmp/settings_dark-academia.png")
        print("  /tmp/settings_swiss-international.png")
        print("  /tmp/settings_neumorphism.png")
        
        return 0
        
    finally:
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
