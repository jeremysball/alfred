#!/usr/bin/env python3
"""Show screenshots of the working themes."""

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


def take_screenshots():
    """Take screenshots showing the working features."""
    themes = [
        ("dark-academia", "Dark Academia"),
        ("swiss-international", "Swiss International"),
        ("neumorphism", "Neumorphism"),
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        
        for theme_id, theme_name in themes:
            print(f"\n📸 {theme_name}...")
            
            # Desktop
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()
            
            page.goto("http://localhost:9999", wait_until="networkidle")
            time.sleep(1)
            
            page.evaluate(f"localStorage.setItem('alfred-theme', '{theme_id}')")
            page.reload(wait_until="networkidle")
            time.sleep(1)
            
            # Add messages with reasoning
            page.evaluate("""
                const messageList = document.getElementById('message-list');
                messageList.innerHTML = '';
                
                const userMsg = document.createElement('chat-message');
                userMsg.setAttribute('role', 'user');
                userMsg.setAttribute('content', 'Explain quantum computing');
                userMsg.setAttribute('timestamp', new Date().toISOString());
                messageList.appendChild(userMsg);
                
                const assistantMsg = document.createElement('chat-message');
                assistantMsg.setAttribute('role', 'assistant');
                assistantMsg.setAttribute('content', 'Quantum computing uses qubits...');
                assistantMsg.setAttribute('timestamp', new Date().toISOString());
                messageList.appendChild(assistantMsg);
                
                assistantMsg.appendReasoning("1. Qubits can be 0 and 1 simultaneously\\n2. This enables parallel computation\\n3. Algorithms like Shor's factor large numbers");
            """)
            
            time.sleep(0.5)
            
            # Screenshot with CoT visible
            page.screenshot(path=f"/tmp/demo_{theme_id}_desktop.png")
            print(f"  Desktop: /tmp/demo_{theme_id}_desktop.png")
            
            # Open settings
            page.click(".settings-toggle")
            time.sleep(0.3)
            page.screenshot(path=f"/tmp/demo_{theme_id}_settings.png")
            print(f"  Settings: /tmp/demo_{theme_id}_settings.png")
            
            context.close()
            
            # Mobile
            context = browser.new_context(viewport={"width": 375, "height": 667})
            page = context.new_page()
            
            page.goto("http://localhost:9999", wait_until="networkidle")
            time.sleep(1)
            
            page.evaluate(f"localStorage.setItem('alfred-theme', '{theme_id}')")
            page.reload(wait_until="networkidle")
            time.sleep(1)
            
            page.evaluate("""
                const messageList = document.getElementById('message-list');
                messageList.innerHTML = '';
                
                const userMsg = document.createElement('chat-message');
                userMsg.setAttribute('role', 'user');
                userMsg.setAttribute('content', 'Mobile test');
                userMsg.setAttribute('timestamp', new Date().toISOString());
                messageList.appendChild(userMsg);
                
                const assistantMsg = document.createElement('chat-message');
                assistantMsg.setAttribute('role', 'assistant');
                assistantMsg.setAttribute('content', 'Mobile response');
                assistantMsg.setAttribute('timestamp', new Date().toISOString());
                messageList.appendChild(assistantMsg);
                
                assistantMsg.appendReasoning("Thinking on mobile...");
            """)
            
            time.sleep(0.5)
            page.screenshot(path=f"/tmp/demo_{theme_id}_mobile.png")
            print(f"  Mobile: /tmp/demo_{theme_id}_mobile.png")
            
            # Open settings on mobile
            page.click(".settings-toggle")
            time.sleep(0.3)
            page.screenshot(path=f"/tmp/demo_{theme_id}_mobile_settings.png")
            print(f"  Mobile Settings: /tmp/demo_{theme_id}_mobile_settings.png")
            
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
        take_screenshots()
        print("\n🎉 All screenshots saved!")
        return 0
        
    finally:
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
