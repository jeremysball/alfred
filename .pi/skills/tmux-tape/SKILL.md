---
name: tmux-tape
description: Control terminal sessions via ttyd + tmux with pixel-perfect screenshots. Use for E2E testing of TUI applications, CLI interactions, and asyncio apps. Use the tmux_tool.py module for terminal control, browser-based screenshots, and text extraction.
---

# tmux-tape Skill

Run terminal sessions programmatically using ttyd (browser terminal) + tmux (session control) + playwright (screenshots). Pixel-perfect rendering with proper box-drawing, colors, and text extraction.

## Overview

**Why this approach:**
- **ttyd** — Runs terminal in browser via xterm.js (pixel-perfect rendering)
- **tmux** — Controls the session, sends keystrokes, captures text
- **playwright** — Takes screenshots of the browser

**Advantages over VHS:**
- Works with asyncio apps (Alfred, etc.)
- Pixel-perfect rendering (box chars connect, proper colors)
- Real terminal emulation (xterm.js)
- **Wait for patterns instead of sleeping** (see `wait_for()` below)

## Test Images

Example screenshots from Alfred CLI:

| Startup | Response |
|---------|----------|
| https://0x0.st/PSVr.png | https://0x0.st/PSVz.png |

---

## Quick Start

**Always use `uv run python script.py` to run scripts.**

### 1. Install Dependencies

```bash
# Python packages
pip install pyte pillow

# Playwright browser (for screenshots)
npx playwright install chromium

# System packages (usually pre-installed)
# ttyd, tmux, curl
```

### 2. Copy tmux_tool.py

Copy the module to your working directory:

```bash
mkdir -p /tmp/pi-tmux
cp .pi/skills/tmux-tape/tmux_tool.py /tmp/pi-tmux/
cd /tmp/pi-tmux
```

### 3. Write Your Script

**Recommended: Add logging so you can see what's happening:**

```python
#!/usr/bin/env python3
import time
from tmux_tool import TerminalSession

def log(msg):
    """Print with timestamp for visibility."""
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

with TerminalSession("test", port=7681) as s:
    log("Starting test...")
    
    s.send("echo hello")
    s.send_key("Enter")
    
    # RECOMMENDED: Use wait_for() instead of sleep()
    # This waits until "hello" appears in terminal text
    if s.wait_for(r"hello", timeout=5):
        log("Found expected output!")
    else:
        log("Timeout waiting for output")
    
    result = s.capture("output.png")
    print(result["text"])
```

### 4. Run

```bash
cd /tmp/pi-tmux
uv run python script.py
```

---

## tmux_tool.py Module

The module is located at `.pi/skills/tmux-tape/tmux_tool.py`. Import it in your scripts:

```python
from tmux_tool import TerminalSession
```

### TerminalSession Class

```python
class TerminalSession:
    def __init__(self, name, cols=120, rows=35, port=7681):
        """Create terminal session."""
    
    def send(self, text: str) -> None:
        """Send text to terminal."""
    
    def send_key(self, key: str) -> None:
        """Send special key: Enter, C-c, C-d, C-l, Escape, Tab, Up, Down, C-Left, C-Right, etc."""
    
    def sleep(self, seconds: float) -> None:
        """Wait for duration. Use wait_for() instead when possible."""
    
    def wait_for(self, pattern: str, timeout: float = 10.0, interval: float = 0.1) -> bool:
        """Wait for regex pattern to appear in terminal. RECOMMENDED over sleep()."""
    
    def wait_for_content(self, check_fn, timeout: float = 10.0, interval: float = 0.1) -> bool:
        """Wait for custom condition on terminal content."""
    
    def capture_text(self) -> str:
        """Get terminal text (ANSI-stripped)."""
    
    def capture_raw(self) -> str:
        """Get terminal text with ANSI codes preserved (for debugging)."""
    
    def capture_screenshot(self, filename=None, upload=False) -> dict:
        """Take screenshot via browser. Returns {screenshot, url?}."""
    
    def capture(self, filename=None, upload=False) -> dict:
        """Capture both text and screenshot. Returns {text, screenshot, url?}."""
    
    def upload(self, filepath: str) -> str:
        """Upload image to imgbb, returns URL."""
```

### Use wait_for() Instead of sleep()

**❌ AVOID: Using sleep() with fixed durations**
```python
s.send("some command")
s.sleep(5)  # Wastes time if command finishes in 1s
# Or fails if command takes 6s
```

**✅ RECOMMENDED: Use wait_for() to wait for actual output**
```python
s.send("some command")
s.send_key("Enter")

# Wait until specific text appears
if s.wait_for(r"Ready|Done|prompt>", timeout=10):
    print("Command completed!")
else:
    print("Timeout - command didn't complete")

result = s.capture("result.png")
```

**Benefits of wait_for():**
- Tests run faster (no wasted sleep time)
- More reliable (waits for actual condition)
- Better debugging (knows when things fail)

### Debugging with Raw ANSI

To see the raw ANSI output (useful for debugging colors/attributes):

```python
raw = s.capture_raw()
print(repr(raw[:500]))  # Show escaped ANSI codes
```

---

## Key Reference

| Key | Description |
|-----|-------------|
| `Enter` | Return/Enter |
| `C-c` | Ctrl+C (interrupt) |
| `C-d` | Ctrl+D (EOF) |
| `C-l` | Clear screen |
| `C-Left` / `C-Right` | Ctrl+Arrow (word navigation) |
| `Escape` | Escape key |
| `Tab` | Tab key |
| `Shift-Tab` | Shift+Tab |
| `Space` | Space bar |
| `Up` / `Down` / `Left` / `Right` | Arrow keys |

---

## Common Patterns

### Start Alfred (asyncio app)
```python
import time
from tmux_tool import TerminalSession

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

with TerminalSession("alfred", port=7681) as s:
    log("Starting Alfred...")
    s.send("bash")
    s.send_key("Enter")
    s.sleep(0.3)
    
    s.send("cd /workspace/alfred-prd && export $(grep -v '^#' .env | xargs) && .venv/bin/alfred")
    s.send_key("Enter")
    
    # Wait for startup banner instead of fixed sleep
    if s.wait_for(r"Alfred.*Your Persistent Memory Assistant", timeout=5):
        log("Alfred started!")
    
    result = s.capture("startup.png")
    print(result["text"])
```

### Send Message and Capture Response
```python
s.send("what is 2+2?")
s.send_key("Enter")

# Wait for response (look for any output after the prompt)
if s.wait_for(r"\n[^>].+", timeout=15):  # Any non-prompt line
    print("Got response!")

result = s.capture("response.png")
print(result["text"])
```

### Upload Screenshots for Sharing
```python
result = s.capture("important.png", upload=True)
print(f"Screenshot URL: {result['url']}")  # https://0x0.st/xxx.png
```

### Clean Exit
```python
s.send_key("C-c")
s.send("exit")
s.send_key("Enter")
s.sleep(0.5)
```

---

## Workflow

### 1. Create Session Directory
```bash
SESSION_DIR="/tmp/pi-tmux/$(date +%Y-%m-%d_%H-%M-%S)"
mkdir -p "$SESSION_DIR"
cp .pi/skills/tmux-tape/tmux_tool.py "$SESSION_DIR/"
cd "$SESSION_DIR"
```

### 2. Write Script with Logging
Create `script.py` with timestamps for visibility:

```python
#!/usr/bin/env python3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tmux_tool import TerminalSession

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

def main():
    log("Starting test...")
    
    with TerminalSession("mytest", port=7681) as s:
        log("Session created")
        
        # Your test steps here with logging...
        
        log("Test complete!")

if __name__ == "__main__":
    main()
```

### 3. Run
```bash
uv run python script.py
```

### 4. Check Results
- Text output printed to stdout (with timestamps if you added logging)
- Screenshots saved in session directory
- Use `upload=True` to get shareable URLs

---

## Error Handling

**Retry pattern:**
1. Read error message
2. Check script.py
3. Fix issue (timing, typo, wrong port)
4. Run again
5. Stop after 3 attempts

**Common issues:**

| Error | Cause | Fix |
|-------|-------|-----|
| `ERR_CONNECTION_REFUSED` | ttyd not running | Check port, wait longer |
| `tmux: command not found` | tmux not installed | Install tmux |
| Empty screenshot | Page didn't load | Increase timeout in wait_for() |
| Upload failed | Network issue | Retry or skip upload |

---

## Image Upload

Upload uses **imgbb** — requires `IMGBB_API_KEY` in environment.

```python
# Upload during capture
result = s.capture("screen.png", upload=True)
url = result["url"]  # https://i.ibb.co/xxx/xxx.png

# Upload existing file
url = s.upload("existing.png")
```

**Setup:**
Add to your `.env` file:
```bash
IMGBB_API_KEY=your_api_key_here
```

**Features:**
- Direct image URLs
- Reliable hosting

---

## Output Format

After running, report terminal text output and list uploaded URLs at the bottom.

**Always output uploaded URLs at the bottom of your response** so they're easy to find and click.

Example:

```
Session dir: /tmp/pi-tmux/2026-02-22_01-45-00
Script: script.py

Text:
[terminal text output]

---

Screenshots:
https://0x0.st/xxx.png
https://0x0.st/yyy.png
```

---

## Full Example

```python
#!/usr/bin/env python3
"""Test Alfred CLI with proper logging and wait_for."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tmux_tool import TerminalSession


def log(msg):
    """Print with timestamp."""
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def main():
    log("=== Alfred Test ===")
    
    with TerminalSession("alfred", port=7681) as s:
        log("Starting bash...")
        s.send("bash")
        s.send_key("Enter")
        s.sleep(0.3)
        
        log("Starting Alfred...")
        s.send("cd /workspace/alfred-prd && .venv/bin/alfred")
        s.send_key("Enter")
        
        # Wait for startup instead of fixed sleep
        if s.wait_for(r"Alfred.*Assistant", timeout=5):
            log("Alfred ready!")
        else:
            log("WARNING: Alfred startup timeout")
        
        result = s.capture("startup.png")
        print(result["text"][:500])
        
        log("Sending message...")
        s.send("what is 2+2?")
        s.send_key("Enter")
        
        # Wait for response
        if s.wait_for(r"4|four", timeout=15):
            log("Got answer!")
        
        result = s.capture("response.png")
        print(result["text"][-500:])  # Last 500 chars
        
        log("Cleaning up...")
        s.send_key("C-c")
        s.send("exit")
        s.send_key("Enter")
    
    log("=== Done ===")


if __name__ == "__main__":
    main()
```

---

## Tips

1. **Use `uv run`** — Always run scripts with `uv run python script.py`
2. **Add logging** — Use `log()` function with timestamps to track progress
3. **Use `wait_for()`** — Instead of `sleep()`, wait for actual output patterns
4. **Unique ports** — Use different ports for concurrent sessions (7681, 7682, etc.)
5. **Use bash** — Avoid fish/shell compatibility issues
6. **Upload selectively** — Use `upload=True` only when you need shareable URLs
7. **Check text** — Always print `result["text"]` for verification

---

## References

- ttyd: https://github.com/tsl0922/ttyd
- tmux: https://github.com/tmux/tmux
- playwright: https://playwright.dev
- 0x0.st: https://0x0.st
