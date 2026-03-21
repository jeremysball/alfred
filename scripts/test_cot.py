#!/usr/bin/env python3
"""Test that CoT/reasoning display is working."""

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


def test_cot():
    """Test CoT display by injecting reasoning."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        
        page.goto("http://localhost:9999", wait_until="networkidle")
        time.sleep(1)
        
        # Test each theme
        for theme_id in ["dark-academia", "swiss-international", "neumorphism"]:
            print(f"\n🎨 Testing {theme_id}...")
            
            page.evaluate(f"localStorage.setItem('alfred-theme', '{theme_id}')")
            page.reload(wait_until="networkidle")
            time.sleep(1)
            
            # Inject a message with reasoning
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
                assistantMsg.setAttribute('content', 'Test answer');
                assistantMsg.setAttribute('timestamp', new Date().toISOString());
                messageList.appendChild(assistantMsg);
                
                // Add reasoning
                assistantMsg.appendReasoning("This is the reasoning process.\\n\\nStep 1: Analyze the question\\nStep 2: Formulate answer");
            """)
            
            time.sleep(0.5)
            
            # Check if reasoning section exists and is visible
            reasoning_visible = page.evaluate("""() => {
                const reasoningContent = document.querySelector('.reasoning-content');
                const reasoningSection = document.querySelector('.reasoning-section');
                const reasoningLabel = document.querySelector('.reasoning-label');
                
                return {
                    hasSection: !!reasoningSection,
                    hasContent: !!reasoningContent,
                    hasLabel: !!reasoningLabel,
                    labelText: reasoningLabel ? reasoningLabel.textContent : null,
                    contentDisplay: reasoningContent ? reasoningContent.style.display : null,
                    contentText: reasoningContent ? reasoningContent.textContent.substring(0, 50) : null
                };
            }""")
            
            print(f"  Reasoning section: {reasoning_visible}")
            
            # Screenshot
            page.screenshot(path=f"/tmp/cot_test_{theme_id}.png")
            print(f"  📸 Screenshot: /tmp/cot_test_{theme_id}.png")
            
            if not reasoning_visible['hasSection']:
                print(f"  ❌ No reasoning section found!")
            elif reasoning_visible['contentDisplay'] == 'none':
                print(f"  ⚠️ Reasoning is collapsed (display: none)")
            else:
                print(f"  ✅ Reasoning is visible")
        
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
        test_cot()
        return 0
        
    finally:
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
