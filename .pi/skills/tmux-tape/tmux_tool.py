#!/usr/bin/env python3
"""
Terminal session controller using ttyd + tmux + playwright.

Features:
- Pixel-perfect screenshots via browser rendering
- Text capture via tmux
- Keystroke sending via tmux
- Image upload to 0x0.st (no API key)

Requirements:
    pip install pyte pillow
    npx playwright install chromium
    # System: ttyd, tmux, curl

Usage:
    from tmux_tool import TerminalSession

    with TerminalSession("test", port=7681) as s:
        s.send("echo hello")
        s.send_key("Enter")
        s.sleep(1)
        result = s.capture("output.png", upload=True)
        print(result["text"])
        print(result["url"])
"""

import subprocess
import time
import re
import sys
from pathlib import Path


class TerminalSession:
    """Terminal session using ttyd + tmux + playwright."""
    
    def __init__(self, name: str, cols: int = 120, rows: int = 35, port: int = 7681):
        """
        Initialize terminal session.
        
        Args:
            name: Unique tmux session name
            cols: Terminal width in columns
            rows: Terminal height in rows
            port: Port for ttyd web server
        """
        self.name = name
        self.cols = cols
        self.rows = rows
        self.port = port
        self.ttyd_proc = None
        self._screenshot_count = 0
    
    def __enter__(self):
        """Create tmux session and start ttyd."""
        # Kill any existing session
        subprocess.run(["tmux", "kill-session", "-t", self.name], capture_output=True)
        
        # Create new tmux session
        subprocess.run([
            "tmux", "new-session", "-d", "-s", self.name,
            "-x", str(self.cols), "-y", str(self.rows)
        ], capture_output=True)
        
        # Clear screen for clean start
        subprocess.run(["tmux", "send-keys", "-t", self.name, "C-l"], check=True)
        time.sleep(0.2)
        
        # Start ttyd attached to tmux session
        self.ttyd_proc = subprocess.Popen(
            ["ttyd", "--port", str(self.port), "--writable",
             "tmux", "attach", "-t", self.name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait for ttyd to be ready
        time.sleep(1)
        
        return self
    
    def __exit__(self, *args):
        """Cleanup ttyd and tmux."""
        if self.ttyd_proc:
            self.ttyd_proc.terminate()
            try:
                self.ttyd_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.ttyd_proc.kill()
        
        subprocess.run(["tmux", "kill-session", "-t", self.name], capture_output=True)
    
    def send(self, text: str) -> None:
        """
        Send text to the terminal.
        
        Args:
            text: Text to type
        """
        subprocess.run(["tmux", "send-keys", "-t", self.name, text], check=True)
    
    def send_key(self, key: str) -> None:
        """
        Send special key to the terminal.
        
        Args:
            key: Key name (Enter, C-c, C-d, C-l, Escape, Tab, Space, Up, Down, Left, Right)
        """
        subprocess.run(["tmux", "send-keys", "-t", self.name, key], check=True)
    
    def sleep(self, seconds: float) -> None:
        """
        Wait for specified duration.
        
        Args:
            seconds: Time to wait
        """
        time.sleep(seconds)
    
    def capture_text(self) -> str:
        """
        Capture terminal text content (ANSI-stripped).
        
        Returns:
            Plain text from terminal
        """
        result = subprocess.run(
            ["tmux", "capture-pane", "-p", "-t", self.name],
            capture_output=True, text=True
        )
        raw = result.stdout
        
        # Strip ANSI escape sequences
        pattern = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\].*?\x07')
        plain = pattern.sub('', raw)
        
        # Clean up trailing whitespace and empty lines
        lines = [line.rstrip() for line in plain.split('\n')]
        while lines and not lines[-1]:
            lines.pop()
        
        return '\n'.join(lines)
    
    def capture_raw(self) -> str:
        """
        Capture terminal with ANSI escape codes (for debugging).
        
        Returns:
            Raw text with ANSI codes preserved
        """
        result = subprocess.run(
            ["tmux", "capture-pane", "-e", "-p", "-t", self.name],
            capture_output=True, text=True
        )
        return result.stdout
    
    def capture_screenshot(self, filename: str = None, upload: bool = False) -> dict:
        """
        Capture screenshot via ttyd + playwright.
        
        Args:
            filename: Output filename (default: screenshot_N.png)
            upload: Upload to 0x0.st and include URL in result
        
        Returns:
            dict with 'screenshot' path and optionally 'url'
        """
        self._screenshot_count += 1
        if filename is None:
            filename = f"screenshot_{self._screenshot_count}.png"
        
        # Calculate viewport size
        viewport = f"{self.cols * 10},{self.rows * 20}"
        
        # Take screenshot with playwright
        result = subprocess.run(
            ["npx", "playwright", "screenshot",
             "--viewport-size", viewport,
             "--wait-for-timeout", "1500",
             f"http://localhost:{self.port}",
             filename],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            return {"error": result.stderr, "screenshot": None}
        
        print(f"Screenshot: {filename}")
        
        result = {"screenshot": filename}
        
        if upload:
            result["url"] = self.upload(filename)
        
        return result
    
    def capture(self, filename: str = None, upload: bool = False) -> dict:
        """
        Capture both text and screenshot.
        
        Args:
            filename: Screenshot filename (default: screenshot_N.png)
            upload: Upload screenshot to 0x0.st
        
        Returns:
            dict with 'text', 'screenshot', and optionally 'url'
        """
        text = self.capture_text()
        screenshot = self.capture_screenshot(filename, upload)
        screenshot["text"] = text
        return screenshot
    
    def upload(self, filepath: str) -> str:
        """
        Upload image to 0x0.st (free, no API key).
        
        Args:
            filepath: Path to image file
        
        Returns:
            URL of uploaded image
        """
        result = subprocess.run(
            ["curl", "-s", "-F", f"file=@{filepath}", "https://0x0.st"],
            capture_output=True, text=True
        )
        url = result.stdout.strip()
        
        if url.startswith("http"):
            print(f"Uploaded: {url}")
            return url
        else:
            print(f"Upload failed: {url}")
            return None


def main():
    """Demo/test of TerminalSession."""
    print("=== Terminal Session Demo ===\n")
    
    with TerminalSession("demo", port=7681) as s:
        print("Running demo commands...")
        
        # Simple echo test
        s.send("echo 'Hello from ttyd!'")
        s.send_key("Enter")
        s.sleep(1)
        
        # Capture
        result = s.capture("demo.png", upload=True)
        
        print("\nText output:")
        print(result["text"])
        
        if result.get("url"):
            print(f"\nScreenshot: {result['url']}")
        elif result.get("screenshot"):
            print(f"\nScreenshot: {result['screenshot']}")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()
