#!/usr/bin/env python3
"""Debug CoT display - trace WebSocket messages."""

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


def debug_cot():
    """Debug CoT by tracing WebSocket messages."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        
        # Enable console logging
        page.on("console", lambda msg: print(f"  [Console] {msg.type}: {msg.text}"))
        
        page.goto("http://localhost:9999", wait_until="networkidle")
        time.sleep(1)
        
        # Monitor WebSocket messages
        page.evaluate("""
            // Store original WebSocket
            const OriginalWebSocket = window.WebSocket;
            
            // Create debug wrapper
            window.WebSocket = function(url) {
                console.log('[WebSocket] Connecting to:', url);
                const ws = new OriginalWebSocket(url);
                
                ws.addEventListener('message', (event) => {
                    console.log('[WebSocket] Received:', event.data);
                    try {
                        const msg = JSON.parse(event.data);
                        if (msg.type === 'reasoning.chunk') {
                            console.log('[WebSocket] ✓ REASONING CHUNK:', msg.payload?.content);
                        } else if (msg.type === 'chat.started') {
                            console.log('[WebSocket] ✓ CHAT STARTED');
                        } else if (msg.type === 'chat.chunk') {
                            console.log('[WebSocket] ✓ CHAT CHUNK:', msg.payload?.content?.substring(0, 50));
                        }
                    } catch(e) {}
                });
                
                return ws;
            };
            window.WebSocket.prototype = OriginalWebSocket.prototype;
        """)
        
        print("\n🧪 Testing with actual chat message...")
        
        # Type a message
        page.fill("#message-input", "What is 2+2?")
        
        # Monitor what's happening
        page.click("#send-button")
        
        print("\n⏳ Waiting for response (10 seconds)...")
        time.sleep(10)
        
        # Check DOM state
        dom_state = page.evaluate("""() => {
            const reasoningSection = document.querySelector('.reasoning-section');
            const reasoningContent = document.querySelector('.reasoning-content');
            const messages = document.querySelectorAll('chat-message');
            
            return {
                messageCount: messages.length,
                hasReasoningSection: !!reasoningSection,
                hasReasoningContent: !!reasoningContent,
                reasoningDisplay: reasoningContent ? reasoningContent.style.display : 'not-found',
                reasoningHTML: reasoningContent ? reasoningContent.innerHTML.substring(0, 200) : 'not-found',
                messageListHTML: document.getElementById('message-list')?.innerHTML?.substring(0, 500)
            };
        }""")
        
        print("\n📊 DOM State:")
        for key, value in dom_state.items():
            print(f"  {key}: {value}")
        
        # Screenshot
        page.screenshot(path="/tmp/debug_cot.png", full_page=True)
        print("\n📸 Screenshot saved: /tmp/debug_cot.png")
        
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
        debug_cot()
        return 0
        
    finally:
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
